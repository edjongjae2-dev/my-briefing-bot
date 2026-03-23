import requests
from bs4 import BeautifulSoup
import os

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# ☀️ 1. 날씨 정보 (깨짐 방지 설정)
def get_weather():
    try:
        # 영문 데이터를 가져와서 한글로 직접 매칭합니다 (가장 확실한 방법)
        url = "https://wttr.in/Seoul?format=%t+%C"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8' # 한글 깨짐 방지
        if res.status_code == 200:
            weather_data = res.text.strip()
            # 간단한 번역 추가
            weather_data = weather_data.replace("Partly cloudy", "구름 조금")
            weather_data = weather_data.replace("Clear", "맑음")
            weather_data = weather_data.replace("Cloudy", "흐림")
            return f"🌡️ 현재 서울: {weather_data}"
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"
    except:
        return "날씨 정보 연결 일시 오류"

# 📰 2. 경제 뉴스 (차단 없는 연합뉴스 비밀 통로)
def get_economy_news():
    # 연합뉴스는 보안이 강력해서 로봇이 들어가기 가장 좋은 통로입니다.
    rss_url = "https://www.yonhapnewstv.co.kr/browse/feed/" 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
    
    try:
        res = requests.get(rss_url, headers=headers, timeout=15)
        # XML 구조를 더 꼼꼼하게 분석합니다
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')
        
        news_result = ""
        count = 0
        for item in items:
            title = item.title.text.strip()
            link = item.link.text.strip()
            # 경제 관련 키워드가 있는 뉴스만 골라내거나, 최신순으로 5개만 가져옵니다.
            news_result += f"{count+1}. {title}\n🔗 {link}\n\n"
            count += 1
            if count == 5: break
            
        return news_result if news_result else "현재 새로운 뉴스가 없습니다."
    except Exception as e:
        return "뉴스 서버가 응답하지 않습니다. 잠시 후 다시 시도해 주세요. 😥"

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
    briefing += f"📈 실시간 주요 뉴스\n\n{news}"
    
    send_telegram(briefing)
