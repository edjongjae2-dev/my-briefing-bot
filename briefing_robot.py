import requests
import os
import yfinance as yf
import html
from bs4 import BeautifulSoup

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN', '').strip()
chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

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
        return f"🌡️ 현재 서울: {current}"
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

# 🌟 구글 뉴스 RSS를 사용하여 안정적으로 뉴스 가져오기
def get_google_news(query, count=1):
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.content, "xml")
        items = soup.find_all("item")
        
        news_text = ""
        for item in items[:count]:
            title = item.title.text.replace(" - " + item.source.text, "").strip()
            link = item.link.text
            news_text += f"   └ <a href='{link}'>{html.escape(title)}</a>\n"
        return news_text if news_text else "   └ 최신 뉴스가 없습니다.\n"
    except:
        return "   └ 뉴스 로딩 실패\n"

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
        
        # 한국 주식 수급 데이터 (네이버 금융 활용)
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
        
        # 구글 뉴스로 종목 뉴스 가져오기
        result += get_google_news(name, count=1)
        result += "\n"
        
    return result

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    market_indices = get_market_indices()
    eco_news = get_google_news("대한민국 경제 증시 시황", count=2)
    vip_stocks = get_stocks_and_news()
    
    briefing = f"🌅 <b>[에드워드 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📊 <b>주요 시장 지수</b>\n{market_indices}\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}\n"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>관심 종목 & 관련 뉴스</b>\n\n{vip_stocks}"
    
    send_telegram(briefing)
