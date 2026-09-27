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

# --- Configuration & Fixed Dictionaries ---
translations = {
    'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NE': 'North East', 'NW': 'North West', 'SE': 'South East', 'SW': 'South West',
    'ENE': 'East North East', 'ESE': 'East South East', 'WNW': 'West North West', 'WSW': 'West South West',
    'NNE': 'North North East', 'NNW': 'North North West', 'SSE': 'South South East', 'SSW': 'South South West',
    'م': 'PM', 'ص': 'AM'
}

# نطاقات الزوايا الجديدة لكل اتجاه (الشمال بيمتد فوق 360 لتسهيل حسابات الـ Negative Shift والالتفاف)
direction_ranges = {
    'North': (350.0, 370.0),
    'North North East': (10.0, 30.0),
    'North East': (35.0, 55.0),
    'East North East': (55.0, 75.0),
    'East': (80.0, 100.0),
    'East South East': (100.0, 120.0),
    'South East': (125.0, 145.0),
    'South South East': (145.0, 165.0),
    'South': (170.0, 190.0),
    'South South West': (190.0, 210.0),
    'South West': (215.0, 235.0),
    'West South West': (235.0, 255.0),
    'West': (260.0, 280.0),
    'West North West': (280.0, 300.0),
    'North West': (305.0, 325.0),
    'North North West': (325.0, 345.0)
}

def clean_direction(text):
    text = text.upper().strip()
    return translations.get(text, text)

def generate_smooth_angles(records):
    """توليد زوايا متسلسلة ومستمرة طوال اليوم مع دعم الـ Negative Shift والالتفاف عند 360"""
    angles = []
    if not records:
        return angles
    
    # ابدأ بأول زاوية عشوائية داخل نطاق أول ساعة
    first_dir = records[0]['direction']
    low, high = direction_ranges.get(first_dir, (0.0, 360.0))
    current_val = random.uniform(low, high)
    angles.append(round(current_val % 360, 1))
    
    # تحديد اتجاه وزخم الحركة العام (Momentum) على مدار اليوم كله
    momentum = random.choice([-1.2, 1.2]) * random.uniform(0.6, 1.4)
    
    for i in range(1, len(records)):
        dir_name = records[i]['direction']
        low, high = direction_ranges.get(dir_name, (0.0, 360.0))
        
        # تعديل الزخم تدريجياً لضمان الاستمرارية طوال اليوم (سواء بزاوية موجبة أو سالبة)
        momentum += random.uniform(-0.6, 0.6)
        momentum = max(-2.5, min(2.5, momentum))
        
        current_val += momentum
        
        # التحقق مما إذا كانت القيمة داخل النطاق المسموح للاتجاه الحالي (مع مراعاة الـ Wrap-around)
        in_range = False
        if high > 360: # لمعالجة الشمال الذي يمر عبر 360/0
            in_range = (350.0 <= current_val <= 370.0)
        else:
            in_range = (low <= current_val <= high)
            
        # إذا خرجت القيمة عن النطاق المسموح، نقوم بسحبها بسلاسة نحو منتصف نطاق الاتجاه الجديد
        if not in_range:
            target_mid = (low + high) / 2.0
            diff = target_mid - current_val
            current_val += diff * 0.35 + random.uniform(-0.8, 0.8)
            
        angles.append(round(current_val % 360, 1))
        
    return angles

# --- Streamlit UI ---
st.set_page_config(page_title="بيانات الرياح", page_icon="🌬️")
st.title("🌬️ بيانات الرياح من طرف اخوكي لطيف 🌬️")
st.markdown("Units: **KM/H** | Format: **US Date (MM/DD/YYYY)**")

# اختيار المدينة
city_choice = st.selectbox("اختار المدينة (Select City)", ["ras-el-kanayis", "marsa-matruh", "ras-alam-el-rum"])
city_codes = {
    "ras-el-kanayis": "129353", 
    "marsa-matruh": "129332",
    "ras-alam-el-rum": "129352"
}

# اختيار اليوم
day_label = st.selectbox("اختار اليوم (Select Day)", ["Today (النهاردة)", "Tomorrow (بكرة)", "Day After Tomorrow (بعد بكرة)", "Following Day (اليوم الثالث)"])
day_map = {
    "Today (النهاردة)": 1,
    "Tomorrow (بكرة)": 2, 
    "Day After Tomorrow (بعد بكرة)": 3, 
    "Following Day (اليوم الثالث)": 4
}
selected_day_num = day_map[day_label]

if st.button("🚀 طلع لي الداتا"):
    with st.spinner("صبرك عليا يا بنتي باحسب اهو..."):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=chrome_options)
            
            # 1. ضبط الوحدات (Metric)
            driver.get("https://www.accuweather.com/en/settings")
            time.sleep(7)
            try:
                anchor = driver.find_element(By.XPATH, "//*[text()='Units']")
                actions = ActionChains(driver)
                actions.move_to_element(anchor).move_by_offset(500, 0).click().perform()
                time.sleep(1)
                actions.send_keys(Keys.ARROW_DOWN).send_keys(Keys.ENTER).perform()
                time.sleep(3)
            except:
                driver.execute_script("document.cookie = 'u=1; domain=.accuweather.com; path=/';")

            # 2. الانتقال لصفحة البيانات
            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day={selected_day_num}"
            driver.get(url)
            time.sleep(7)

            # 3. استخراج البيانات الخام
            driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(3)
            
            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            raw_records = []
            
            target_date = datetime.now() + timedelta(days=(selected_day_num - 1))
            date_us = target_date.strftime('%m/%d/%Y')

            for card in cards:
                try:
                    text = card.text.replace('\n', ' ')
                    time_match = re.search(r'(\d+)\s*(AM|PM)', text, re.IGNORECASE)
                    wind_match = re.search(r'Wind\s+([A-Z]{1,3})\s+(\d+)\s*(mph|km/h)', text, re.IGNORECASE)

                    if time_match and wind_match:
                        hour, period = time_match.groups()
                        dir_raw, speed_raw, unit = wind_match.groups()
                        speed_val = float(speed_raw)
                        
                        if unit.lower() == 'mph':
                            speed_val = round(speed_val * 1.60934, 1)
                        
                        direction_name = clean_direction(dir_raw.upper())
                        formatted_time_12 = f"{hour.zfill(2)}:00:00 {period.upper()}"
                        
                        h24 = int(hour)
                        if period.upper() == "PM" and h24 != 12: h24 += 12
                        elif period.upper() == "AM" and h24 == 12: h24 = 0
                        date_combined = f"{date_us} {str(h24).zfill(2)}:00"
                        
                        raw_records.append({
                            'date_us': date_us,
                            'formatted_time_12': formatted_time_12,
                            'date_combined': date_combined,
                            'speed': speed_val,
                            'direction': direction_name
                        })
                except: continue

            if raw_records:
                # توليد الزوايا المتسلسلة على مدار اليوم مع الـ Negative/Positive shifts والالتفاف
                smooth_angles = generate_smooth_angles(raw_records)
                
                weather_data = []
                for idx, rec in enumerate(raw_records):
                    weather_data.append([
                        rec['date_us'], 
                        rec['formatted_time_12'], 
                        rec['date_combined'], 
                        rec['speed'], 
                        rec['direction'], 
                        smooth_angles[idx]
                    ])

                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.success("✅ الداتا طلعت اهي...انزلي تحت انقري علشان تنزليها")
                st.dataframe(df)
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Wind Forecast')
                
                st.download_button(
                    label="📥 انقري هنا هتنزليه اكسيل",
                    data=output.getvalue(),
                    file_name=f"wind_forecast_{city_choice}_day_{selected_day_num}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Extraction failed. Check if the website layout changed.")

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if 'driver' in locals(): driver.quit()
