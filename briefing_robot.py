import requests
import os
import re
import xml.etree.ElementTree as ET
import yfinance as yf # 🌟 주식 가격을 가져오는 마법 부품
import html # 특수문자 에러 방지

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# 🎯 나의 관심 기업 세팅 (언제든 종목명과 티커를 수정하세요!)
# 한국 주식은 뒤에 .KS(코스피) 또는 .KQ(코스닥)를 붙이고, 미국 주식은 그냥 씁니다.
COMPANIES = {
    '삼성전자': '005930.KS',
    '애플': 'AAPL',
    '테슬라': 'TSLA'
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
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"
    except:
        return "날씨 정보 연결 일시 오류"

# 📰 2. 일반 경제 뉴스 (링크를 제목에 예쁘게 숨김!)
def get_economy_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        news_result = ""
        for item in items[:3]: # 주요 경제 뉴스는 딱 3개만!
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            # 🌟 더러운 주소 대신 <a href> 태그를 써서 깔끔하게 제목에 링크를 숨깁니다!
            news_result += f"▪️ <a href='{link}'>{clean_title}</a>\n"
            
        return news_result
    except Exception as e:
        return f"뉴스 로딩 중 에러가 발생했습니다."

# 📈 3. 관심 기업 주식 & 관련 뉴스
def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
        # 1) 주식 종가 가져오기
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            price = hist['Close'].iloc[-1]
            
            if str(ticker).endswith('.KS') or str(ticker).endswith('.KQ'):
                price_str = f"{int(price):,}원"
            else:
                price_str = f"${price:,.2f}"
        except:
            price_str = "가격 정보 오류"
            
        result += f"\n🏢 <b>{name}</b> (마감: {price_str})\n"
        
        # 2) 해당 기업 최신 뉴스 2개 가져오기
        news_url = f"https://news.google.com/rss/search?q={name}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(news_url, timeout=10)
            root = ET.fromstring(res.content)
            items = root.findall('.//item')[:2] # 2개만!
            
            for item in items:
                title = item.find('title').text.strip()
                clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
                link = item.find('link').text.strip()
                result += f" 🔹 <a href='{link}'>{clean_title}</a>\n"
        except:
            result += " 🔹 관련 뉴스 로딩 실패\n"
            
    return result

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "parse_mode": "HTML", # 🌟 텔레그램이 HTML 태그(숨긴 링크)를 읽도록 허락하는 옵션!
        "disable_web_page_preview": True 
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    eco_news = get_economy_news()
    vip_stocks = get_stocks_and_news()
    
    briefing = f"🌅 <b>[에드워드 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}\n"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>나의 관심 기업 종목 & 뉴스</b>{vip_stocks}"
    
    send_telegram(briefing)
