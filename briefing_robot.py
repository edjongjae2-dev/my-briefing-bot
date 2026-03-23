import requests
from bs4 import BeautifulSoup
import os
import re

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# ☀️ 1. 날씨 정보 (현재 성공 중인 방식 유지)
def get_weather():
    try:
        url = "https://wttr.in/Seoul?format=%t+%C"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.text.strip()
            # 간단 번역
            data = data.replace("Partly cloudy", "구름 조금").replace("Clear", "맑음").replace("Cloudy", "흐림").replace("Overcast", "매우 흐림").replace("Light rain", "약한 비")
            return f"🌡️ 현재 서울: {data}"
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"
    except:
        return "날씨 정보 연결 일시 오류"

# 📰 2. 경제 뉴스 (절대 안 막히는 구글 뉴스 직접 파싱 방식)
def get_economy_news():
    # 구글 뉴스 경제 섹션 (한국어)
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')
        
        news_result = ""
        count = 0
        for item in items:
            title = item.title.text.strip()
            # 제목 뒤의 언론사명 제거 (예: 삼성전자 주가 상승 - 매경 -> 삼성전자 주가 상승)
            clean_title = re.sub(r' - [^ -]+$', '', title)
            link = item.link.text.strip()
            
            news_result += f"{count+1}. {clean_title}\n🔗 {link}\n\n"
            count += 1
            if count == 5: break # 딱 5개만!
            
        if not news_result:
            return "현재 새로운 뉴스를 찾을 수 없습니다."
        return news_result
    except Exception as e:
        return "뉴스 서버 접속에 실패했습니다. (Google News)"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "disable_web_page_preview": True # 링크 미리보기 꺼서 깔끔하게
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    news_info = get_economy_news()
    
    briefing = f"🌅 [에드워드 경제 브리핑]\n\n"
    briefing += f"📍 서울 날씨\n{weather_info}\n"
    briefing += f"──────────────────\n"
    briefing += f"📈 실시간 주요 경제 뉴스\n\n{news_info}"
    
    send_telegram(briefing)
