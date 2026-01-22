import os
import csv
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tkinter import Tk, filedialog


# ---------------- HELPERS ----------------

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def sanitize(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()

def csv_to_category_text(csv_path):
    name = os.path.basename(csv_path).replace(".csv", "")
    name = name.replace("-", " ")
    return name.title()

def force_png(url):
    if "imgix.net" in url:
        return url + ("&fm=png" if "?" in url else "?fm=png")
    return url

def scroll_page(driver, times=5):
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)


# ---------------- MAIN ----------------

def main():
    Tk().withdraw()
    csv_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not csv_path:
        return

    save_dir = os.path.dirname(csv_path)
    category_text = csv_to_category_text(csv_path)

    print(f"🎯 Target category: {category_text}")

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    wait = WebDriverWait(driver, 30)

    # STEP 1: Open directory
    driver.get("https://www.capterra.in/directory")
    time.sleep(5)

    categories = driver.find_elements(
        By.CSS_SELECTOR,
        "a.list-group-item.list-group-item-action.border-0.fw-bold"
    )

    category_url = None
    for c in categories:
        if normalize(c.text) == normalize(category_text):
            category_url = c.get_attribute("href")
            break

    if not category_url:
        print("❌ Category not found")
        driver.quit()
        return

    print(f"✅ Category found: {category_url}")

    # STEP 2: Load CSV titles
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_titles = [row.get("Title", "").strip() for row in reader]

    pending = {normalize(t): t for t in csv_titles}

    current_url = category_url
    page_no = 1

    # STEP 3: Pagination loop
    while pending:
        print(f"\n📄 Scanning page {page_no}")
        driver.get(current_url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        scroll_page(driver)

        cards = driver.find_elements(By.CSS_SELECTOR, "div.card")
        print(f"📦 Cards found: {len(cards)}")

        for card in cards:
            try:
                name_el = card.find_element(By.CSS_SELECTOR, "h2.h5.fw-bold.mb-2 a")
                img_el = card.find_element(By.CSS_SELECTOR, "img.img-fluid")

                scraped_name = normalize(name_el.text)
                img_url = img_el.get_attribute("src")

                for key in list(pending.keys()):
                    if key in scraped_name or scraped_name in key:
                        final_url = force_png(img_url)
                        save_path = os.path.join(
                            save_dir, sanitize(pending[key]) + ".png"
                        )

                        r = requests.get(final_url, timeout=20)
                        r.raise_for_status()
                        with open(save_path, "wb") as f:
                            f.write(r.content)

                        print(f"✅ Saved logo: {pending[key]}")
                        del pending[key]
                        break
            except:
                continue

        # Find next page
        try:
            next_link = driver.find_element(
                By.CSS_SELECTOR,
                "ul.pagination li.page-item.next a"
            )
            href = next_link.get_attribute("href")
            if not href:
                break
            current_url = href
            page_no += 1
        except:
            print("⛔ No next page button")
            break

    # STEP 4: Report missing
    for name in pending.values():
        print(f"⚠️ Logo not found in category pages: {name}")

    driver.quit()
    print("\n🎉 PAGINATION DONE — ALL POSSIBLE LOGOS DOWNLOADED")


if __name__ == "__main__":
    main()
