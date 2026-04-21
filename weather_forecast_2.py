from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import csv
import re
import os
import subprocess
import random  # مكتبة لتوليد الأرقام العشوائية
from datetime import datetime, timedelta

# إعدادات المتصفح
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# قاموس الترجمة للاتجاهات
translations = {
    'شمالية شرقية': 'North East',
    'شمالية غربية': 'North West',
    'جنوبية شرقية': 'South East',
    'جنوبية غربية': 'South West',
    'شمالية': 'North',
    'جنوبية': 'South',
    'شرقية': 'East',
    'غربية': 'West',
    'شمال': 'North',
    'جنوب': 'South',
    'شرق': 'East',
    'غرب': 'West',
    'م': 'PM',
    'ص': 'AM'
}

# قاموس زوايا الرياح (القيمة المركزية)
direction_angles = {
    'North': 0.0,
    'North North East': 22.5,
    'North East': 45.0,
    'East North East': 67.5,
    'East': 90.0,
    'East South East': 112.5,
    'South East': 135.0,
    'South South East': 157.5,
    'South': 180.0,
    'South South West': 202.5,
    'South West': 225.0,
    'West South West': 247.5,
    'West': 270.0,
    'West North West': 292.5,
    'North West': 315.0,
    'North North West': 337.5
}

def translate_direction(text):
    for arabic, english in translations.items():
        text = text.replace(arabic, english)
    return text.strip()

def get_random_angle(direction_name):
    """توليد زاوية عشوائية ضمن نطاق +- 5 درجات"""
    base_angle = direction_angles.get(direction_name)
    if base_angle is None:
        return "N/A"
    
    # توليد قيمة عشوائية بين -5 و +5 وإضافتها للزاوية الأساسية
    random_offset = random.uniform(-5.0, 5.0)
    final_angle = base_angle + random_offset
    
    # معالجة زاوية الشمال لتظل ضمن نطاق 0-360
    if final_angle < 0:
        final_angle += 360
    elif final_angle >= 360:
        final_angle -= 360
        
    return round(final_angle, 1)

# حساب تاريخ الغد
tomorrow_dt = datetime.now() + timedelta(days=1)
tomorrow_str = tomorrow_dt.strftime('%d/%m/%Y')

driver = webdriver.Chrome(options=chrome_options)

while True:
    city_index = input("Select the City (enter 1 to select Ras-El-Kanayis or  2 to select Marsa-Matruh): ").strip().lower()
    if city_index == "1":
        city = "ras-el-kanayis"
        city_code = "129353"
        break
    elif city_index == "2":
        city = "marsa-matruh"
        city_code = "129332"
        break
    else:
        print("Invalid city. Type 1 or 2 only")
        

url = f"https://www.accuweather.com/ar/eg/{city}/{city_code}/hourly-weather-forecast/{city_code}?day=2"

filename = f"tomorrow_wind_forecast_{city}.csv"
weather_data = []

try:
    driver.get(url)
    time.sleep(5) 

    cards = driver.find_elements(By.CSS_SELECTOR, ".accordion-item, .hourly-card-n")
    
    print(f"--- Processing Data for {city} ---")

    for card in cards:
        full_text = card.text.replace('\n', ' ')
        if not full_text.strip(): continue

        time_match = re.search(r'(\d+)\s*([صم])', full_text)
        if time_match:
            hour_int = int(time_match.group(1))
            period_ar = time_match.group(2)
            
            # 1. تنسيق الوقت
            period_en = translations.get(period_ar)
            formatted_time_12 = f"{str(hour_int).zfill(2)}:00:00 {period_en}"
            
            hour_24 = hour_int
            if period_ar == 'م' and hour_int != 12:
                hour_24 += 12
            elif period_ar == 'ص' and hour_int == 12:
                hour_24 = 0
            
            date_and_time_merged = f"{tomorrow_str} {str(hour_24).zfill(2)}:00"
            
            # 2. استخراج الرياح والزاوية العشوائية
            wind_speed = "N/A"
            wind_direction = "N/A"
            wind_angle = "N/A"
            
            if "الرياح" in full_text:
                after_wind = full_text.split("الرياح")[-1].strip()
                wind_match = re.search(r'(.*?)\s*(\d+)\s*كم/س', after_wind)
                
                if wind_match:
                    raw_direction = wind_match.group(1).strip()
                    wind_speed = wind_match.group(2).strip()
                    wind_direction = translate_direction(raw_direction)
                    wind_angle = get_random_angle(wind_direction)
                else:
                    parts = after_wind.split()
                    if len(parts) >= 2:
                        wind_direction = translate_direction(parts)
                        wind_angle = get_random_angle(wind_direction)
                        speed_find = re.search(r'\d+', after_wind)
                        if speed_find: wind_speed = speed_find.group()
            
            weather_data.append([tomorrow_str, formatted_time_12, date_and_time_merged, wind_speed, wind_direction, wind_angle])
            print(f"Captured: {formatted_time_12} | Dir: {wind_direction} | Angle: {wind_angle}")

    # حفظ الملف مع العمود الأخير الجديد
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
        writer.writerows(weather_data)

    print(f"\n✅ Success! File opened: {filename}")

    if os.name == 'nt':
        os.startfile(filename)
    else:
        opener = 'open' if os.uname().sysname == 'Darwin' else 'xdg-open'
        subprocess.call([opener, filename])

finally:
    driver.quit()
