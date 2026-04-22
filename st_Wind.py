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

# --- القواميس المعتادة ---
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
    base_angle = direction_angles.get(direction_name)
    if base_angle is None:
        for key in direction_angles:
            if key in direction_name:
                base_angle = direction_angles[key]
                break
    return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1) if base_angle is not None else 0.0

# --- واجهة Streamlit ---
st.set_page_config(page_title="AccuWeather Settings Debugger", page_icon="🌬️")
st.title("🌬️ Wind Scraper (Full Debug Mode)")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Run Scraper & Capture All Steps"):
    with st.spinner("Executing interactions and capturing screenshots..."):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)
            
            # 1. الذهاب لصفحة الإعدادات
            driver.get("https://www.accuweather.com/en/settings")
            time.sleep(5)

            # تجاوز نافذة الخصوصية
            try:
                accept_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept')]")
                driver.execute_script("arguments.click();", accept_btn)
                time.sleep(2)
            except: pass

            # 2. التفاعل مع قائمة الوحدات المخصصة
            try:
                # النقر لفتح القائمة
                unit_dropdown = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Units')]/following-sibling::div | //*[contains(text(), 'Imperial')]"))
                )
                driver.execute_script("arguments.click();", unit_dropdown)
                time.sleep(2)
                
                # النقر على خيار Metric
                metric_option = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Metric')]"))
                )
                driver.execute_script("arguments.click();", metric_option)
                time.sleep(3)
                st.write("✅ Interaction with settings menu complete.")
            except Exception as e:
                st.warning(f"Settings interaction error: {e}")

            # --- التعديل المطلوب: لقطة شاشة لصفحة الإعدادات بعد التغيير ---
            st.subheader("📸 Step 1: Settings Page Status")
            st.image(driver.get_screenshot_as_png(), caption="Verification: Did the units switch to Metric in settings?")

            # 3. الانتقال لصفحة الطقس
            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            driver.get(url)
            time.sleep(6)

            # لقطة شاشة ثانية لصفحة البيانات
            st.subheader("📸 Step 2: Hourly Forecast Page Status")
            st.image(driver.get_screenshot_as_png(), caption="Checking units (MPH/KMH) on the forecast page")

            # 4. استخراج البيانات
            driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(3)
            
            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            weather_data = []
            tomorrow_str
