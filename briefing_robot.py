import requests
import os
import yfinance as yf
import html
from bs4 import BeautifulSoup

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN', '').strip()
chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

# 🎯 나의 관심 리스트 (종목명: [야후티커, 네이버코드])
COMPANIES = {
    '삼성전자': ['005930.KS', '005930'],
    'SK하이닉스': ['000660.KS', '000660'],
    '한미반도체': ['042700.KS', '042700'],
    '애플': ['AAPL', 'AAPL'],
    '엔비디아': ['NVDA', 'NVDA'],
    '마이크론': ['MU', 'MU'],
    '테슬라': ['TSLA', 'TSLA']
}
INDICES = {
    '코스피': '^KS11', '코스닥': '^KQ11', 'S&P 500': '^GSPC', '나스닥': '^IXIC'
}

def get_weather():
    try:
        url = "https://wttr.in/Seoul?format=%t+%C"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        return f"🌡️ 현재 서울: {res.text.strip().replace('Â', '')}"
    except:
        return "날씨 정보 확인 불가"

def get_market_indices():
    result = ""
    for name, ticker in INDICES.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            t_price, y_price = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            diff, pct = t_price - y_price, ((t_price - y_price) / y_price) * 100
            sign = "▲" if diff > 0 else "▼" if diff < 0 else "-"
            result += f" 🔹 {name}: {t_price:,.2f} ({sign}{abs(diff):,.2f}, {pct:+.2f}%)\n"
        except:
            result += f" 🔹 {name}: 확인 불가\n"
    return result

def get_stocks_and_news():
    result = ""
    for name, info in COMPANIES.items():
        ticker, code = info[0], info[1]
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            t_price, y_price = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            diff, pct = t_price - y_price, ((t_price - y_price) / y_price) * 100
            sign = "▲" if diff > 0 else "▼" if diff < 0 else "-"
            
            if '.KS' in ticker or '.KQ' in ticker:
                price_str = f"{int(t_price):,}원 ({sign}{int(abs(diff)):,}원, {pct:+.2f}%)"
            else:
                price_str = f"${t_price:,.2f} ({sign}${abs(diff):,.2f}, {pct:+.2f}%)"
        except:
            price_str = "확인 불가"
            
        result += f"🏢 <b>{name}</b> (마감: {price_str})\n"
        
        # 👥 수급 데이터 (한국 종목만)
        if '.KS' in ticker or '.KQ' in ticker:
            try:
                n_url = f"https://finance.naver.com/item/frgn.naver?code={code}"
                n_res = requests.get(n_url, headers={'User-Agent': 'Mozilla/5.0'})
                n_soup = BeautifulSoup(n_res.text, 'html.parser')
                row = n_soup.select('table.type2 tr[onmouseover]')[0].select('td')
                ant, inst, fore = row[4].text.strip(), row[5].text.strip(), row[6].text.strip()
                result += f"   👥 수급: 개인 {ant} / 외인 {fore} / 기관 {inst}\n"
            except:
                pass
        
        # 🔗 [핵심] 절대 안 막히는 직통 뉴스 링크 생성
        if '.KS' in ticker or '.KQ' in ticker:
            news_link = f"https://finance.naver.com/item/news.naver?code={code}"
        else:
            news_link = f"https://www.google.com/search?q={name}+stock+news&tbm=nws"
        
        result += f"   🔗 <a href='{news_link}'>[{name}] 실시간 뉴스 확인하기</a>\n\n"
        
    return result

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather = get_weather()
    indices = get_market_indices()
    stocks = get_stocks_and_news()
    
    # 종합 경제 시황 링크
    eco_news_link = "https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=101"
    
    briefing = (
        f"🌅 <b>[에드워드 모닝 브리핑]</b>\n\n"
        f"📍 <b>오늘의 날씨</b>\n{weather}\n\n"
        f"────────────────\n"
        f"📊 <b>주요 시장 지수</b>\n{indices}\n"
        f"────────────────\n"
        f"📰 <b>경제 시황 종합</b>\n"
        f"▪️ <a href='{eco_news_link}'>네이버 경제 주요뉴스 바로가기</a>\n"
        f"────────────────\n"
        f"📈 <b>관심 종목 & 수급 현황</b>\n\n{stocks}"
    )
    send_telegram(briefing)
