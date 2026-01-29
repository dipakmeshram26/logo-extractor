import os
import csv
import requests
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from PIL import Image
import io
from tkinter import Tk, filedialog

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

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
def clean_name(name):
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    name = re.sub(r'\s+', '-', name)
    return name


# -------------------------------------------------
def unique_path(folder, name):
    path = os.path.join(folder, name + ".png")
    i = 1
    while os.path.exists(path):
        path = os.path.join(folder, f"{name}-{i}.png")
        i += 1
    return path


# -------------------------------------------------
def save_png(content, path):
    try:
        img = Image.open(io.BytesIO(content))
        img = img.convert("RGBA")
        img.save(path, "PNG", quality=100)
        return True
    except:
        return False


# -------------------------------------------------
def download_image(url, final_path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return False

        if "text/html" in r.headers.get("Content-Type", ""):
            return False

        return save_png(r.content, final_path)
    except:
        return False


# -------------------------------------------------
def filename_from_title_or_domain(title, domain):
    if title:
        return clean_name(title)
    return domain.replace(".", "-")


# -------------------------------------------------
def fetch_logo_or_favicon(domain, title, logos_dir):
    homepage = f"https://{domain}"

    file_base = filename_from_title_or_domain(title, domain)
    final_path = unique_path(logos_dir, file_base)

    soup = None
    try:
        r = requests.get(homepage, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
    except:
        pass

    # 1️⃣ LOGO FROM HTML
    if soup:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = (img.get("alt") or "").lower()

            if "logo" in alt or "logo" in src.lower():
                if download_image(urljoin(homepage, src), final_path):
                    print(f"✓ LOGO saved as: {os.path.basename(final_path)}")
                    return True

    # 2️⃣ FAVICON FROM HTML
    if soup:
        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])).lower()
            href = link.get("href")

            if "icon" in rel and href:
                if download_image(urljoin(homepage, href), final_path):
                    print(f"✓ FAVICON saved as: {os.path.basename(final_path)}")
                    return True

    # 3️⃣ /favicon.ico
    if download_image(f"{homepage}/favicon.ico", final_path):
        print(f"✓ FAVICON saved as: {os.path.basename(final_path)}")
        return True

    # 4️⃣ GOOGLE FALLBACK
    google = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
    if download_image(google, final_path):
        print(f"✓ GOOGLE favicon saved as: {os.path.basename(final_path)}")
        return True

    print(f"❌ NOT FOUND: {domain}")
    return False


# -------------------------------------------------
# MAIN
# -------------------------------------------------
Tk().withdraw()

csv_path = filedialog.askopenfilename(
    title="Select CSV File",
    filetypes=[("CSV Files", "*.csv")]
)

if not csv_path:
    print("❌ No CSV selected")
    exit()

base_dir = os.path.dirname(csv_path)
logos_dir = os.path.join(base_dir, "logos")
os.makedirs(logos_dir, exist_ok=True)

print(f"\n📂 Logos will be saved in:\n{logos_dir}")

total = success = failed = 0

with open(csv_path, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        domain = get_domain(row.get("product.metafields.custom.custom", ""))
        title = row.get("Title", "").strip()

        if not domain:
            continue

        total += 1
        print(f"\n🔍 Processing: {title or domain}")

        if fetch_logo_or_favicon(domain, title, logos_dir):
            success += 1
        else:
            failed += 1


print("\n" + "=" * 60)
print("📊 SUMMARY")
print(f"Total processed : {total}")
print(f"Downloaded      : {success}")
print(f"Not found       : {failed}")
print("📁 Image name = CSV Title → else Domain name")
print("📁 All images saved in /logos folder")
print("=" * 60)
