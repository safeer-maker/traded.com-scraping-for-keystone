import os
import csv
import time
import random
from typing import List, Dict, Tuple

from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

load_dotenv()
TRADED_USERNAME = os.getenv("TRADED_USERNAME" )
TRADED_PASSWORD = os.getenv("TRADED_PASSWORD" )

THRESHOLD_PERCENTAGE = 40
MAX_PAGES_PER_BROKER = 5
MAX_DEALS_TO_ANALYZE = 100
GOOD_KEYWORDS = [
    "bridge", "construction", "acquisition", "refinance", "refinances", "mezzanine", "mezz", "rehab", "rehabilitation",
    "development", "lease-up", "stabilization", "value-add", "repositioning", "transitional", "gap", "interim"
]
BAD_KEYWORDS = [
    "permanent", "perm", "takeout", "fixed-rate", "amortizing", "agency", "conduit", "life company", "hud", "fannie",
    "freddie"
]


def get_chrome_driver() -> webdriver.Chrome:
    print("  Initializing headless Chrome driver...")
    options = Options()
    # options.add_argument("--headless=new") 
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
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
    print("✓ Driver initialized successfully.")
    return driver


def login_to_traded(driver: webdriver.Chrome):
    print("\n[STEP 1] Logging into traded.co...")
    try:
        base_url = "https://traded.co"
        driver.get(base_url)
        wait = WebDriverWait(driver, 20)
        login_prompt_button_locator = (By.XPATH, "//button[normalize-space()='Sign up or log in']")
        print("  Clicking 'Sign up or log in' button...")
        login_prompt_button = wait.until(EC.element_to_be_clickable(login_prompt_button_locator))
        login_prompt_button.click()
        time.sleep(1)
        print("  Entering email...")
        email_input = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        email_input.send_keys(TRADED_USERNAME)
        print("  Entering password...")
        password_input = wait.until(EC.visibility_of_element_located((By.NAME, "password")))
        password_input.send_keys(TRADED_PASSWORD)
        print("  Submitting credentials...")
        submit_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and normalize-space()='Continue']")))
        submit_button.click()
        print("  Checking for newsletter popup...")
        try:
            short_wait = WebDriverWait(driver, 7)
            close_button_xpath = "//button[@aria-label='close' or @aria-label='Close']"
            close_button = short_wait.until(EC.element_to_be_clickable((By.XPATH, close_button_xpath)))
            print("  ✓ Newsletter popup found. Closing it...")
            driver.execute_script("arguments[0].click();", close_button)
        except TimeoutException:
            print("  - Newsletter popup did not appear. Continuing.")
            pass
        print("  Waiting for login confirmation...")
        wait.until(EC.invisibility_of_element_located(login_prompt_button_locator))
        print("✓ Login successful. Confirmed by absence of 'Log In' button.")
    except Exception as e:
        print(f"❌ An critical error occurred during login: {e}")
        raise


def force_nav(driver, url, timeout=30):
    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
    except Exception:
        driver.execute_script("window.location.href = arguments[0];", url)
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")


def human_delay(a=5, b=8):
    time.sleep(random.uniform(a, b))


def load_all_deals(driver, max_pages=10) -> List[Dict[str, str]]:
    all_deals, seen_urls, current_page = [], set(), 1
    while current_page <= max_pages:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        links = soup.select('a[class*="MuiTypography-bBase"][href*="/deals/"]')
        if not links:
            break
        new_deals_found = False
        for link in links:
            url, title = link.get("href", ""), link.get_text(strip=True)
            if url and url not in seen_urls and len(title) > 20:
                seen_urls.add(url)
                all_deals.append({'title': title, 'url': url})
                new_deals_found = True
        if not new_deals_found and current_page > 1:
            break
        current_page += 1
        if current_page > max_pages:
            break
        try:
            next_page_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[@aria-label='Go to page {current_page}']")))
            driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", next_page_button)
            time.sleep(random.uniform(3, 5))
        except TimeoutException:
            break
    return all_deals


def analyze_broker(driver, broker: Dict[str, str]) -> Tuple[bool, str, str, Dict[str, float], str]:
    force_nav(driver, broker["profile_url"])
    human_delay()
    
    deal_data = load_all_deals(driver, max_pages=MAX_PAGES_PER_BROKER)
    print(f"    Analyzing {len(deal_data)} deals...")
    good = bad = skipped = 0
    good_sample_url = None
    for deal in deal_data[:min(MAX_DEALS_TO_ANALYZE, len(deal_data))]:
        title, url = deal['title'].lower(), deal['url']
        has_good = any(k in title for k in GOOD_KEYWORDS)
        has_bad = any(k in title for k in BAD_KEYWORDS)
        if has_good and not has_bad:
            good += 1
            if not good_sample_url and url:
                good_sample_url = f"https://traded.co{url}" if url.startswith("/") else url
        elif has_bad:
            bad += 1
        else:
            skipped += 1
    
    categorized = good + bad
    pct_good = (good / categorized) * 100 if categorized else 0.0
    print(f"    Good: {good} | Bad: {bad} | Skipped: {skipped} | %Good: {pct_good:.1f}%")

    job_title = "Not Found"
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        title_element = soup.select_one("h1 + p")
        if title_element:
            job_title = title_element.get_text(strip=True)
    except Exception:
        pass

    linkedin_url = ""
    try:
        wait = WebDriverWait(driver, 5)
        about_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//h2[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='about']")
        ))
        
        driver.execute_script("arguments[0].click();", about_button)
        time.sleep(2) 
        
        linkedin_element = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@href, 'linkedin.com') and contains(@aria-label, 'LinkedIn profile')]")
        ))
        
        raw_href = linkedin_element.get_attribute("href")
        if raw_href:
            linkedin_url = raw_href
            print(f"    LinkedIn found: {linkedin_url}")
            
    except TimeoutException:
        print("    LinkedIn/About section not found or timed out.")
    except Exception as e:
        print(f"    Error extracting LinkedIn: {e}")

    qualified = pct_good >= THRESHOLD_PERCENTAGE and categorized > 0
    stats = {"good": good, "bad": bad, "skipped": skipped, "pct_good": pct_good}
    
    return qualified, (good_sample_url or ""), job_title, stats, linkedin_url


def run_broker_analysis(brokers: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    The main scraping logic, refactored to be a callable function.
    Accepts a list of broker data, returns a list of qualified brokers.
    """
    print("=" * 70)
    print("STARTING NEW BROKER ANALYSIS RUN")
    print("=" * 70)

    driver = None
    qualified_rows: List[Dict[str, str]] = []

    try:
        driver = get_chrome_driver()
        login_to_traded(driver)

        if not brokers:
            print("No brokers provided in the request. Exiting run.")
            return []

        print(f"\n[STEP 2] Analyzing {len(brokers)} broker profiles provided by API request…\n")
        for i, broker in enumerate(brokers, 1):
            print(f"[{i}/{len(brokers)}] {broker['name']} ({broker['company']})")
            print(f"  URL: {broker['profile_url']}")

            try:
                qualified, sample_url, job_title, stats, linkedin = analyze_broker(driver, broker)
                if qualified:
                    print("  ✓ QUALIFIED")
                    parts = broker["name"].split()

                    qualified_rows.append({
                        "Name": broker["name"],
                        "FirstName": parts[0] if parts else "",
                        "LastName": parts[-1] if len(parts) > 1 else "",
                        "JobTitle": job_title.strip().removesuffix(" at"),
                        "CompanyName": broker["company"],
                        "LinkedInProfile": linkedin,
                        "TradedLinkToLoan": sample_url,
                        "TradedLinkToProfile": broker["profile_url"],
                    })
                else:
                    print(f"  ✗ Did not qualify ({stats['pct_good']:.1f}% < {THRESHOLD_PERCENTAGE}%)")
                print("-" * 30)
                if i < len(brokers):
                    human_delay(8, 12)
            except Exception as e:
                print(f"  ❌ Error analyzing {broker['name']}: {e}\n")
                continue

    except Exception as e:
        print(f"\nAn unexpected fatal error occurred: {e}")
    finally:
        print("\n" + "=" * 70)
        print("ANALYSIS RUN FINISHED. Closing driver.")
        if driver:
            driver.quit()
        print("=" * 70)

    return qualified_rows