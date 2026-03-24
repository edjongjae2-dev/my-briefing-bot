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

def get_naver_news(query, is_main=False):
    # 검색 정확도를 높이기 위해 쿼리 조정
    url = f"https://search.naver.com/search.naver?where=news&query={query}&sort=0"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    news_result = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 뉴스 아이템을 잡는 선택자를 더 포괄적으로 변경
        articles = soup.select('.news_wrap, .news_area')
        
        count = 2 if is_main else 1
        found = 0
        
        for article in articles:
            if found >= count: break
            
            title_tag = article.select_one('.news_tit')
            if not title_tag: continue
            
            title = title_tag.text.strip()
            link = title_tag['href']
            
            # 요약 설명 부분 추출 (클래스명이 다를 수 있어 여러 개 시도)
            desc_tag = article.select_one('.api_txt_lines.dsc_txt_wrap') or article.select_one('.news_dsc')
            summary = desc_tag.text.strip() if desc_tag else "상세 내용은 기사를 확인하세요."
            if len(summary) > 70:
                summary = summary[:70] + "..."
                
            clean_title = html.escape(title)
            clean_summary = html.escape(summary)
            
            if is_main:
                news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
                news_result += f"    💡 <i>{clean_summary}</i>\n\n"
            else:
                news_result += f"   └ <a href='{link}'>{clean_title}</a>\n"
                news_result += f"     💡 <i>{clean_summary}</i>\n"
            found += 1
                
        return news_result if news_result else "뉴스 로딩 중 (검색 결과 없음)\n"
    except:
        return "뉴스 정보 연결 실패\n"

def get_economy_news():
    return get_naver_news("경제 금융 주요뉴스", is_main=True)

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
        
        # 한국 주식 수급(개인/외국인/기관) 가져오기
        if '.KS' in ticker or '.KQ' in ticker:
            try:
                code = ticker.split('.')[0]
                n_url = f"https://finance.naver.com/item/frgn.naver?code={code}"
                n_res = requests.get(n_url, headers={'User-Agent': 'Mozilla/5.0'})
                n_soup = BeautifulSoup(n_res.text, 'html.parser')
                
                rows = n_soup.select('table.type2 tr[onmouseover]')
                if rows:
                    cols = rows[0].select('td')
                    # 네이버 금융 수급 표 순서: 4(개인), 5(기관), 6(외국인)
                    ant = cols[4].text.strip()   # 개인
                    inst = cols[5].text.strip()  # 기관
                    fore = cols[6].text.strip()  # 외국인
                    result += f"   👥 수급: 개인 {ant} / 외국인 {fore} / 기관 {inst}\n"
            except:
                pass
        
        result += get_naver_news(name, is_main=False)
        result += "\n"
        
    return result

def send_telegram(message):
    if not token or not chat_id:
        print("토큰이나 채팅 ID가 설정되지 않았습니다.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    market_indices = get_market_indices()
    eco_news = get_economy_news()
    vip_stocks = get_stocks_and_news()
    
    briefing = f"🌅 <b>[에드워드 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📊 <b>주요 시장 지수</b>\n{market_indices}\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>관심 종목 & 관련 뉴스</b>\n\n{vip_stocks}"
    
    send_telegram(briefing)
