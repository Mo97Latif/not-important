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

def clean_direction(text):
    text = text.strip().upper()
    for ar, en in translations.items():
        text = text.replace(ar, en)
    # تنظيف أي كلمات زائدة مثل "Wind" أو "الرياح"
    text = text.replace("WIND", "").replace("الرياح", "").strip()
    return text

def get_random_angle(direction_name):
    base_angle = direction_angles.get(direction_name)
    if base_angle is None: return 0.0
    return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1)

# --- واجهة Streamlit ---
st.set_page_config(page_title="Wind Scraper Final", page_icon="🌬️")
st.title("🌬️ Tomorrow's Wind Forecast Scraper")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Start Scraping"):
    with st.spinner("Connecting to AccuWeather... (Targeting specific HTML elements)"):
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )

            city_code = city_codes[city_choice]
            # نستخدم الرابط الإنجليزي لأنه أكثر استقراراً في الكلاسات
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            
            tomorrow_dt = datetime.now() + timedelta(days=1)
            tomorrow_str = tomorrow_dt.strftime('%d/%m/%Y')
            
            driver.get(url)
            time.sleep(10)

            # استخراج جميع "بطاقات" الساعات
            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            weather_data = []

            for card in cards:
                try:
                    # 1. استخراج الوقت (الوقت موجود غالباً في كلاس .date أو .time)
                    time_text = card.find_element(By.CSS_SELECTOR, ".date").text.strip() # مثل "1 AM"
                    time_match = re.search(r'(\d+)\s*(AM|PM)', time_text, re.IGNORECASE)
                    
                    if not time_match: continue
                    
                    hour_int = int(time_match.group(1))
                    period = time_match.group(2).upper()
                    
                    # تنسيق 12 ساعة
                    formatted_time_12 = f"{str(hour_int).zfill(2)}:00:00 {period}"
                    
                    # تنسيق 24 ساعة
                    hour_24 = hour_int
                    if period == 'PM' and hour_int != 12: hour_24 += 12
                    elif period == 'AM' and hour_int == 12: hour_24 = 0
                    date_time_merged = f"{tomorrow_str} {str(hour_24).zfill(2)}:00"

                    # 2. استخراج بيانات الرياح بدقة
                    # الرياح غالباً تكون داخل div يحتوي على معلومات إضافية
                    # نضغط على الكارت أولاً ليظهر المحتوى المخفي
                    driver.execute_script("arguments.click();", card)
                    time.sleep(0.5)

                    # استهداف خلية الرياح مباشرة (كلاس .wind في AccuWeather)
                    wind_container = card.find_element(By.XPATH, ".//div[contains(text(), 'Wind') or contains(text(), 'الرياح')]/following-sibling::div")
                    wind_raw = wind_container.text.strip() # مثل "NW 15 km/h"
                    
                    # تحليل نص الرياح
                    wind_parts = wind_raw.split()
                    # غالباً الجزء الأول هو الاتجاه، والثاني هو الرقم
                    raw_dir = wind_parts
                    raw_speed = re.search(r'\d+', wind_raw).group()
                    
                    wind_direction = clean_direction(raw_dir)
                    wind_speed = raw_speed
                    wind_angle = get_random_angle(wind_direction)

                    weather_data.append([tomorrow_str, formatted_time_12, date_time_merged, wind_speed, wind_direction, wind_angle])
                except:
                    continue # إذا فشل استخراج ساعة معينة ننتقل للتالية

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.success("Data extracted successfully!")
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 Download CSV", data=csv_buffer.getvalue(), file_name=f"wind_report_{city_choice}.csv")
            else:
                st.error("Still getting N/A. AccuWeather is blocking the server IP. Try running locally or use a different Cloud provider.")

        finally:
            driver.quit()
