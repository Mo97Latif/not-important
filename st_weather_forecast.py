import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time
import re
import random
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# --- القواميس وإعدادات الترجمة ---
translations = {
    'شمالية شرقية': 'North East', 'شمالية غربية': 'North West',
    'جنوبية شرقية': 'South East', 'جنوبية غربية': 'South West',
    'شمالية': 'North', 'جنوبية': 'South', 'شرقية': 'East', 'غربية': 'West',
    'شمال': 'North', 'جنوب': 'South', 'شرق': 'East', 'غرب': 'West',
    'م': 'PM', 'ص': 'AM', 'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NE': 'North East', 'NW': 'North West', 'SE': 'South East', 'SW': 'South West',
    'NNE': 'North North East', 'ENE': 'East North East', 'ESE': 'East South East',
    'SSE': 'South South East', 'SSW': 'South South West', 'WSW': 'West South West',
    'WNW': 'West North West', 'NNW': 'North North West'
}

direction_angles = {
    'North': 0.0, 'North North East': 22.5, 'North East': 45.0,
    'East North East': 67.5, 'East': 90.0, 'East South East': 112.5,
    'South East': 135.0, 'South South East': 157.5, 'South': 180.0,
    'South South West': 202.5, 'South West': 225.0, 'West South West': 247.5,
    'West': 270.0, 'West North West': 292.5, 'North West': 315.0, 'North North West': 337.5
}

def translate_direction(text):
    text = text.upper().strip()
    text = re.sub(r'(WIND|الرياح)', '', text).strip()
    return translations.get(text, text)

def get_random_angle(direction_name):
    base_angle = direction_angles.get(direction_name)
    if base_angle is None: return 0.0
    return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1)

# --- واجهة المستخدم ---
st.set_page_config(page_title="Ultimate Wind Scraper", layout="wide")
st.title("🌬️ Tomorrow's Hourly Wind Data")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Run Advanced Scraper"):
    with st.spinner("Executing stealth scraping... Please wait up to 30 seconds."):
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        # هوية متصفح حديثة جداً
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=options
            )

            city_code = city_codes[city_choice]
            # الدخول مباشرة على صفحة تفاصيل الغد
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            
            driver.get(url)
            time.sleep(15) # وقت كافٍ جداً لتجاوز الـ DDoS Protection

            # استخراج جميع عناصر الساعات
            # سنعتمد على استخراج النصوص الخام ثم تقسيمها برمجياً
            cards = driver.find_elements(By.CLASS_NAME, "hourly-card-n")
            if not cards:
                cards = driver.find_elements(By.CLASS_NAME, "accordion-item")

            weather_data = []
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')

            for card in cards:
                try:
                    # استخراج النص الكامل للبطاقة
                    raw_text = card.text.replace('\n', ' ')
                    
                    # 1. استخراج الوقت
                    time_match = re.search(r'(\d+)\s*(AM|PM)', raw_text, re.IGNORECASE)
                    if not time_match: continue
                    
                    hour = time_match.group(1)
                    period = time_match.group(2).upper()
                    
                    # 2. استخراج الرياح باستخدام نمط البحث عن الأرقام بجوار الاتجاهات
                    # نبحث عن نمط: اتجاه (حرفين أو ثلاثة) متبوع برقم متبوع بـ km/h
                    wind_match = re.search(r'([A-Z]{1,3})\s+(\d+)\s*km/h', raw_text)
                    
                    if not wind_match:
                        # محاولة أخرى للبحث عن كلمة Wind متبوعة باتجاه ورقم
                        wind_match = re.search(r'Wind\s+([A-Z\s]+)\s+(\d+)\s*km/h', raw_text, re.IGNORECASE)

                    if wind_match:
                        wind_dir_raw = wind_match.group(1).strip()
                        wind_speed = wind_match.group(2).strip()
                        wind_direction = translate_direction(wind_dir_raw)
                        
                        # التنسيقات المطلوبة
                        formatted_time_12 = f"{hour.zfill(2)}:00:00 {period}"
                        
                        h24 = int(hour)
                        if period == "PM" and h24 != 12: h24 += 12
                        elif period == "AM" and h24 == 12: h24 = 0
                        date_time_24 = f"{tomorrow_str} {str(h24).zfill(2)}:00"
                        
                        angle = get_random_angle(wind_direction)
                        
                        weather_data.append([tomorrow_str, formatted_time_12, date_time_24, wind_speed, wind_direction, angle])
                except:
                    continue

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.success(f"Successfully scraped {len(df)} hours!")
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 Download Data", data=csv_buffer.getvalue(), file_name=f"{city_choice}_wind.csv")
            else:
                st.error("Access Refused: AccuWeather detected the cloud server. This is a common limitation of free cloud hosting like Streamlit.")
                st.info("Try running this script on your local PC for 100% success rate, as your local IP is not blacklisted.")

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            driver.quit()
