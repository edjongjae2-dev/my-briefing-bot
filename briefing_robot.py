import requests
import os
import re
import xml.etree.ElementTree as ET
import yfinance as yf
import html
from bs4 import BeautifulSoup
import google.generativeai as genai

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
gemini_key = os.environ.get('GEMINI_API_KEY')

# 🧠 제미나이 AI 세팅
if gemini_key:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

# 🎯 나의 관심 리스트
COMPANIES = {
    '삼성전자': '005930.KS', 
    'SK하이닉스': '000660.KS', 
    '한미반도체': '042700.KS', 
    '애플': 'AAPL', 
    '엔비디아': 'NVDA', 
    '마이크론': 'MU', 
    '테슬라': 'TSLA'
}
INDICES = {
    '코스피': '^KS11', 
    '코스닥': '^KQ11', 
    'S&P 500': '^GSPC', 
    '나스닥': '^IXIC'
}

def get_weather():
    try:
        url = "https://wttr.in/Seoul?format=%t+%C"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            data = res.text.strip().replace("Â", "").replace("Partly cloudy", "구름 조금").replace("Clear", "맑음").replace("Cloudy", "흐림").replace("Overcast", "매우 흐림").replace("Light rain", "약한 비")
            return f"🌡️ 현재 서울: {data}"
        return "날씨 로딩 중.."
    except:
        return "날씨 오류"

def get_market_indices():
    result = ""
    for name, ticker in INDICES.items():
        try:
            price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
            result += f" 🔹 {name}: {price:,.2f}\n"
        except:
            result += f" 🔹 {name}: 확인 불가\n"
    return result

# 🤖 [핵심] 제미나이 AI에게 기사 1줄 요약 시키기
def get_ai_summary(news_url):
    if not gemini_key:
        return "AI 키가 없어 요약할 수 없습니다."
    
    try:
        # 기사 링크에 들어가서 본문 텍스트를 긁어옵니다.
        res = requests.get(news_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        article_text = " ".join([p.text for p in paragraphs])[:1000] # 앞부분 1000자만
        
        if len(article_text) < 50:
            return "본문이 짧아 요약이 어렵습니다."
            
        # 제미나이에게 명령!
        prompt = f"다음 뉴스 기사 내용을 딱 1줄(40자 이내)로 핵심만 깔끔하게 요약해줘:\n\n{article_text}"
        response = model.generate_content(prompt)
        
        summary = response.text.strip().replace('\n', ' ')
        return summary
    except Exception as e:
        return "요약을 제공하지 않는 기사입니다."

def get_economy_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        news_result = ""
        for item in items[:2]: # 요약 시간이 걸리므로 탑뉴스 2개만!
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            # AI 요약 함수 출동!
            summary = html.escape(get_ai_summary(link))
            
            news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
            news_result += f"   💡 <i>{summary}</i>\n\n"
        return news_result
    except:
        return f"뉴스 로딩 중 에러."

def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
        try:
            price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
            price_str = f"{int(price):,}원" if '.KS' in ticker or '.KQ' in ticker else f"${price:,.2f}"
        except:
            price_str = "확인 불가"
            
        result += f"🏢 <b>{name}</b> (마감: {price_str})\n"
        
        news_url = f"https://news.google.com/rss/search?q={name}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(news_url, timeout=10)
            root = ET.fromstring(res.content)
            item = root.findall('.//item')[0] # 1개만
            
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            # AI 요약 함수 출동!
            summary = html.escape(get_ai_summary(link))
            
            result += f"  └ <a href='{link}'>{clean_title}</a>\n"
            result += f"    💡 <i>{summary}</i>\n"
        except:
            result += "  └ 관련 뉴스 로딩 실패\n"
        result += "\n"
    return result

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    market_indices = get_market_indices()
    eco_news = get_economy_news()
    vip_stocks = get_stocks_and_news()
    
    briefing = f"🌅 <b>[에드워드 AI 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📊 <b>주요 시장 지수</b>\n{market_indices}\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>관심 종목 & 관련 뉴스</b>\n\n{vip_stocks}"
    
    send_telegram(briefing)
