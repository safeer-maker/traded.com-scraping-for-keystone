import time
import random
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from scraper import (get_chrome_driver, login_to_traded, force_nav, human_delay, load_all_deals, GOOD_KEYWORDS,
                     BAD_KEYWORDS)

N8N_WEBHOOK_URL = "https://n8n.globbizenterprises.com/webhook/scraper-webhook"


def send_to_webhook(data: List[Dict], state: str):
    if not data:
        return
    print(f"  [Webhook] Sending {len(data)} results for {state} to n8n...")
    try:
        payload = {"state": state, "count": len(data), "brokers": data}
        response = requests.post(N8N_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print("  ✓ Webhook sent successfully.")
        else:
            print(f"  ✗ Webhook failed with status: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Webhook error: {e}")


def collect_broker_links(driver, states: List[str], max_pages: int) -> List[Dict[str, str]]:
    seen_urls = set()
    results = []

    for state in states:
        state_slug = state.lower().replace(" ", "-")
        for page in range(1, max_pages + 1):
            if page == 1:
                url = f"https://traded.co/agents/{state_slug}/loan/"
            else:
                url = f"https://traded.co/agents/{state_slug}/loan/?page={page}"

            print(f"  [Discovery] Scraping {state_slug} - Page {page}...")
            try:
                driver.get(url)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//a[normalize-space()='Profile']")))
                except:
                    print("    No profiles found. Stopping pagination.")
                    break

                soup = BeautifulSoup(driver.page_source, "html.parser")
                profile_buttons = soup.find_all("a", string="Profile")

                count_on_page = 0
                for btn in profile_buttons:
                    href = btn.get('href')
                    if href and href.startswith("/agent/"):
                        full_url = f"https://traded.co{href}"
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            results.append({"url": full_url, "state": state})
                            count_on_page += 1

                print(f"    Found {count_on_page} new profiles.")
                if count_on_page == 0:
                    break
                human_delay(2, 4)
            except Exception as e:
                print(f"    Error scraping {url}: {e}")
                continue
    return results


def extract_broker_metadata(driver, profile_url: str) -> Dict[str, str]:
    force_nav(driver, profile_url)
    human_delay(1.5, 3)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    name = "Unknown"
    first_name = ""
    last_name = ""
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
        parts = name.split()
        if parts:
            first_name = parts[0]
            if len(parts) > 1:
                last_name = parts[-1]

    company = "Unknown"
    job_title = "Unknown"
    position_element = soup.select_one("span[aria-label*='position in']")
    if position_element:
        strong_tag = position_element.find("strong")
        if strong_tag:
            company = strong_tag.get_text(strip=True)
        full_text = position_element.get_text(strip=True)
        if company != "Unknown":
            temp_title = full_text.replace(company, "").strip()
            job_title = temp_title[:-3].strip() if temp_title.lower().endswith(" at") else temp_title
    else:
        fallback_element = soup.select_one("span.MuiTypography-caption strong")
        if fallback_element:
            company = fallback_element.get_text(strip=True)
            parent_text = fallback_element.parent.get_text(strip=True)
            job_title = parent_text.replace(company, "").strip().removesuffix(" at").strip()

    email = ""
    mailto = soup.select_one('a[href^="mailto:"]')
    if mailto:
        email = mailto.get("href").replace("mailto:", "").split("?")[0]

    phone_number = "Not Found"
    phone_icon = soup.select_one('div[aria-label="phone icon"]')
    if phone_icon:
        phone_button = phone_icon.find_parent('button')
        if phone_button:
            phone_number = phone_button.get_text(strip=True)

    traded_link_to_loan = None
    deal_data = load_all_deals(driver, max_pages=3)
    for deal in deal_data:
        title = deal['title'].lower()
        url = deal['url']
        has_good = any(k in title for k in GOOD_KEYWORDS)
        has_bad = any(k in title for k in BAD_KEYWORDS)
        if has_good and not has_bad:
            traded_link_to_loan = f"https://traded.co{url}" if url.startswith("/") else url
            break

    linkedin_url = ""
    try:
        wait = WebDriverWait(driver, 4)
        about_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//h2[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='about']")
        ))
        driver.execute_script("arguments[0].click();", about_button)
        time.sleep(1.5)
        
        linkedin_element = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@href, 'linkedin.com') and contains(@aria-label, 'LinkedIn profile')]")
        ))
        raw_href = linkedin_element.get_attribute("href")
        if raw_href:
            linkedin_url = raw_href
    except Exception:
        pass

    return {
        "Name": name,
        "First Name": first_name,
        "Last Name": last_name,
        "Traded Link to Profile": profile_url,
        "Company": company,
        "Job Title": job_title,
        "Business Email": email,
        "Mobile Phone Number": phone_number,
        "LinkedIn Profile": linkedin_url,
        "Traded Link to Loan (Non-Stabilized)": traded_link_to_loan
    }


def run_discovery_process(states: List[str], max_pages: int = 5) -> List[Dict[str, str]]:
    print("=" * 70)
    print(f"STARTING DISCOVERY RUN FOR STATES: {states}")
    print("=" * 70)
    driver = None
    all_discovered_brokers = []

    try:
        driver = get_chrome_driver()
        login_to_traded(driver)

        for state in states:
            print(f"\n>>> PROCESSING STATE: {state.upper()}")
            state_items = collect_broker_links(driver, [state], max_pages)
            if not state_items:
                continue

            state_brokers_data = []
            print(f"--- Extracting Data for {len(state_items)} profiles ---")

            for i, item in enumerate(state_items[0:2], 1):  # Limiting to first 2 for testing
                url = item['url']
                print(f"[{i}/{len(state_items)}] {url}")
                try:
                    data = extract_broker_metadata(driver, url)

                    data['Location'] = state

                    deal_status = "✓ Found Loan" if data['Traded Link to Loan (Non-Stabilized)'] else "✗ No Loan"
                    print(f"    -> {data['Name']} | {deal_status} | LI: {data['LinkedIn Profile']}")

                    state_brokers_data.append(data)
                except Exception as e:
                    print(f"    -> Error extracting data: {e}")

            if state_brokers_data:
                send_to_webhook(state_brokers_data, state)
                all_discovered_brokers.extend(state_brokers_data)

            print(f"<<< FINISHED STATE: {state.upper()}\n")

    except Exception as e:
        print(f"Fatal error in discovery: {e}")
    finally:
        if driver:
            driver.quit()
        print("=" * 70)

    return all_discovered_brokers
