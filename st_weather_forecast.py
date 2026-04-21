import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time
import csv
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

# --- Streamlit Interface ---
st.set_page_config(page_title="Wind Scraper Pro", page_icon="🌬️")
st.title("🌬️ Tomorrow's Wind Forecast Scraper")
st.markdown("This tool bypasses anti-bot protections to get clean hourly wind data.")

city_choice = st.selectbox("Select City", ["ras-el-kanayis", "marsa-matruh"])
city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}

if st.button("Start Scraping"):
    with st.spinner("Bypassing security and fetching data... This may take a moment."):
        
        # --- Advanced Selenium Anti-Detection Setup ---
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )
            
            # Additional script to hide Selenium signature
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })

            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/ar/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            
            tomorrow_dt = datetime.now() + timedelta(days=1)
            tomorrow_str = tomorrow_dt.strftime('%d/%m/%Y')
            
            driver.get(url)
            time.sleep(10) # Wait longer for security checks to pass
            
            cards = driver.find_elements(By.CSS_SELECTOR, ".accordion-item, .hourly-card-n")
            weather_data = []

            for card in cards:
                full_text = card.text.replace('\n', ' ')
                time_match = re.search(r'(\d+)\s*([صم])', full_text)
                
                if time_match:
                    hour_int = int(time_match.group(1))
                    period_ar = time_match.group(2)
                    
                    # 1. Formatting 12hr: hh:00:00 AM/PM
                    period_en = translations.get(period_ar)
                    formatted_time_12 = f"{str(hour_int).zfill(2)}:00:00 {period_en}"
                    
                    # 2. Convert to 24hr for Merged Column
                    hour_24 = hour_int
                    if period_ar == 'م' and hour_int != 12: hour_24 += 12
                    elif period_ar == 'ص' and hour_int == 12: hour_24 = 0
                    
                    date_time_merged = f"{tomorrow_str} {str(hour_24).zfill(2)}:00"
                    
                    # 3. Wind Processing
                    wind_speed, wind_direction, wind_angle = "N/A", "N/A", "N/A"
                    if "الرياح" in full_text:
                        after_wind = full_text.split("الرياح")[-1].strip()
                        # Regex to capture Direction and Speed
                        wind_match = re.search(r'(.*?)\s*(\d+)\s*كم/س', after_wind)
                        if wind_match:
                            wind_direction = translate_direction(wind_match.group(1))
                            wind_speed = wind_match.group(2)
                            wind_angle = get_random_angle(wind_direction)

                    weather_data.append([tomorrow_str, formatted_time_12, date_time_merged, wind_speed, wind_direction, wind_angle])

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                st.success(f"Success! Captured {len(df)} hours.")
                st.dataframe(df)

                # Export to CSV
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Download Wind Data CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"wind_{city_choice}_{tomorrow_dt.strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.error("No data found. AccuWeather is still detecting the scraper. Please refresh and try again.")

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
