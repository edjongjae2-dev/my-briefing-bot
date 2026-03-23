import requests
from bs4 import BeautifulSoup
import os

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

def get_weather():
    # 서울 날씨 기준 (원하시는 지역이 있다면 '서울 날씨' 대신 넣으세요)
    url = "https://search.naver.com/search.naver?query=서울+날씨"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        temp = soup.select_one('.status_reflection .today_now').text.replace('현재 온도', '').strip()
        desc = soup.select_one('.status_reflection .before_slash').text.strip()
        dust = soup.select('.today_area .item_level')[0].text.strip() # 미세먼지
        
        return f"🌡️ 현재 기온: {temp}\n☁️ 상태: {desc}\n😷 미세먼지: {dust}"
    except:
        return "날씨 정보를 가져오지 못했습니다."

def get_news():
    url = "https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=101" # 경제 뉴스 기준
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 주요 헤드라인 5개 추출
        news_list = soup.select('.sh_text_headline')[:5]
        result = ""
        for i, news in enumerate(news_list, 1):
            title = news.text.strip()
            link = news['href']
            result += f"{i}. {title}\n🔗 {link}\n\n"
        return result
    except:
        return "뉴스 정보를 가져오지 못했습니다."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "disable_web_page_preview": True}
    requests.post(url, json=payload)

if __name__ == "__main__":
    weather = get_weather()
    news = get_news()
    
    full_msg = f"🌅 [에드워드 브리핑 도착]\n\n📍 오늘의 날씨\n{weather}\n\n───────────────\n\n📰 오늘의 주요 뉴스(경제)\n\n{news}"
    send_telegram(full_msg)
