import requests
from bs4 import BeautifulSoup
import os

# 🔐 금고 설정 (이미 등록하신 secrets를 사용합니다)
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# ☀️ 1. 날씨 정보 가져오기 (네이버 날씨 검색)
def get_weather():
    try:
        url = "https://search.naver.com/search.naver?query=서울날씨"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 기온 및 상태
        temp = soup.select_one('.today_temp').text.replace('현재 온도', '').strip()
        desc = soup.select_one('.before_slash').text.strip()
        dust = soup.select('.txt_level')[0].text.strip() # 미세먼지
        
        return f"🌡️ 온도: {temp} / 🌈 상태: {desc}\n😷 미세먼지: {dust}"
    except:
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"

# 📰 2. 네이버 경제 뉴스 TOP 5 가져오기
def get_economy_news():
    try:
        url = "https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=101" # 경제 카테고리
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 최신 뉴스 헤드라인 5개 추출
        news_list = soup.select('.sh_text_headline') or soup.select('.cluster_text_headline')
        
        result = ""
        for i, news in enumerate(news_list[:5], 1):
            title = news.text.strip()
            link = news.get('href') if news.get('href') else "링크 없음"
            result += f"{i}. {title}\n🔗 {link}\n\n"
            
        return result if result else "현재 새로운 뉴스가 없습니다."
    except Exception as e:
        return f"뉴스를 가져오지 못했습니다. 😥"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "disable_web_page_preview": True}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather_info = get_weather()
    news_info = get_economy_news()
    
    briefing = f"🌅 [에드워드 브리핑 도착]\n\n"
    briefing += f"📍 오늘의 서울 날씨\n{weather_info}\n"
    briefing += f"──────────────────\n"
    briefing += f"📈 오늘의 주요 뉴스(경제)\n\n{news_info}"
    
    send_telegram(briefing)
