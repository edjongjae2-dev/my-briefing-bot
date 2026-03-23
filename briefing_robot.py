import requests
from bs4 import BeautifulSoup
import os

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# ☀️ 1. 날씨 정보 (한글 깨짐 없는 버전)
def get_weather():
    try:
        url = "https://wttr.in/Seoul?format=%t+%C"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.text.strip()
            # 간단 번역
            data = data.replace("Partly cloudy", "구름 조금").replace("Clear", "맑음").replace("Cloudy", "흐림").replace("Overcast", "매우 흐림")
            return f"🌡️ 현재 서울: {data}"
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"
    except:
        return "날씨 정보 연결 일시 오류"

# 📰 2. 경제 뉴스 (차단 없는 구글 뉴스 RSS 방식)
def get_economy_news():
    # 구글 뉴스 한국어 경제 섹션 RSS 주소입니다. (가장 차단이 안 되는 안전한 곳!)
    rss_url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        res = requests.get(rss_url, headers=headers, timeout=15)
        # XML 데이터를 분석합니다.
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')
        
        news_result = ""
        count = 0
        for item in items:
            title = item.title.text.strip()
            # 구글 뉴스 제목은 뒤에 ' - 매일경제' 같은 언론사명이 붙으므로 깔끔하게 잘라줍니다.
            clean_title = title.rsplit(' - ', 1)[0]
            link = item.link.text.strip()
            
            news_result += f"{count+1}. {clean_title}\n🔗 {link}\n\n"
            count += 1
            if count == 5: break # 5개만 가져오기
            
        return news_result if news_result else "현재 새로운 경제 뉴스가 없습니다."
    except Exception as e:
        return "뉴스 서버가 현재 응답하지 않습니다. 잠시 후 다시 시도해 주세요. 😥"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "disable_web_page_preview": True 
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather = get_weather()
    news = get_economy_news()
    
    briefing = f"🌅 [에드워드 경제 브리핑]\n\n"
    briefing += f"📍 서울 날씨\n{weather}\n"
    briefing += f"──────────────────\n"
    briefing += f"📈 실시간 주요 경제 뉴스\n\n{news}"
    
    send_telegram(briefing)
