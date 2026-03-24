import requests
import os
import xml.etree.ElementTree as ET
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

# 🌟 [핵심] 네이버 뉴스 검색결과에서 요약본을 바로 주워오는 마법!
def get_naver_news(query, is_main=False):
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    news_result = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        articles = soup.select('.news_area')
        
        count = 2 if is_main else 1 # 메인 뉴스는 2개, 종목 뉴스는 1개
        
        for article in articles[:count]:
            # 기사 제목과 링크 훔쳐오기
            title_tag = article.select_one('.news_tit')
            if not title_tag: continue
            title = title_tag.text.strip()
            link = title_tag['href']
            
            # 네이버 화면에 적혀있는 1줄 요약 훔쳐오기
            desc_tag = article.select_one('.api_txt_lines.dsc_txt_wrap')
            summary = desc_tag.text.strip() if desc_tag else "자세한 내용은 기사를 클릭하세요."
            if len(summary) > 60:
                summary = summary[:60] + "..."
                
            clean_title = html.escape(title)
            clean_summary = html.escape(summary)
            
            if is_main:
                news_result += f"▪️ <a href='{link}'><b>{clean_title}</b></a>\n"
                news_result += f"   💡 <i>{clean_summary}</i>\n\n"
            else:
                news_result += f"  └ <a href='{link}'>{clean_title}</a>\n"
                news_result += f"    💡 <i>{clean_summary}</i>\n"
                
        return news_result if news_result else "뉴스를 찾을 수 없습니다.\n"
    except:
        return "뉴스 로딩 실패\n"

def get_economy_news():
    # 네이버에 '증시 경제 종합'이라고 검색한 결과를 가져옵니다.
    return get_naver_news("증시 경제 종합", is_main=True)

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
        
        # 한국 주식 수급(외국인/기관) 긁어오기
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
        
        # 종목별 뉴스 1개 긁어오기 (네이버 뉴스 활용!)
        result += get_naver_news(name, is_main=False)
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
    
    briefing = f"🌅 <b>[에드워드 모닝 브리핑]</b>\n\n"
    briefing += f"📍 <b>오늘의 날씨</b>\n{weather_info}\n\n"
    briefing += f"────────────────\n"
    briefing += f"📊 <b>주요 시장 지수</b>\n{market_indices}\n"
    briefing += f"────────────────\n"
    briefing += f"📰 <b>주요 경제 뉴스</b>\n{eco_news}"
    briefing += f"────────────────\n"
    briefing += f"📈 <b>관심 종목 & 관련 뉴스</b>\n\n{vip_stocks}"
    
    send_telegram(briefing)
