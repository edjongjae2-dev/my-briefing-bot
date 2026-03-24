import requests
import os
import re
import xml.etree.ElementTree as ET
import yfinance as yf
import html
from bs4 import BeautifulSoup
import time 

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN', '').strip()
chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()

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
# 🪙 코인 리스트 (원화 KRW 기준으로 변경!)
CRYPTOS = {
    '비트코인': 'BTC-KRW',
    '이더리움': 'ETH-KRW',
    '솔라나': 'SOL-KRW'
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
                forecast += f"\n    ⏱️ {time_str}: {temp}°C ({desc})"
                
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

# 🪙 코인 정보 가져오는 함수 (원화 표시로 수정)
def get_crypto_prices():
    result = ""
    for name, ticker in CRYPTOS.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            t_price = hist['Close'].iloc[-1]
            y_price = hist['Close'].iloc[-2]
            
            diff = t_price - y_price
            pct = (diff / y_price) * 100
            sign = "▲" if diff > 0 else "▼" if diff < 0 else "-"
            
            # 원화는 금액이 크므로 int()를 씌워서 소수점을 없애고 깔끔하게 표현합니다.
            result += f" 🔹 {name}: {int(t_price):,}원 ({sign}{abs(int(diff)):,}원, {pct:+.2f}%)\n"
        except:
            result += f" 🔹 {name}: 확인 불가\n"
    return result

def get_smart_summary(news_title, news_link):
    if gemini_key:
        try:
            time.sleep(1)
            prompt = f"경제 뉴스 제목: '{news_title}'. 이 뉴스가 미칠 영향을 딱 1줄(40자 이내)로 설명해."
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {'Content-Type': 'application/json'}
            res = requests.post(api_url, json=payload, headers=headers, timeout=5)
            
            if res.status_code == 200:
                answer = res.json()['candidates'][0]['content']['parts'][0]['text']
                return answer.strip().replace('\n', ' ')
        except:
            pass 

    try:
        r1 = requests.get(news_link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        urls = re.findall(r'href=[\'"]?(https?://[^\'" >]+)', r1.text)
        real_url = next((u for u in urls if 'google.com' not in u and 'policies.google' not in u), None)
        
        if real_url:
            r2 = requests.get(real_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            s2 = BeautifulSoup(r2.text, 'html.parser')
            desc = s2.find('meta', attrs={'property': 'og:description'}) or s2.find('meta', attrs={'name': 'description'})
            
            if desc and desc.get('content'):
                summary = desc.get('content').strip()
                if "Comprehensive" not in summary and len(summary) > 5:
                    return summary[:65] + "..." if len(summary) > 65 else summary
    except:
        pass
    return "상세 내용은 기사 링크를 참조해 주세요."

def get_economy_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        news_result = ""
        for item in items[:2]:
            title = item.find('title').text.strip()
            clean_title = html.escape(re.sub(r' - [^ -]+$', '', title))
            link = item.find('link').text.strip()
            summary = html.escape(get_smart_summary(clean_title, link))
            news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
            news_result += f"    💡 <i>{summary}</i>\n\n"
        return news_result
    except:
        return f"뉴스 로딩 실패"

def get_stocks_and_news():
    result = ""
    for name, ticker in COMPANIES.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            t_price, y_price = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            diff, pct = t_price - y_price, (t_price - y_price) / y_price * 100
            sign = "▲" if diff > 0 else "▼" if diff < 0 else "-"
            price_str = f"{int(t_price):,}원" if '.KS' in ticker or '.KQ' in ticker else f"${t_price:,.2f}"
            price_str += f" ({sign}{abs(diff):,.2f}, {pct:+.2f}%)"
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
                    ant = cols[4].text.strip()   # 개인
                    inst = cols[5].text.strip()  # 기관
                    fore = cols[6].text.strip()  # 외국인
                    result += f"   👥 수급: 개인 {ant} / 외국인 {fore} / 기관 {inst}\n"
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
            summary = html.escape(get_smart_summary(clean_title, link))
            result += f"   └ <a href='{link}'>{clean_title}</a>\n"
            result += f"     💡 <i>{summary}</i>\n"
        except:
            result += "   └ 관련 뉴스 로딩 실패\n"
        result += "\n"
    return result

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    market_indices = get_market_indices()
    crypto_prices = get_crypto_prices() # 🪙 코인 정보
    eco_news = get_economy_news()
    vip_stocks = get_stocks_and_news()
    
    briefing = f"🌅 <b>[에드워드 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📊 <b>주요 시장 지수</b>\n{market_indices}\n"
    briefing += f"────────────────\n"
    briefing += f"🪙 <b>주요 암호화폐</b>\n{crypto_prices}\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}\n"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>관심 종목 & 관련 뉴스</b>\n\n{vip_stocks}"
    
    send_telegram(briefing)
