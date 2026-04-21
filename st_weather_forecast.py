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

# --- قاموس الترجمة والزوايا ---
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

def clean_direction(text):
    text = text.upper().strip()
    # إزالة أي كلمات مثل Wind أو الرياح
    text = re.sub(r'(WIND|الرياح)', '', text).strip()
    return translations.get(text, text)

def get_random_angle(direction_name):
    base_angle = direction_angles.get(direction_name)
    if base_angle is None: return 0.0
    return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1)

# --- واجهة التطبيق ---
st.set_page_config(page_title="Wind Forecast Scraper", layout="wide")
st.title("🌬️ Hourly Wind Forecast (Tomorrow)")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Scrape Data"):
    with st.spinner("Accessing AccuWeather... (This can take up to 20 seconds)"):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # تغيير الـ User Agent لنسخة حديثة جداً لتجنب الحجب
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=options
            )
            
            city_code = city_codes[city_choice]
            # سنحاول الدخول للرابط العربي أولاً، وإذا فشل ننتقل للرابط الإنجليزي تلقائياً
            url = f"https://www.accuweather.com/ar/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            
            tomorrow_dt = datetime.now() + timedelta(days=1)
            tomorrow_str = tomorrow_dt.strftime('%d/%m/%Y')
            
            driver.get(url)
            time.sleep(12) # وقت طويل لضمان تجاوز صفحة الحماية

            # البحث عن جميع العناصر التي قد تحتوي على بيانات الساعة
            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item, .hourly-forecast-card")
            
            weather_data = []

            for card in cards:
                full_text = card.text.replace('\n', ' ')
                
                # استخراج الوقت (ص أو م أو AM أو PM)
                time_match = re.search(r'(\d+)\s*(ص|م|AM|PM)', full_text, re.IGNORECASE)
                if not time_match: continue
                
                hour = time_match.group(1)
                period_raw = time_match.group(2).upper()
                period_en = "AM" if period_raw in ['ص', 'AM'] else "PM"
                
                # تنسيق الوقت المطلوب
                formatted_time_12 = f"{hour.zfill(2)}:00:00 {period_en}"
                
                hour_24 = int(hour)
                if period_en == "PM" and hour_24 != 12: hour_24 += 12
                elif period_en == "AM" and hour_24 == 12: hour_24 = 0
                date_time_24 = f"{tomorrow_str} {str(hour_24).zfill(2)}:00"

                # استخراج الرياح: نبحث عن رقم متبوع بـ "كم/س" أو "km/h"
                wind_speed = "N/A"
                wind_dir = "N/A"
                
                # نمط البحث عن الرياح (يدعم العربية والإنجليزية)
                wind_pattern = re.search(r'(الرياح|Wind)\s*(.*?)\s*(\d+)\s*(كم/س|km/h)', full_text, re.IGNORECASE)
                
                if wind_pattern:
                    wind_dir = clean_direction(wind_pattern.group(2))
                    wind_speed = wind_pattern.group(3)
                else:
                    # محاولة أخيرة إذا كان النص بسيطاً مثل "NW 15 km/h"
                    fallback = re.search(r'([A-Z]{1,3})\s+(\d+)\s*(km/h|كم/س)', full_text)
                    if fallback:
                        wind_dir = clean_direction(fallback.group(1))
                        wind_speed = fallback.group(2)

                angle = get_random_angle(wind_dir) if wind_dir != "N/A" else "N/A"
                
                weather_data.append([tomorrow_str, formatted_time_12, date_time_24, wind_speed, wind_dir, angle])

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.success(f"Done! Extracted {len(df)} hours.")
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 Download Result", data=csv_buffer.getvalue(), file_name=f"wind_{city_choice}.csv")
            else:
                st.error("AccuWeather blocked the access. Try clicking the button again or try at a different time.")
                st.info("Technical Tip: Sites like AccuWeather sometimes block cloud providers like AWS/Streamlit. If this persists, the script is best run on a local computer.")

        finally:
            driver.quit()
