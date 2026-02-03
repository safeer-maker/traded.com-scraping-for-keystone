from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import undetected_chromedriver as uc

import time

# to hande captache

def solve_captcha(driver):
    try:
        # Wait for the captcha iframe to load
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'captcha')]"))
        )
        driver.switch_to.frame(iframe)

        # Click on the checkbox to solve the captcha
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
        )
        checkbox.click()

        # Switch back to the main content
        driver.switch_to.default_content()

        # Wait for a moment to let the captcha process
        time.sleep(5)
    except TimeoutException:
        print("No captcha found or failed to solve captcha.")

def captcha_args():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    )
    return options


# Selenium Manager automatically handles the driver setup
driver = webdriver.Chrome()


driver.get("http://www.google.com")
print(driver.title)

sandbox = driver.find_element(By.NAME, "q")
sandbox.send_keys("Selenium")
sandbox.send_keys(Keys.RETURN)


solve_captcha(driver)

results = driver.find_elements(By.CSS_SELECTOR, "div.g")

time.sleep(2)  # Let the user actually see something!

driver.quit()


