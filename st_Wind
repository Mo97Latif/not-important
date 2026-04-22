import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    'م': 'PM', 'ص': 'AM', 'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West'
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
    for arabic, english in translations.items():
        text = text.replace(arabic, english)
    return text

def get_random_angle(direction_name):
    base_angle = direction_angles.get(direction_name)
    if base_angle is None:
        for key in direction_angles:
            if key in direction_name:
                base_angle = direction_angles[key]
                break
    if base_angle is None: return 0.0
    return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1)

# --- واجهة Streamlit ---
st.set_page_config(page_title="Wind Forecast Scraper", page_icon="🌬️")
st.title("🌬️ Tomorrow's Wind Forecast Scraper")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Start Scraping"):
    with st.spinner("Initializing Stealth Browser & Waiting for Data..."):
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        # تنكر في هوية متصفح حقيقي لتجاوز الحماية
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )
            
            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            
            tomorrow_dt = datetime.now() + timedelta(days=1)
            tomorrow_str = tomorrow_dt.strftime('%d/%m/%Y')
            
            driver.get(url)

            # --- التحديث المطلوب: الانتظار حتى ظهور بيانات الرياح ---
            try:
                # ننتظر حتى يظهر أي عنصر يحتوي على كلمة الرياح أو Wind لمدة 20 ثانية
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Wind') or contains(text(), 'الرياح')]"))
                )
            except:
                st.warning("⚠️ Time out: Wind info didn't load in time. The script will try to continue anyway.")

            # تمرير بسيط لضمان تحميل المحتوى الديناميكي
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(3)

            # استخراج البطاقات
            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            weather_data = []

            for card in cards:
                try:
                    full_text = card.text.replace('\n', ' ')
                    
                    # استخراج الوقت
                    time_match = re.search(r'(\d+)\s*(AM|PM|ص|م)', full_text, re.IGNORECASE)
                    if not time_match: continue
                    
                    hour = time_match.group(1)
                    period_raw = time_match.group(2).upper()
                    period_en = "AM" if period_raw in ["AM", "ص"] else "PM"

                    # استخراج الرياح
                    # نبحث عن نمط: اتجاه (حروف) متبوع برقم متبوع بـ km/h
                    wind_match = re.search(r'([A-Z]{1,3}|North|South|East|West|شمال|جنوب|شرق|غرب)\s+(\d+)\s*(km/h|كم/س)', full_text, re.IGNORECASE)

                    if wind_match:
                        wind_dir_raw = wind_match.group(1)
                        wind_speed = wind_match.group(2)
                        wind_direction = translate_direction(wind_dir_raw)
                        
                        formatted_time_12 = f"{hour.zfill(2)}:00:00 {period_en}"
                        h24 = int(hour)
                        if period_en == "PM" and h24 != 12: h24 += 12
                        elif period_en == "AM" and h24 == 12: h24 = 0
                        date_time_24 = f"{tomorrow_str} {str(h24).zfill(2)}:00"
                        
                        angle = get_random_angle(wind_direction)
                        weather_data.append([tomorrow_str, formatted_time_12, date_time_24, wind_speed, wind_direction, angle])
                except:
                    continue

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.success(f"✅ Successfully scraped {len(df)} hours!")
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 Download Excel/CSV", data=csv_buffer.getvalue(), file_name=f"wind_{city_choice}.csv")
            else:
                st.error("❌ No wind data found. AccuWeather might be blocking the Cloud Server IP.")

        except Exception as e:
            st.error(f"Error occurred: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
