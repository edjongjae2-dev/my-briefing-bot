import requests
import os
import re
import xml.etree.ElementTree as ET
import yfinance as yf
import html
from bs4 import BeautifulSoup
import google.generativeai as genai
import time 

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
gemini_key = os.environ.get('GEMINI_API_KEY')

# 🧠 제미나이 AI 세팅 (🌟 못 찾던 뇌 대신, 가장 안정적인 gemini-pro로 교체!)
if gemini_key:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-pro')

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
        url_current = "https://wttr.in/Seoul?format=%t+%C"
        res_c = requests.get(url_current, timeout=10)
        res_c.encoding = 'utf-8'
        current = res_c.text.strip().replace("Â", "").replace("Partly cloudy", "구름 조금").replace("Clear", "맑음").replace("Cloudy", "흐림").replace("Overcast", "매우 흐림").replace("Light rain", "약한 비")
        
        url_json = "https://wttr.in/Seoul?format=j1"
        res_j = requests.get(url_json, timeout=10)
        hourly_data = res_j.json()['weather'][0]['hourly']
        
        forecast = ""
        for h in hourly_data:
            time_val = h['time']
            time_str = "00시" if time_val == "0" else f"{int(time_val)//100:02d}시"
            if time_str in ["09시", "12시", "15시", "18시", "21시"]:
                temp = h['tempC']
                desc = h['weatherDesc'][0]['value'].replace("Partly cloudy", "구름").replace("Clear", "맑음").replace("Cloudy", "흐림").replace("Overcast", "흐림").replace("Sunny", "맑음")
                forecast += f"\n   ⏱️ {time_str}: {temp}°C ({desc})"
                
        return f"🌡️ 현재 서울: {current}\n👇 <b>오늘의 시간별 예보</b>{forecast}"
    except:
        return "날씨 정보를 불러올 수 없습니다."

def get_market_indices():
    result = ""
    for name, ticker in INDICES.items():
        try:
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

# 🤖 제미나이 AI 
def get_ai_summary(news_title):
    if not gemini_key: return "AI 키 없음"
    try:
        # 과속 방지 3초 휴식
        time.sleep(3) 
        
        prompt = f"다음은 경제 기사 제목이야: '{news_title}'. 이 뉴스가 시장이나 해당 기업에 미칠 핵심 영향이나 의미를 딱 1줄(40자 이내)로 알기 쉽게 설명해줘."
        response = model.generate_content(prompt)
        return response.text.strip().replace('\n', ' ')
    except Exception as e:
        error_msg = str(e)[:40] 
        return f"AI 에러: {error_msg}..."

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
            
            summary = html.escape(get_ai_summary(clean_title))
            
            news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
            news_result += f"   💡 <i>{summary}</i>\n\n"
        return news_result
    except:
        return f"뉴스 로딩 중 에러."

def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
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
        
        if '.KS' in ticker or '.KQ' in ticker:
            try:
                code = ticker.split('.')[0]
                n_url = f"https://finance.naver.com/item/frgn.naver?code={code}"
                n_res = requests.get(n_url, headers={'User-Agent': 'Mozilla/5.0'})
                n_soup = BeautifulSoup(n_res.text, 'html.parser')
                
                rows = n_soup.select('table.type2 tr[onmouseover]')
                if rows:
                    cols = rows[0].select('td')
                    inst = cols[5].text.strip() 
                    fore = cols[6].text.strip() 
                    result += f"  👥 수급(최근영업일): 외국인 {fore} / 기관 {inst}\n"
            except:
                pass
        
        news_url = f"https://news.google.com/rss/search?q={name}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(news_url, timeout=10)
            root = ET.fromstring(res.content)
            item = root.findall('.//item')[0]
            
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            
            summary = html.escape(get_ai_summary(clean_title))
            
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
