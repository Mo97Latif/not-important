from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import csv
import re
import os  # مكتبة للتعامل مع نظام التشغيل

# إعدادات المتصفح
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
city = input("Enter City Name copy and paste <ras-el-kanayis> or <marsa-matruh>: ").strip()
if city == "ras-el-kanayis":
    city_code = "129353"
elif city == "marsa-matruh":
    city_code = "129332"
else:
    print("Please enter ras-el-kanayis or marsa-matruh only")
url = f"https://www.accuweather.com/ar/eg/{city}/{city_code}/hourly-weather-forecast/{city_code}?day=2"

filename = f"tomorrow_wind_forecast_{city}.csv"
weather_data = []

try:
    driver.get(url)
    time.sleep(5) 

    cards = driver.find_elements(By.CSS_SELECTOR, ".accordion-item, .hourly-card-n")
    
    print(f"--- جاري استخراج وتنظيف بيانات {len(cards)} ساعة ---")

    for card in cards:
        full_text = card.text.replace('\n', ' ')
        if not full_text.strip():
            continue

        # تنظيف الوقت: استخراج الرقم الأول وحرف (ص/م) فقط
        time_match = re.search(r'(\d+)\s*([صم])', full_text)
        
        if time_match:
            clean_time = f"{time_match.group(1)} {time_match.group(2)}"
            
            # استخراج الرياح
            wind_info = "غير متوفر"
            if "الرياح" in full_text:
                after_wind = full_text.split("الرياح")[-1].strip()
                wind_match = re.search(r'(.*?كم/س)', after_wind)
                if wind_match:
                    wind_info = wind_match.group(1).strip()
                else:
                    wind_info = " ".join(after_wind.split()[:2])
            
            weather_data.append([clean_time, wind_info])

    # حفظ الملف
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['الوقت', 'الرياح'])
        writer.writerows(weather_data)

    print(f"\n✅ تم الحفظ بنجاح. جاري فتح الملف...")

    # --- فتح الملف تلقائياً بناءً على نوع نظام التشغيل ---
    if os.name == 'nt': # لنظام ويندوز
        os.startfile(filename)
    else: # لنظام ماك أو لينكس
        import subprocess
        subprocess.call(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', filename])

finally:
    driver.quit()
