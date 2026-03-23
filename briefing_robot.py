import requests
import os
import re
import xml.etree.ElementTree as ET
import yfinance as yf
import html
import time
import google.generativeai as genai

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
gemini_api_key = os.environ.get('GEMINI_API_KEY')

# 제미나이 AI 두뇌 연결
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

# 🎯 나의 관심 기업 세팅 (요청하신 기업들 완벽 추가!)
COMPANIES = {
    '삼성전자': '005930.KS',
    'SK하이닉스': '000660.KS',
    '한미반도체': '042700.KS',
    '애플': 'AAPL',
    '엔비디아': 'NVDA',
    '마이크론': 'MU',
    '테슬라': 'TSLA'
}

# 🤖 AI 요약 로봇 함수
def get_ai_summary(title, link):
    if not gemini_api_key:
        return ""
    try:
        # 기사 본문 긁어오기
        res = requests.get(link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        texts = [p.text.strip() for p in soup.find_all('p') if len(p.text.strip()) > 20]
        content = " ".join(texts)[:1000] # 분석을 위해 앞부분 핵심만 발췌
        
        if len(content) < 50: content = title # 막힌 기사면 제목으로만 추론
            
        # 제미나이에게 요약 지시!
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"다음 뉴스를 1~2줄로 간결하게 핵심만 요약해줘. 어투는 반드시 '~함', '~임'으로 끝내줘.\n\n뉴스내용: {content}"
        response = model.generate_content(prompt)
        time.sleep(2) # AI가 과부하 걸리지 않게 2초 휴식
        return f"\n   💡 <i>{response.text.strip()}</i>\n"
    except Exception as e:
        return f"\n   💡 <i>AI 요약을 불러오지 못했습니다.</i>\n"

# ☀️ 1. 날씨 정보
def get_weather():
    try:
        url = "https://wttr.in/Seoul?format=%t+%C"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            data = res.text.strip().replace("Â", "")
            data = data.replace("Partly cloudy", "구름 조금").replace("Clear", "맑음").replace("Cloudy", "흐림").replace("Overcast", "매우 흐림").replace("Light rain", "약한 비")
            return f"🌡️ 현재 서울: {data}"
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"
    except:
        return "날씨 정보 오류"

# 📰 2. 일반 경제 뉴스 (2개 + AI 요약)
def get_economy_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        news_result = ""
        for item in items[:2]: # 요약글이 길어지므로 가장 중요한 2개만!
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>"
            news_result += get_ai_summary(clean_title, link)
            
        return news_result
    except Exception as e:
        return "뉴스 로딩 중 에러가 발생했습니다.\n"

# 📈 3. 관심 기업 주식 & 관련 뉴스 1개 (AI 요약)
def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
        # 주식 종가
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                price_str = f"{int(price):,}원" if str(ticker).endswith(('.KS', '.KQ')) else f"${price:,.2f}"
            else:
                price_str = "가격 정보 없음"
        except:
            price_str = "가격 정보 오류"
            
        result += f"\n🏢 <b>{name}</b> (마감: {price_str})\n"
        
        # 기업 관련 최신 뉴스 1개 + 요약
        news_url = f"https://news.google.com/rss/search?q={name}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(news_url, timeout=10)
            root = ET.fromstring(res.content)
            item = root.find('.//item')
            if item is not None:
                title = item.find('title').text.strip()
                clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
                link = item.find('link').text.strip()
                
                result += f" 🔹 <a href='{link}'>{clean_title}</a>"
                result += get_ai_summary(clean_title, link)
        except:
            result += " 🔹 뉴스 로딩 실패\n"
            
    return result

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True 
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    eco_news = get_economy_news()
    vip_stocks = get_stocks_and_news()
    
    briefing = f"🌅 <b>[에드워드 AI 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}\n"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>관심 종목 & AI 브리핑</b>{vip_stocks}"
    
    # 텔레그램 글자 수 제한 안전장치
    send_telegram(briefing[:4000])
