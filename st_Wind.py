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

# --- القواميس وإعدادات الاتجاهات ---
translations = {
    'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NE': 'North East', 'NW': 'North West', 'SE': 'South East', 'SW': 'South West',
    'ENE': 'East North East', 'ESE': 'East South East', 'WNW': 'West North West', 'WSW': 'West South West',
    'NNE': 'North North East', 'NNW': 'North North West', 'SSE': 'South South East', 'SSW': 'South South West',
    'م': 'PM', 'ص': 'AM'
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
    return translations.get(text, text)

def get_random_angle(direction_name):
    base_angle = None
    for key in direction_angles:
        if key in direction_name:
            base_angle = direction_angles[key]
            break
    return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1) if base_angle is not None else 0.0

# --- واجهة Streamlit ---
st.set_page_config(page_title="Wind Scraper - Force Metric", page_icon="🌬️")
st.title("🌬️ Wind Forecast (Injection Mode)")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("🚀 Start Final Extraction"):
    with st.spinner("Injecting Metric configuration directly into browser memory..."):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)
            
            # 1. الدخول للموقع (نفتح الصفحة الرئيسية أولاً لتجهيز الدومين)
            driver.get("https://www.accuweather.com/")
            time.sleep(5)

            # 2. حقن الإعدادات برمجياً (تجاوز الواجهة تماماً)
            st.write("⚙️ Injecting Metric preference...")
            driver.execute_script("""
                localStorage.setItem('awx_unit', 'm');
                localStorage.setItem('isMetric', 'true');
                document.cookie = "u=1; domain=.accuweather.com; path=/; expires=Fri, 31 Dec 9999 23:59:59 GMT";
            """)
            time.sleep(2)

            # 3. الانتقال مباشرة لصفحة الطقس
            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            driver.get(url)
            time.sleep(8)

            # لقطة شاشة للتحقق من الوحدات
            st.subheader("📸 Server Screenshot Status")
            st.image(driver.get_screenshot_as_png(), caption="Checking if injection worked (KM/H vs MPH)")

            # 4. استخراج البيانات
            driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(3)
            
            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            weather_data = []
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')

            for card in cards:
                try:
                    text = card.text.replace('\n', ' ')
                    time_match = re.search(r'(\d+)\s*(AM|PM)', text, re.IGNORECASE)
                    wind_match = re.search(r'Wind\s+([A-Z]{1,3})\s+(\d+)\s*(mph|km/h)', text, re.IGNORECASE)

                    if time_match and wind_match:
                        hour, period = time_match.groups()
                        dir_raw, speed_raw, unit = wind_match.groups()
                        
                        speed_val = float(speed_raw)
                        # تحويل رياضي احتياطي إجباري (Safety Net)
                        if unit.lower() == 'mph':
                            speed_val = round(speed_val * 1.60934, 1)
                        
                        direction = clean_direction(dir_raw.upper())
                        formatted_time_12 = f"{hour.zfill(2)}:00:00 {period.upper()}"
                        
                        h24 = int(hour)
                        if period.upper() == "PM" and h24 != 12: h24 += 12
                        elif period.upper() == "AM" and h24 == 12: h24 = 0
                        date_time_24 = f"{tomorrow_str} {str(h24).zfill(2)}:00"
                        
                        angle = get_random_angle(direction)
                        weather_data.append([tomorrow_str, formatted_time_12, date_time_24, speed_val, direction, angle])
                except: continue

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.success(f"Successfully extracted {len(df)} forecast hours.")
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 Download Final Report", data=csv_buffer.getvalue(), file_name=f"wind_{city_choice}.csv")
            else:
                st.error("Extraction failed. Check the screenshot above.")

        except Exception as e:
            st.error(f"Critical Error: {e}")
        finally:
            if 'driver' in locals(): driver.quit()
