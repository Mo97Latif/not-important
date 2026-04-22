import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By  # هذا هو السطر الذي كان ينقصك
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time

st.title("🔍 IP & Access Connectivity Test")

if st.button("Run Connection Test"):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    try:
        with st.spinner("Starting Chrome and testing connection..."):
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )
            
            # --- الخطوة 1: معرفة الـ IP الخاص بالسيرفر ---
            st.subheader("1. Server Identity Check")
            driver.get("https://api.ipify.org")
            # الآن سيعمل By.TAG_NAME بدون مشاكل
            server_ip = driver.find_element(By.TAG_NAME, "body").text
            st.write(f"🌐 Streamlit Server IP: `{server_ip}`")

            # --- الخطوة 2: اختبار الوصول لـ AccuWeather ---
            st.subheader("2. AccuWeather Accessibility")
            test_url = "https://www.accuweather.com/"
            driver.get(test_url)
            time.sleep(5)
            
            page_title = driver.title
            st.write(f"📄 Page Title: **{page_title}**")

            if "Access Denied" in page_title or "403" in page_title:
                st.error("🚫 Result: IP is BLOCKED by AccuWeather (Access Denied).")
            elif "AccuWeather" in page_title:
                st.success("✅ Result: Connection Successful! AccuWeather is reachable.")
            else:
                st.warning(f"⚠️ Result: Unexpected response. Title: {page_title}")

    except Exception as e:
        st.error(f"❌ Test Failed: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
