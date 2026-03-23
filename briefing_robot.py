import requests
from bs4 import BeautifulSoup
import os

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# ☀️ 1. 날씨 정보 (더 튼튼한 오픈 API 방식)
def get_weather():
    try:
        # 서울 날씨를 가져오는 공용 주소입니다.
        url = "https://wttr.in/Seoul?format=%c+%t+%C+미세먼지:%mp"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.text.strip()
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"
    except:
        return "날씨 서버 연결 실패 😥"

# 📰 2. 경제 뉴스 (차단 없는 '비밀 통로' RSS 방식)
def get_economy_news():
    # 매경 경제 뉴스 RSS (로봇에게 아주 친절한 주소입니다)
    rss_url = "https://www.mk.co.kr/rss/30100041/" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(rss_url, headers=headers, timeout=10)
        # XML(뉴스 데이터) 분석 시작
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')
        
        news_result = ""
        for i, item in enumerate(items[:5], 1): # 최신 뉴스 5개만!
            title = item.title.text.strip()
            link = item.link.text.strip()
            news_result += f"{i}. {title}\n🔗 {link}\n\n"
            
        return news_result if news_result else "현재 새로운 뉴스가 없습니다."
    except Exception as e:
        return "뉴스를 가져오는 통로가 막혔습니다. 😥"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "disable_web_page_preview": True # 링크 미리보기 꺼서 깔끔하게!
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather = get_weather()
    news = get_economy_news()
    
    briefing = f"🌅 [에드워드 경제 브리핑]\n\n"
    briefing += f"📍 서울 날씨 정보\n{weather}\n"
    briefing += f"──────────────────\n"
    briefing += f"📈 오늘의 주요 경제 뉴스\n\n{news}"
    
    send_telegram(briefing)
