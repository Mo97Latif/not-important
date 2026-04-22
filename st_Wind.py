import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time
import re
import random
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# --- قواميس الترجمة والزوايا ---
import random

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
    # إزالة أي مسافات زائدة وتحويل لحروف كبيرة
    text = text.upper().strip()
    return translations.get(text, text)

def get_random_angle(direction_name):
    # البحث عن المطابقة الكاملة أولاً للحصول على أدق زاوية
    # استخدمنا .get() مباشرة بدلاً من الـ loop لتجنب أخطاء البحث الجزئي
    base_angle = direction_angles.get(direction_name)
    
    if base_angle is None:
        # إذا لم يجد مطابقة كاملة (مثلاً بسبب مسافة أو تنسيق)، يبحث عن أطول مفتاح يطابق النص
        # ترتيب المفاتيح من الأطول للأقصر يضمن صيد "North North West" قبل "North"
        sorted_keys = sorted(direction_angles.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key in direction_name:
                base_angle = direction_angles[key]
                break
                
    if base_angle is not None:
        return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1)
    
    return 0.0

# --- واجهة Streamlit ---
st.set_page_config(page_title="بيانات الرياح", page_icon="🌬️")
st.title("🌬️ Wind Forecast من طرف اخوكي لطيف 🌬️")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("🚀 طلع لي الجدول"):
    with st.spinner("صبرك عليا يا فنانة اخلص تحميل، متستعجيلينيش لأهنج منك..."):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)
            
            # 1. ضبط الوحدات عبر الإحداثيات النسبية (فكرتك الذكية)
            driver.get("https://www.accuweather.com/en/settings")
            time.sleep(7)

            try:
                # تحديد مكان كلمة Units كمرجع
                anchor = driver.find_element(By.XPATH, "//*[text()='Units']")
                actions = ActionChains(driver)
                
                # التحرك يميناً للنقر على القائمة ثم اختيار Metric
                actions.move_to_element(anchor).move_by_offset(500, 0).click().perform()
                time.sleep(1)
                actions.send_keys(Keys.ARROW_DOWN).send_keys(Keys.ENTER).perform()
                time.sleep(3)
            except:
                # حماية إضافية عبر الكوكيز في حال فشل التحرك
                driver.execute_script("document.cookie = 'u=1; domain=.accuweather.com; path=/';")

            # 2. الانتقال لصفحة البيانات
            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            driver.get(url)
            time.sleep(7)

            # 3. استخراج البيانات
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
                        
                        # ضمان التحويل للكيلومتر رياضياً في حال فشل المتصفح في التغيير
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
                st.success("✅ الجدول منور اهو، انزلي تحت بقى وانقري لتنزيل ملف الاكسيل")
                st.dataframe(df)
                
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button("📥 ايوا انقري هنا", data=csv_buffer.getvalue(), file_name=f"wind_{city_choice}.csv")
            else:
                st.error("No data found. The site structure might have changed.")

        except Exception as e:
            st.error(f"Critical Error: {e}")
        finally:
            if 'driver' in locals(): driver.quit()
