import os
import csv
import requests
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from PIL import Image
import io

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

SUPPORTED_FORMATS = [".png", ".jpg", ".jpeg", ".webp", ".svg", ".avif", ".ico"]

# -------------------------------------------------
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


# -------------------------------------------------
def save_image(content, ext, base_path):
    if ext == ".ico":
        img = Image.open(io.BytesIO(content))
        img = img.convert("RGBA")
        img.save(base_path + ".png", "PNG", quality=100)
        return base_path + ".png"

    with open(base_path + ext, "wb") as f:
        f.write(content)
    return base_path + ext


# -------------------------------------------------
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


# -------------------------------------------------
def fetch_logo_or_favicon(domain, title, logos_dir):
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

    # 1️⃣ LOGO
    if soup:
        logo_selectors = [
            "img[alt*='logo' i]",
            "img[class*='logo' i]",
            "img[id*='logo' i]"
        ]

        for sel in logo_selectors:
            tag = soup.select_one(sel)
            if tag and tag.get("src"):
                if download(urljoin(homepage, tag["src"]), base_path):
                    print(f"✓ LOGO saved: {domain}")
                    return True

    # 2️⃣ FAVICON FROM HTML
    favicon_urls = []

    if soup:
        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])).lower()
            if "icon" in rel and link.get("href"):
                favicon_urls.append(urljoin(homepage, link["href"]))

    # 3️⃣ /favicon.ico
    favicon_urls.append(f"{homepage}/favicon.ico")

    for fav in favicon_urls:
        if download(fav, base_path):
            print(f"✓ FAVICON saved: {domain}")
            return True

    # 4️⃣ GOOGLE FAVICON
    google_favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
    if download(google_favicon, base_path):
        print(f"✓ GOOGLE FAVICON saved: {domain}")
        return True

    print(f"❌ NO LOGO OR FAVICON FOUND: {domain}")
    return False


# -------------------------------------------------
# MAIN
# -------------------------------------------------
csv_path = input("CSV file path: ").strip()

if not os.path.exists(csv_path):
    print("CSV not found")
    exit()

base_dir = os.path.dirname(csv_path)

logos_dir = os.path.join(base_dir, "logos")
os.makedirs(logos_dir, exist_ok=True)

print(f"\n📂 Logos will be saved in:\n{logos_dir}")

total = 0
success = 0
not_found = 0

with open(csv_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        domain = get_domain(row.get("product.metafields.custom.custom", ""))
        title = row.get("Title", "website")

        if not domain:
            continue

        total += 1
        print(f"\n🔍 Processing: {domain}")

        if fetch_logo_or_favicon(domain, title, logos_dir):
            success += 1
        else:
            not_found += 1


print("\n" + "=" * 60)
print(f"📊 SUMMARY")
print(f"Total processed      : {total}")
print(f"Images downloaded    : {success}")
print(f"❌ Not found (any way): {not_found}")
print("✔ LOGO if exists | ✔ FAVICON if logo not found | ✔ GOOGLE fallback")
print("📁 All images stored inside /logos folder")
print("=" * 60)
