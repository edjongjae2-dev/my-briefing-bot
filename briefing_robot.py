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
            # 안전하게 5일 치를 가져와서 가장 최근 2일 비교
            hist = yf.Ticker(ticker).history(period="5d")
            t_price = hist['Close'].iloc[-1]
            y_price = hist['Close'].iloc[-2]
            
            diff = t_price - y_price
            pct = (diff / y_price) * 100
            sign = "▲" if diff > 0 else "▼" if diff < 0 else "-"
            
            result += f" 🔹 {name}: {t_price:,.2f} ({sign}{abs(diff):,.2f}, {pct:+.2f}%)\n"
        except:
            result += f" 🔹 {name}: 확인 불가\n"
    return result

# 🤖 제미나이 AI: 빈 화면이면 제목으로 추론하기!
def get_ai_summary(news_url, news_title):
    if not gemini_key: return "AI 키 없음"
    try:
        res = requests.get(news_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        article_text = " ".join([p.text for p in paragraphs])[:1000]
        
        # 🌟 구글이 막아서 본문이 짧을 경우, 제목을 분석해서 요약하라고 명령합니다!
        if len(article_text) < 50:
            prompt = f"다음은 경제 기사 제목이야: '{news_title}'. 이 제목이 뜻하는 핵심 내용이나 경제적 영향을 딱 1줄(40자 이내)로 알기 쉽게 설명해줘."
        else:
            prompt = f"다음 뉴스 기사 내용을 딱 1줄(40자 이내)로 핵심만 요약해줘:\n\n{article_text}"
            
        response = model.generate_content(prompt)
        return response.text.strip().replace('\n', ' ')
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
        for item in items[:2]:
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            # AI 요약 함수에 기사 제목도 같이 넘겨줍니다.
            summary = html.escape(get_ai_summary(link, clean_title))
            
            news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
            news_result += f"   💡 <i>{summary}</i>\n\n"
        return news_result
    except:
        return f"뉴스 로딩 중 에러."

def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
        # 1. 가격 및 등락률 계산
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            t_price = hist['Close'].iloc[-1]
            y_price = hist['Close'].iloc[-2]
            
            diff = t_price - y_price
            pct = (diff / y_price) * 100
            sign = "▲" if diff > 0 else "▼" if diff < 0 else "-"
            
            if '.KS' in ticker or '.KQ' in ticker:
                price_str = f"{int(t_price):,}원 ({sign}{int(abs(diff)):,}원, {pct:+.2f}%)"
            else:
                price_str = f"${t_price:,.2f} ({sign}${abs(diff):,.2f}, {pct:+.2f}%)"
        except:
            price_str = "확인 불가"
            
        result += f"🏢 <b>{name}</b> (마감: {price_str})\n"
        
        # 2. 한국 주식만 네이버 수급 긁어오기
        if '.KS' in ticker or '.KQ' in ticker:
            try:
                code = ticker.split('.')[0]
                n_url = f"https://finance.naver.com/item/investor.naver?code={code}"
                n_res = requests.get(n_url, headers={'User-Agent': 'Mozilla/5.0'})
                n_soup = BeautifulSoup(n_res.text, 'html.parser')
                
                rows = n_soup.select('table.type2 tr[onmouseover]')
                if rows:
                    cols = rows[0].select('td')
                    ind = cols[1].text.strip() # 개인
                    fore = cols[2].text.strip() # 외국인
                    inst = cols[3].text.strip() # 기관
                    result += f"  👥 수급: 개인 {ind} / 외국인 {fore} / 기관 {inst}\n"
            except:
                result += "  👥 수급: 로딩 실패\n"
        
        # 3. 관련 뉴스 및 요약
        news_url = f"https://news.google.com/rss/search?q={name}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(news_url, timeout=10)
            root = ET.fromstring(res.content)
            item = root.findall('.//item')[0]
            
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            summary = html.escape(get_ai_summary(link, clean_title))
            
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
