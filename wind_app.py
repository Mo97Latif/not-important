import customtkinter as ctk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import random
import pandas as pd
from datetime import datetime, timedelta
import os
import subprocess

# --- قواميس الترجمة والزوايا ---
translations = {
    'شمالية شرقية': 'North East', 'شمالية غربية': 'North West',
    'جنوبية شرقية': 'South East', 'جنوبية غربية': 'South West',
    'شمالية': 'North', 'جنوبية': 'South', 'شرقية': 'East', 'غربية': 'West',
    'شمال': 'North', 'جنوب': 'South', 'شرق': 'East', 'غرب': 'West',
    'م': 'PM', 'ص': 'AM', 'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NE': 'North East', 'NW': 'North West', 'SE': 'South East', 'SW': 'South West',
    'NNE': 'North North East', 'ENE': 'East North East', 'ESE': 'East South East',
    'SSE': 'South South East', 'SSW': 'South South West', 'WSW': 'West South West',
    'WNW': 'West North West', 'NNW': 'North North West'
}

direction_angles = {
    'North': 0.0, 'North North East': 22.5, 'North East': 45.0,
    'East North East': 67.5, 'East': 90.0, 'East South East': 112.5,
    'South East': 135.0, 'South South East': 157.5, 'South': 180.0,
    'South South West': 202.5, 'South West': 225.0, 'West South West': 247.5,
    'West': 270.0, 'West North West': 292.5, 'North West': 315.0, 'North North West': 337.5
}

class WindScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wind Forecast Scraper Pro")
        self.geometry("500x450")
        ctk.set_appearance_mode("dark")
        
        self.label = ctk.CTkLabel(self, text="Wind Forecast Scraper", font=("Roboto", 24, "bold"))
        self.label.pack(pady=20)

        self.city_option = ctk.CTkOptionMenu(self, values=["ras-el-kanayis", "marsa-matruh"])
        self.city_option.pack(pady=15)

        self.status_label = ctk.CTkLabel(self, text="Status: Ready", text_color="gray")
        self.status_label.pack(pady=10)

        self.scrape_button = ctk.CTkButton(self, text="Scrape & Open Excel", command=self.start_scraping)
        self.scrape_button.pack(pady=20)

    def translate_direction(self, text):
        text = text.upper().strip()
        text = re.sub(r'(WIND|الرياح)', '', text).strip()
        return translations.get(text, text)

    def get_random_angle(self, direction_name):
        base_angle = direction_angles.get(direction_name)
        if base_angle is None: return 0.0
        return round((base_angle + random.uniform(-5.0, 5.0)) % 360, 1)

    def start_scraping(self):
        self.scrape_button.configure(state="disabled")
        self.status_label.configure(text="Status: Scraping... Please wait", text_color="yellow")
        self.update()

        city = self.city_option.get()
        city_codes = {"ras-el-kanayis": "129353", "marsa-matruh": "129332"}
        city_code = city_codes[city]

        options = Options()
        # --- إعادة تفعيل وضع المتصفح الخفي ---
        options.add_argument("--headless") 
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.implicitly_wait(20) 
            
            url = f"https://www.accuweather.com/en/eg/{city}/{city_code}/hourly-weather-forecast/{city_code}?day=2"
            driver.get(url)
            
            # محاولة إغلاق رسالة الكوكيز في الخلفية
            try:
                cookie_btn = driver.find_element(By.CSS_SELECTOR, ".policy-accept")
                cookie_btn.click()
                time.sleep(1)
            except:
                pass

            # التمرير لضمان تحميل البيانات
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(8)

            # استخراج البطاقات باستخدام XPATH مرن
            cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'hourly-card-n') or contains(@class, 'accordion-item')]")
            weather_data = []
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')

            for card in cards:
                try:
                    full_text = card.text.replace('\n', ' ')
                    if not full_text.strip(): continue

                    # البحث عن الوقت والرياح بنمط شامل
                    time_match = re.search(r'(\d+)\s*(AM|PM|ص|م)', full_text, re.IGNORECASE)
                    wind_match = re.search(r'([A-Z]{1,3}|North|South|East|West|شمال|جنوب|شرق|غرب)\s+(\d+)\s*(km/h|كم/س)', full_text, re.IGNORECASE)

                    if time_match and wind_match:
                        hour = time_match.group(1)
                        period_raw = time_match.group(2).upper()
                        period_en = "AM" if period_raw in ["AM", "ص"] else "PM"
                        
                        wind_dir_raw = wind_match.group(1)
                        wind_speed = wind_match.group(2)
                        wind_direction = self.translate_direction(wind_dir_raw)
                        
                        formatted_time_12 = f"{hour.zfill(2)}:00:00 {period_en}"
                        h24 = int(hour)
                        if period_en == "PM" and h24 != 12: h24 += 12
                        elif period_en == "AM" and h24 == 12: h24 = 0
                        date_time_24 = f"{tomorrow_str} {str(h24).zfill(2)}:00"
                        
                        angle = self.get_random_angle(wind_direction)
                        weather_data.append([tomorrow_str, formatted_time_12, date_time_24, wind_speed, wind_direction, angle])
                except:
                    continue

            if weather_data:
                df = pd.DataFrame(weather_data, columns=['Date', 'Time', 'Date and time', 'wind speed km/hr', 'wind direction', 'Wind Direction Angle'])
                filename = f"wind_forecast_{city}_{datetime.now().strftime('%H%M%S')}.csv"
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                
                self.status_label.configure(text=f"Success! File: {filename}", text_color="green")
                
                # فتح الملف تلقائياً
                if os.name == 'nt': os.startfile(filename)
                else:
                    import subprocess
                    cmd = 'open' if os.uname().sysname == 'Darwin' else 'xdg-open'
                    subprocess.call([cmd, filename])
            else:
                self.status_label.configure(text="Status: Failed to find data", text_color="red")
                messagebox.showwarning("No Data", "Could not find wind data. The site might be blocking headless requests.")

        except Exception as e:
            self.status_label.configure(text="Status: Error occurred", text_color="red")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            if 'driver' in locals():
                driver.quit()
            self.scrape_button.configure(state="normal")

if __name__ == "__main__":
    app = WindScraperApp()
    app.mainloop()
