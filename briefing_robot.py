import requests
import os
import re
import xml.etree.ElementTree as ET # 🌟 에러 나던 돋보기 대신, 파이썬 기본 튼튼한 리더기 장착!

# 🔐 금고 설정
token = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# ☀️ 1. 날씨 정보 (이상한 기호 Â 청소 기능 추가)
def get_weather():
    try:
        url = "https://wttr.in/Seoul?format=%t+%C"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8' # 한글 깨짐 방지
        
        if res.status_code == 200:
            data = res.text.strip()
            data = data.replace("Â", "") # 🌟 에러 났던 이상한 기호 삭제!
            
            # 간단 번역
            data = data.replace("Partly cloudy", "구름 조금").replace("Clear", "맑음").replace("Cloudy", "흐림").replace("Overcast", "매우 흐림").replace("Light rain", "약한 비")
            return f"🌡️ 현재 서울: {data}"
        return "날씨 정보를 읽어오는 중입니다.. 🌤️"
    except:
        return "날씨 정보 연결 일시 오류"

# 📰 2. 경제 뉴스 (구글 뉴스 + 기본 리더기 조합 = 절대 실패 안 함)
def get_economy_news():
    url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        
        # 🌟 에러의 주범이었던 BeautifulSoup 대신, 파이썬 기본 내장 모듈 사용!
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        
        news_result = ""
        count = 0
        for item in items:
            title = item.find('title').text.strip()
            clean_title = re.sub(r' - [^ -]+$', '', title) # 언론사 이름 자르기
            link = item.find('link').text.strip()
            
            news_result += f"{count+1}. {clean_title}\n🔗 {link}\n\n"
            count += 1
            if count == 5: break
            
        if not news_result:
            return "현재 새로운 뉴스를 찾을 수 없습니다."
        return news_result
        
    except Exception as e:
        # 혹시라도 에러가 나면 무슨 에러인지 텔레그램으로 바로 알려주도록 설정
        return f"뉴스 로딩 중 에러가 발생했습니다: {str(e)}"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "disable_web_page_preview": True 
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
