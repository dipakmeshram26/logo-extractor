import os
import csv
import time
import re
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from PIL import Image
import io

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tkinter import Tk, filedialog


# ================= COUNTS =================
TOTAL = 0
CAPTERRA_LOGO = 0
FAVICON_LOGO = 0
NOT_FOUND = 0


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

SUPPORTED_FORMATS = [".png", ".jpg", ".jpeg", ".webp", ".svg", ".avif", ".ico"]


def get_domain(url):
    if not url:
        return None
    url = re.sub(r'\(.*?\)', '', url)
    url = re.sub(r'[\[\]"\'<>]', '', url).strip()
    if not url.startswith("http"):
        url = "https://" + url.split()[0]
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        return domain if "." in domain else None
    except:
        return None


def save_image(content, ext, base_path):
    if ext == ".ico":
        img = Image.open(io.BytesIO(content))
        img = img.convert("RGBA")
        img.save(base_path + ".png", "PNG", quality=100)
        return True

    with open(base_path + ext, "wb") as f:
        f.write(content)
    return True


def download(url, base_path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200 or not r.content:
            return False

        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext not in SUPPORTED_FORMATS:
            ext = ".png"

        save_image(r.content, ext, base_path)
        return True
    except:
        return False


def fetch_logo_or_favicon(domain, title, logos_dir):
    global FAVICON_LOGO, NOT_FOUND

    homepage = f"https://{domain}"
    safe_name = re.sub(r'[^a-zA-Z0-9\-]', '', title.replace(" ", "-").lower())
    base_path = os.path.join(logos_dir, safe_name)

    soup = None
    try:
        r = requests.get(homepage, headers=HEADERS, timeout=20, allow_redirects=True)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
    except:
        pass

    if soup:
        for sel in ["img[alt*='logo' i]", "img[class*='logo' i]", "img[id*='logo' i]"]:
            tag = soup.select_one(sel)
            if tag and tag.get("src"):
                if download(urljoin(homepage, tag["src"]), base_path):
                    print(f"🟢 WEBSITE LOGO: {title}")
                    FAVICON_LOGO += 1
                    return True

    if soup:
        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])).lower()
            if "icon" in rel and link.get("href"):
                if download(urljoin(homepage, link["href"]), base_path):
                    print(f"🟡 FAVICON: {title}")
                    FAVICON_LOGO += 1
                    return True

    if download(f"{homepage}/favicon.ico", base_path):
        print(f"🟡 FAVICON: {title}")
        FAVICON_LOGO += 1
        return True

    google = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
    if download(google, base_path):
        print(f"🟡 GOOGLE FAVICON: {title}")
        FAVICON_LOGO += 1
        return True

    print(f"❌ NO IMAGE: {title}")
    NOT_FOUND += 1
    return False


def normalize(t):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', '', (t or '').lower())).strip()


def scroll_page(driver):
    for _ in range(6):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)


def main():
    global TOTAL, CAPTERRA_LOGO, NOT_FOUND

    Tk().withdraw()
    csv_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not csv_path:
        return

    category_url = input("\n👉 Paste Capterra category URL: ").strip()
    if not category_url.startswith("http"):
        print("❌ Invalid category URL")
        return

    base_dir = os.path.dirname(csv_path)
    logos_dir = os.path.join(base_dir, "logos")
    os.makedirs(logos_dir, exist_ok=True)

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    TOTAL = len(rows)
    pending = {normalize(r["Title"]): r for r in rows if r.get("Title")}

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    wait = WebDriverWait(driver, 30)

    page_url = category_url

    while page_url and pending:
        driver.get(page_url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        scroll_page(driver)

        cards = driver.find_elements(By.CSS_SELECTOR, "div.card")

        for card in cards:
            try:
                name_el = card.find_element(By.CSS_SELECTOR, "h2.h5 a")
                img_el = card.find_element(By.TAG_NAME, "img")

                scraped = normalize(name_el.text)
                img_url = img_el.get_attribute("src")

                for key in list(pending.keys()):
                    if key in scraped or scraped in key:
                        title = pending[key]["Title"]
                        base_path = os.path.join(
                            logos_dir,
                            re.sub(r'[^a-zA-Z0-9\-]', '', title.replace(" ", "-").lower())
                        )

                        if img_url and download(img_url, base_path):
                            print(f"✅ CAPTERRA LOGO: {title}")
                            CAPTERRA_LOGO += 1
                        else:
                            domain = get_domain(pending[key].get("product.metafields.custom.custom", ""))
                            if domain:
                                fetch_logo_or_favicon(domain, title, logos_dir)
                            else:
                                NOT_FOUND += 1

                        del pending[key]
                        break
            except:
                continue

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a[rel='next']")
            page_url = next_btn.get_attribute("href")
        except:
            break

    for row in pending.values():
        domain = get_domain(row.get("product.metafields.custom.custom", ""))
        if domain:
            fetch_logo_or_favicon(domain, row["Title"], logos_dir)
        else:
            NOT_FOUND += 1

    driver.quit()

    print("\n" + "=" * 50)
    print("📊 FINAL SUMMARY")
    print("=" * 50)
    print(f"🔢 Total softwares      : {TOTAL}")
    print(f"🟢 Capterra logos       : {CAPTERRA_LOGO}")
    print(f"🟡 Website/Favicon used : {FAVICON_LOGO}")
    print(f"🔴 Not found            : {NOT_FOUND}")
    print("=" * 50)


if __name__ == "__main__":
    main()
