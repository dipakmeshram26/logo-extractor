import os
import csv
import time
import re
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tkinter import Tk, filedialog


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


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
    return name.replace("-", " ").title()

def force_png(url):
    if "imgix.net" in url:
        return url + ("&fm=png" if "?" in url else "?fm=png")
    return url

def scroll_page(driver, times=5):
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)


# ---------------- DOMAIN / FAVICON LOGIC ----------------

def get_domain(url):
    if not url:
        return None
    if not url.startswith("http"):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except:
        return None


def download_image(url, save_path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200 and r.content:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except:
        pass
    return False


def fetch_logo_or_favicon(domain, title, save_dir):
    base_path = os.path.join(save_dir, sanitize(title) + ".png")
    homepage = f"https://{domain}"

    # Try homepage
    soup = None
    try:
        r = requests.get(homepage, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
    except:
        pass

    # 1️⃣ Website LOGO
    if soup:
        selectors = [
            "img[alt*='logo' i]",
            "img[class*='logo' i]",
            "img[id*='logo' i]"
        ]
        for sel in selectors:
            img = soup.select_one(sel)
            if img and img.get("src"):
                if download_image(urljoin(homepage, img["src"]), base_path):
                    print(f"🟢 Website LOGO used: {title}")
                    return True

    # 2️⃣ Favicon from HTML
    if soup:
        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])).lower()
            if "icon" in rel and link.get("href"):
                if download_image(urljoin(homepage, link["href"]), base_path):
                    print(f"🟡 FAVICON used: {title}")
                    return True

    # 3️⃣ /favicon.ico
    if download_image(f"{homepage}/favicon.ico", base_path):
        print(f"🟡 FAVICON.ico used: {title}")
        return True

    # 4️⃣ Google favicon fallback
    google = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
    if download_image(google, base_path):
        print(f"🟡 GOOGLE FAVICON used: {title}")
        return True

    print(f"❌ No logo or favicon: {title}")
    return False


# ---------------- MAIN ----------------

def main():
    Tk().withdraw()
    csv_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not csv_path:
        return

    save_dir = os.path.join(os.path.dirname(csv_path), "logos")
    os.makedirs(save_dir, exist_ok=True)

    category_text = csv_to_category_text(csv_path)
    print(f"🎯 Target category: {category_text}")

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    wait = WebDriverWait(driver, 30)

    # Load CSV
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    pending = {
        normalize(r["Title"]): r for r in rows if r.get("Title")
    }

    # Open directory
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

    page_url = category_url
    page_no = 1

    # Pagination loop
    while pending:
        print(f"\n📄 Page {page_no}")
        driver.get(page_url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        scroll_page(driver)

        cards = driver.find_elements(By.CSS_SELECTOR, "div.card")

        for card in cards:
            try:
                name_el = card.find_element(By.CSS_SELECTOR, "h2.h5.fw-bold.mb-2 a")
                img_el = card.find_element(By.CSS_SELECTOR, "img.img-fluid")

                scraped = normalize(name_el.text)
                img_url = force_png(img_el.get_attribute("src"))

                for key in list(pending.keys()):
                    if key in scraped or scraped in key:
                        save_path = os.path.join(
                            save_dir, sanitize(pending[key]["Title"]) + ".png"
                        )
                        if download_image(img_url, save_path):
                            print(f"✅ Capterra LOGO: {pending[key]['Title']}")
                        del pending[key]
                        break
            except:
                continue

        # Next page
        try:
            next_btn = driver.find_element(
                By.CSS_SELECTOR, "ul.pagination li.page-item.next a"
            )
            page_url = next_btn.get_attribute("href")
            page_no += 1
        except:
            break

    # Fallback (favicon)
    for key, row in pending.items():
        domain = get_domain(row.get("product.metafields.custom.custom", ""))
        if domain:
            fetch_logo_or_favicon(domain, row["Title"], save_dir)

    driver.quit()
    print("\n🎉 DONE — LOGO → FAVICON FALLBACK COMPLETED")


if __name__ == "__main__":
    main()
