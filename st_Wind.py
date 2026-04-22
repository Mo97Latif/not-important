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
import requests

# --- وظيفة جلب بروكسيات مجانية ---
def get_free_proxies():
    """يجلب قائمة بروكسيات مجانية من مصدر خارجي"""
    try:
        # نستخدم API مجاني لجلب بروكسيات HTTP
        url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            proxies = response.text.strip().split("\r\n")
            return [p for p in proxies if p]
    except Exception:
        return []
    return []

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
    for ar, en in translations.items():
        text = text.replace(ar, en)
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
st.set_page_config(page_title="Wind Scraper Proxy Edition", page_icon="🌬️")
st.title("🌬️ Tomorrow's Wind Forecast Scraper")
st.write("Current Strategy: **Cloud Browser + Free Proxy Rotation**")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Start Scraping (Using Proxy)"):
    proxies = get_free_proxies()
    
    with st.spinner("Initializing Stealth Browser..."):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        
        # إضافة بروكسي عشوائي إذا نجح الجلب
        current_proxy = None
        if proxies:
            current_proxy = random.choice(proxies)
            chrome_options.add_argument(f'--proxy-server={current_proxy}')
            st.info(f"🌐 Connected via Proxy: `{current_proxy}`")
        else:
            st.warning("⚠️ No free proxies found, trying direct connection...")

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )
            
            # زيادة مهلة التحميل لأن البروكسي قد يكون بطيئاً
            driver.set_page_load_timeout(45)
            
            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            
            tomorrow_dt = datetime.now() + timedelta(days=1)
            tomorrow_str = tomorrow_dt.strftime('%d/%m/%Y')
            
            driver.get(url)
            
            # الانتظار الذكي لظهور بيانات الرياح
            wait = WebDriverWait(driver, 25)
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Wind') or contains(text(), 'الرياح')]")))

            # تمرير الصفحة لتفعيل المحتوى الديناميكي
            driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(5)

            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            weather_data = []

            for card in cards:
                try:
                    full_text = card.text.replace('\n', ' ')
                    time_match = re.search(r'(\d+)\s*(AM|PM|ص|م)', full_text, re.IGNORECASE)
                    if not time_match: continue
                    
                    hour = time_match.group(1)
                    period_raw = time_match.group(2).upper()
                    period_en = "AM" if period_raw in ["AM", "ص"] else "PM"

                    # البحث عن سرعة واتجاه الرياح
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
                st.success(f"✅ Extracted {len(df)} hours of data!")
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 Download Results", data=csv_buffer.getvalue(), file_name=f"wind_{city_choice}.csv")
            else:
                st.error("❌ Data not found. This proxy might be blocked or the page structure changed.")

        except Exception as e:
            st.error(f"⚠️ Scraping failed: {e}")
            st.info("Free proxies often fail. Try clicking the button again to rotate to a new proxy.")
        finally:
            if 'driver' in locals():
                driver.quit()
