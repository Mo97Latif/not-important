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
    'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NW': 'North West', 'NE': 'North East', 'SW': 'South West', 'SE': 'South East',
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
st.set_page_config(page_title="Wind Scraper Pro", page_icon="🌬️")
st.title("🌬️ Tomorrow's Hourly Wind Scraper")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Download File"):
    with st.spinner("Extracting data"):
        
        # --- الإعدادات الجديدة والمطورة للمتصفح ---
        chrome_options = Options()
        chrome_options.add_argument("--headless=new") # استخدام المحرك الجديد لإخفاء المتصفح
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # إخفاء هوية السيلينيوم (تخطي كشف البوتات)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # هوية متصفح حقيقي (User-Agent)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )
            
            # حقن سكريبت إضافي لمنع اكتشاف المتصفح الآلي
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            driver.get(url)

            # 1. التعامل مع نافذة الخصوصية (Privacy Popup)
            try:
                accept_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".policy-accept"))
                )
                driver.execute_script("arguments.click();", accept_btn)
                time.sleep(2)
            except:
                pass

            # 2. الانتظار حتى تحميل بيانات الساعات
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")))

            # 3. التمرير لأسفل ببطء لضمان تحميل كافة العناصر
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(5)

            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            weather_data = []
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')

            for card
