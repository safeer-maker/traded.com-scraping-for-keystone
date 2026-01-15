from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# Selenium Manager automatically handles the driver setup
driver = webdriver.Chrome()

driver.get("http://www.google.com")
print(driver.title)
driver.quit()
