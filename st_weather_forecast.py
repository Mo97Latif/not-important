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

# --- Configuration & Translation Dictionaries ---
translations = {
    'شمالية شرقية': 'North East', 'شمالية غربية': 'North West',
    'جنوبية شرقية': 'South East', 'جنوبية غربية': 'South West',
    'شمالية': 'North', 'جنوبية': 'South', 'شرقية': 'East', 'غربية': 'West',
    'شمال': 'North', 'جنوب': 'South', 'شرق': 'East', 'غرب': 'West',
    'م': 'PM', 'ص': 'AM'
}

direction_angles = {
    'North': 0.0, 'North North East': 22.5, 'North East': 45.0,
    'East North East': 67.5, 'East': 90.0, 'East South East': 112.5,
    'South East': 135.0, 'South South East': 157.5, 'South': 180.0,
    'South South West': 202.5, 'South West': 225.0, 'West South West': 247.5,
    'West': 270.0, 'West North West': 292.5, 'North West': 315.0, 'North North West': 337.5
}

def translate_direction(text):
    for arabic, english in translations.items():
        text = text.replace(arabic, english)
    return text.strip()

def get_random_angle(direction_name):
    base_angle = direction_angles.get(direction_name)
    if base_angle is None: return 0.0
    final_angle = (base_angle + random.uniform(-5.0, 5.0)) % 360
    return round(final_angle, 1)

# --- Streamlit UI ---
st.set_page_config(page_title="Wind Scraper Optimized", page_icon="🌬️")
st.title("🌬️ Tomorrow's Wind Forecast Scraper")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Start Scraping"):
    with st.spinner("Bypassing security... please wait."):
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )

            city_code = city_codes[city_choice]
            # استخدام الرابط الإنجليزي أحياناً يكون أسهل في القشط وأقل حماية
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            
            tomorrow_dt = datetime.now() + timedelta(days=1)
            tomorrow_str = tomorrow_dt.strftime('%d/%m/%Y')
            
            driver.get(url)
            time.sleep(10) # وقت كافٍ لتجاوز الحماية
            
            # محاولة النقر على جميع الأزرار لتوسيع البيانات (لسحب الرياح المخفية)
            expand_buttons = driver.find_elements(By.CSS_SELECTOR, ".accordion-item-header, .hourly-card-n")
            for btn in expand_buttons[:15]: # توسيع أول 15 ساعة كمثال
                try: driver.execute_script("arguments.click();", btn)
                except: pass
            
            time.sleep(2)
            
            cards = driver.find_elements(By.CSS_SELECTOR, ".accordion-item, .hourly-card-n")
            weather_data = []

            for card in cards:
                text = card.text.replace('\n', ' ')
                
                # البحث عن الوقت (يدعم English/Arabic)
                time_match = re.search(r'(\d+)\s*(AM|PM|ص|م)', text, re.IGNORECASE)
                if not time_match: continue
                
                hour_int = int(time_match.group(1))
                period = time_match.group(2).upper()
                
                # توحيد التوقيت لـ AM/PM
                period_en = "AM" if period in ["ص", "AM"] else "PM"
                formatted_time_12 = f"{str(hour_int).zfill(2)}:00:00 {period_en}"
                
                # تحويل لـ 24 ساعة
                hour_24 = hour_int
                if period_en == 'PM' and hour_int != 12: hour_24 += 12
                elif period_en == 'AM' and hour_int == 12: hour_24 = 0
                date_time_merged = f"{tomorrow_str} {str(hour_24).zfill(2)}:00"
                
                # --- البحث عن الرياح بنمط مرن جداً ---
                # نبحث عن نمط: اتجاه متبوع برقم متبوع بـ km/h أو كم/س
                wind_speed, wind_direction, wind_angle = "N/A", "N/A", "N/A"
                
                # محاولة استخراج الرياح من النص الإنجليزي (لأننا غيرنا الرابط للأسرع)
                wind_match = re.search(r'Wind\s+([a-zA-Z\s]+)\s+(\d+)\s*km/h', text, re.IGNORECASE)
                if not wind_match:
                    # محاولة استخراج من النص العربي كخيار احتياطي
                    wind_match = re.search(r'الرياح\s*(.*?)\s*(\d+)\s*كم/س', text)

                if wind_match:
                    wind_direction = translate_direction(wind_match.group(1).strip())
                    wind_speed = wind_match.group(2).strip()
                    wind_angle = get_random_angle(wind_direction)

                weather_data.append([tomorrow_str, formatted_time_12, date_time_merged, wind_speed, wind_direction, wind_angle])

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 Download CSV", data=csv_buffer.getvalue(), file_name=f"wind_{city_choice}.csv")
            else:
                st.error("No data extracted. The site structure might have changed or access is blocked.")

        finally:
            driver.quit()
