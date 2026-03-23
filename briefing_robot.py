import requests
import os
import re
import xml.etree.ElementTree as ET
import yfinance as yf
import html
import time
import google.generativeai as genai # 🌟 제미나이 AI 부품!

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
gemini_api_key = os.environ.get('GEMINI_API_KEY') # 🌟 방금 넣으신 AI 열쇠!

# 제미나이 AI 세팅 (가장 빠르고 똑똑한 모델)
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

# 🎯 나의 관심 기업 및 지수!
COMPANIES = {
    '삼성전자': '005930.KS', 'SK하이닉스': '000660.KS', '한미반도체': '042700.KS',
    '애플': 'AAPL', '엔비디아': 'NVDA', '마이크론': 'MU', '테슬라': 'TSLA'
}
INDICES = {
    '코스피': '^KS11', '코스닥': '^KQ11', 'S&P 500': '^GSPC', '나스닥': '^IXIC'
}

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
    except:
        pass
    return "날씨 정보를 읽어오는 중입니다.. 🌤️"

# 📊 2. 시장 지수 마감 정보
def get_market_indices():
    result = ""
    for name, ticker in INDICES.items():
        try:
            price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
            result += f" 🔹 {name}: {price:,.2f}\n"
        except:
            result += f" 🔹 {name}: 확인 불가\n"
    return result

# 🤖 [핵심 기능] 제미나이 AI 요약 로봇 출동!
def get_ai_summary(title, url):
    if not gemini_api_key:
        return "AI 키가 없어 요약할 수 없습니다."
    
    try:
        # 1. 기사 본문에 몰래 들어가서 글자들을 쓸어담습니다.
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        
        paragraphs = soup.find_all('p')
        content = " ".join([p.text for p in paragraphs if len(p.text) > 30])
        
        # 2. 제미나이에게 명령을 내립니다!
        if len(content) < 100:
            prompt = f"다음은 경제 기사 제목입니다. 이 제목이 어떤 의미인지 딱 1줄(50자 이내)로 요약해줘.\n제목: {title}"
        else:
            content = content[:1500] # AI가 너무 많이 읽지 않게 적당히 자름
            prompt = f"다음 기사 본문을 읽고, 가장 중요한 핵심 내용만 딱 1줄(공백 포함 60자 이내)로 짧게 요약해줘. 해요체(~요, ~다)로 대답해.\n본문: {content}"
            
        response = model.generate_content(prompt)
        summary = response.text.strip().replace('\n', ' ')
        
        # 텔레그램 에러 방지를 위해 특수문자 안전처리
        return html.escape(summary)
    except Exception:
        return "AI가 기사를 읽지 못했습니다. (보안 차단)"

# 📰 3. 경제 뉴스 (AI 요약 추가)
def get_economy_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        news_result = ""
        for item in items[:2]: # 요약 시간이 걸리므로 메인 뉴스는 2개만!
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            summary = get_ai_summary(clean_title, link)
            time.sleep(1) # AI가 지치지 않게 1초 휴식
            
            news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
            news_result += f"   💡 <i>{summary}</i>\n\n"
        return news_result
    except Exception:
        return "뉴스 로딩 에러"

# 📈 4. 관심 기업 & 뉴스 (AI 요약 추가)
def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
        try:
            price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
            price_str = f"{int(price):,}원" if str(ticker).endswith('.KS') else f"${price:,.2f}"
        except:
            price_str = "가격 확인 불가"
            
        result += f"🏢 <b>{name}</b> (현재가: {price_str})\n"
        
        news_url = f"https://news.google.com/rss/search?q={name}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(news_url, timeout=10)
            root = ET.fromstring(res.content)
            item = root.findall('.//item')[0] # 종목별 최신 뉴스 딱 1개!
            
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            summary = get_ai_summary(clean_title, link)
            time.sleep(1)
            
            result += f"  └ <a href='{link}'>{clean_title}</a>\n"
            result += f"    └ 💡 <i>{summary}</i>\n"
        except:
            result += "  └ 최근 관련 뉴스가 없습니다.\n"
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
    briefing += f"📈 <b>관심 종목 & 최신 뉴스</b>\n\n{vip_stocks}"
    
    send_telegram(briefing)
