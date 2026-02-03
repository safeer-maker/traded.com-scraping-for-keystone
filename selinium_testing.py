from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import time

# Selenium Manager automatically handles the driver setup
driver = webdriver.Chrome()

driver.get("http://www.google.com")
print(driver.title)

sandbox = driver.find_element(By.NAME, "q")
sandbox.send_keys("Selenium")
sandbox.send_keys(Keys.RETURN)

results = driver.find_elements(By.CSS_SELECTOR, "div.g")

time.sleep(2)  # Let the user actually see something!

driver.quit()


