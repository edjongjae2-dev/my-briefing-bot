import requests
from bs4 import BeautifulSoup
import os
import re
import xml.etree.ElementTree as ET
import yfinance as yf
import html

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# 🎯 유저님의 관심 기업 리스트!
COMPANIES = {
    '삼성전자': '005930.KS',
    'SK하이닉스': '000660.KS',
    '한미반도체': '042700.KS',
    '애플': 'AAPL',
    '엔비디아': 'NVDA',
    '마이크론': 'MU',
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

# 🌟 [핵심 기능] 기사 링크에 들어가서 '한 줄 요약' 훔쳐오기
def get_article_summary(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 기사 주소로 몰래 접속합니다.
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 언론사가 숨겨둔 '요약본(description)'을 찾습니다.
        desc = soup.find('meta', attrs={'property': 'og:description'}) or soup.find('meta', attrs={'name': 'description'})
        
        if desc and desc.get('content'):
            summary = desc.get('content').strip()
            # 요약이 너무 길면 텔레그램이 지저분해지므로 80자에서 자릅니다.
            if len(summary) > 80:
                summary = summary[:80] + "..."
            if len(summary) < 5:
                return "기사를 클릭해서 자세한 내용을 확인하세요."
            return summary
        return "기사를 클릭해서 자세한 내용을 확인하세요."
    except:
        return "요약을 제공하지 않는 기사입니다."

# 📰 2. 일반 경제 뉴스 (제목 + 요약)
def get_economy_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        news_result = ""
        # 요약을 가져오느라 시간이 조금 걸리므로 핵심 뉴스 2개만 봅니다.
        for item in items[:2]: 
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            # 요약 로봇 출동!
            summary = html.escape(get_article_summary(link)) 
            
            news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
            news_result += f"   💡 <i>{summary}</i>\n\n"
            
        return news_result
    except Exception as e:
        return f"뉴스 로딩 중 에러가 발생했습니다."

# 📈 3. 관심 기업 주식 & 관련 뉴스 (제목 + 요약)
def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            price = hist['Close'].iloc[-1]
            if str(ticker).endswith('.KS') or str(ticker).endswith('.KQ'):
                price_str = f"{int(price):,}원"
            else:
                price_str = f"${price:,.2f}"
        except:
            price_str = "가격 확인 불가"
            
        result += f"🏢 <b>{name}</b> (마감: {price_str})\n"
        
        news_url = f"https://news.google.com/rss/search?q={name}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(news_url, timeout=10)
            root = ET.fromstring(res.content)
            # 종목이 많으므로 종목당 뉴스는 가장 최신 1개씩만!
            items = root.findall('.//item')[:1] 
            
            for item in items:
                title = item.find('title').text.strip()
                clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
                link = item.find('link').text.strip()
                
                # 요약 로봇 출동!
                summary = html.escape(get_article_summary(link))
                
                result += f" 🔹 <a href='{link}'>{clean_title}</a>\n"
                result += f"    └ <i>{summary}</i>\n"
        except:
            result += " 🔹 관련 뉴스 로딩 실패\n"
        result += "\n"
        
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
    
    briefing = f"🌅 <b>[에드워드 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>관심 종목 & 관련 뉴스</b>\n\n{vip_stocks}"
    
    send_telegram(briefing)
