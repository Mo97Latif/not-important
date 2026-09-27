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
import shutil
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
    """
    NOTE: AccuWeather's hourly view only ever exposes a compass abbreviation
    (e.g. 'NW'), never a precise degree reading. This function SIMULATES a
    plausible continuous angle inside that compass sector - it is not a real
    measured value. Keep the column labeled clearly as estimated/simulated
    so nobody downstream mistakes it for an actual instrument reading.
    """
    angles = []
    if not records:
        return angles

    first_dir = records[0]['direction']
    low, high = direction_ranges.get(first_dir, (0.0, 360.0))
    current_val = random.uniform(low, high)
    angles.append(round(current_val % 360, 1))

    momentum = random.choice([-1.2, 1.2]) * random.uniform(0.6, 1.4)

    for i in range(1, len(records)):
        dir_name = records[i]['direction']
        low, high = direction_ranges.get(dir_name, (0.0, 360.0))

        momentum += random.uniform(-0.6, 0.6)
        momentum = max(-2.5, min(2.5, momentum))

        current_val += momentum

        in_range = False
        if high > 360:
            in_range = (350.0 <= current_val <= 370.0)
        else:
            in_range = (low <= current_val <= high)

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
st.caption("⚠️ The 'Wind Direction Angle' column is a simulated estimate inside AccuWeather's "
           "compass sector, not a measured degree value — AccuWeather never publishes exact degrees.")

city_choice = st.selectbox("اختار المدينة (Select City)", ["ras-el-kanayis", "marsa-matruh", "ras-alam-el-rum"])
city_codes = {
    "ras-el-kanayis": "129353",
    "marsa-matruh": "129332",
    "ras-alam-el-rum": "129352"
}

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

        # --- FIX: make the browser binary match the driver we ask webdriver_manager for.
        # On most Linux hosts (Streamlit Community Cloud, most Docker images) only
        # "chromium" is installed, not "google-chrome". webdriver_manager was being told
        # chrome_type=ChromeType.CHROMIUM (so it fetches a Chromium-matched driver) but
        # chrome_options never pointed Selenium at the chromium binary, so Selenium tried
        # the default google-chrome path and failed with "cannot find Chrome binary".
        chromium_binary = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if chromium_binary:
            chrome_options.binary_location = chromium_binary

        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )

            # --- REMOVED: the old "force metric units via Settings page" step.
            # It navigated to /settings, tried to click a dropdown at a hard-coded
            # pixel offset, and silently swallowed any failure with a bare `except`,
            # then guessed a cookie ('u=1') whose meaning was never actually verified.
            # It's also unnecessary: the scraper already reads whichever unit AccuWeather
            # displays (mph or km/h) per row below and converts mph -> km/h itself, so the
            # final output is correct in km/h regardless of the site's display unit.
            # Removing it also saves ~10+ seconds of page loads per run.

            city_code = city_codes[city_choice]
            url = f"https://www.accuweather.com/en/eg/{city_choice}/{city_code}/hourly-weather-forecast/{city_code}?day={selected_day_num}"
            driver.get(url)
            time.sleep(7)

            driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(3)

            cards = driver.find_elements(By.CSS_SELECTOR, ".hourly-card-n, .accordion-item")
            raw_records = []
            parse_failures = []

            target_date = datetime.now() + timedelta(days=(selected_day_num - 1))
            date_us = target_date.strftime('%m/%d/%Y')

            for card in cards:
                try:
                    text = card.text.replace('\n', ' ')
                    time_match = re.search(r'(\d+)\s*(AM|PM)', text, re.IGNORECASE)
                    # --- FIX: AccuWeather renders this as "WindS 8 mph" / "WindSSW 9 mph"
                    # i.e. there is NO space between "Wind" and the compass letters.
                    # The old pattern required `Wind\s+` (one-or-more whitespace), which
                    # never matched, so raw_records stayed empty and the app always fell
                    # through to "Extraction failed". Changed to `Wind\s*` (zero-or-more).
                    wind_match = re.search(r'Wind\s*([A-Z]{1,3})\s+(\d+)\s*(mph|km/h)', text, re.IGNORECASE)

                    if time_match and wind_match:
                        hour, period = time_match.groups()
                        dir_raw, speed_raw, unit = wind_match.groups()
                        speed_val = float(speed_raw)

                        if unit.lower() == 'mph':
                            speed_val = round(speed_val * 1.60934, 1)

                        direction_name = clean_direction(dir_raw.upper())
                        formatted_time_12 = f"{hour.zfill(2)}:00:00 {period.upper()}"

                        h24 = int(hour)
                        if period.upper() == "PM" and h24 != 12:
                            h24 += 12
                        elif period.upper() == "AM" and h24 == 12:
                            h24 = 0
                        date_combined = f"{date_us} {str(h24).zfill(2)}:00"

                        raw_records.append({
                            'date_us': date_us,
                            'formatted_time_12': formatted_time_12,
                            'date_combined': date_combined,
                            'speed': speed_val,
                            'direction': direction_name
                        })
                    else:
                        parse_failures.append(text[:80])
                except Exception as card_err:
                    parse_failures.append(f"[exception: {card_err}]")
                    continue

            if raw_records:
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

                df = pd.DataFrame(weather_data, columns=[
                    'Date', 'Time', 'Date and time', 'wind speed km/hr',
                    'wind direction', 'Wind Direction Angle (simulated)'
                ])
                st.success("✅ الداتا طلعت اهي بالزوايا المتسلسلة طول اليوم...انزلي تحت انقري علشان تنزليها")
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
                # --- FIX: surface *why* extraction failed instead of a dead-end message.
                st.error(f"Extraction failed. Found {len(cards)} card element(s) but none matched "
                         f"the time/wind pattern. Sample card text seen:")
                for sample in parse_failures[:5]:
                    st.code(sample)

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
