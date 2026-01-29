import os
import csv
import requests
from urllib.parse import urlparse
from PIL import Image
import io
import re
from tkinter import Tk, filedialog  # ✅ FILE PICKER

def get_domain(url):
    if not url:
        return None
    
    cleaned_url = re.sub(r'[\[\]"\']', '', url.strip())
    cleaned_url = cleaned_url.split()[0]
    
    try:
        parsed = urlparse(cleaned_url)
        domain = parsed.netloc.lower().replace("www.", "")
        return domain if domain else None
    except:
        return None

def download_high_quality_png(domain, product_title, category, output_dir):
    if not domain:
        return False
    
    if product_title:
        clean_title = product_title.lower().strip().replace(" ", "-")
        filename_base = f"{clean_title}-{category.replace(' ', '-')}"
    else:
        filename_base = domain.replace(".", "-")
    
    filename = f"{filename_base}.png"
    path = os.path.join(output_dir, filename)

    api_list = [
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        f"https://api.faviconkit.com/{domain}/256",
        f"https://s2.googleusercontent.com/s2/favicons?domain={domain}&sz=256",
        f"https://logo.clearbit.com/{domain}?size=256"
    ]

    for api_url in api_list:
        try:
            print(f"  ट्राय कर रहा: {api_url.split('//')[1].split('/')[0]}")
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                img_data = io.BytesIO(response.content)
                img = Image.open(img_data)
                
                if img.format == 'ICO':
                    img = img.resize((256, 256), Image.LANCZOS)
                
                img = img.convert("RGBA")
                img.save(path, "PNG", quality=100, optimize=False)
                print(f"✓ सेव हो गया: {filename}")
                return True
                
        except Exception as e:
            print(f"  फेल: {api_url.split('//')[1].split('/')[0]} → {str(e)}")

    print(f"✗ नहीं मिला: {domain} ({product_title})")
    return False


# ================= MAIN PROGRAM =================

# ✅ CSV FILE PICKER
Tk().withdraw()  # tkinter window hide

csv_file_path = filedialog.askopenfilename(
    title="CSV फाइल चुनो",
    filetypes=[("CSV Files", "*.csv")]
)

if not csv_file_path:
    print("कोई CSV फाइल सेलेक्ट नहीं की गई")
    exit()

if not os.path.exists(csv_file_path):
    print("फाइल नहीं मिली!")
    exit()

print(f"सेलेक्ट की गई CSV फाइल: {csv_file_path}")

# CSV वाले folder का path
base_dir = os.path.dirname(csv_file_path)

# उसी folder में 'logos' नाम का folder
logos_dir = os.path.join(base_dir, "logos")
os.makedirs(logos_dir, exist_ok=True)

print(f"इमेजेस यहाँ सेव होंगी: {logos_dir}")

success_count = 0
fail_count = 0

with open(csv_file_path, 'r', encoding='utf-8', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    
    for row in reader:
        url = row.get('product.metafields.custom.custom', '').strip()
        title = row.get('Title', '').strip()
        category = row.get('Product Category', 'Unknown').strip()
        
        domain = get_domain(url)
        
        if not domain:
            print(f"Invalid URL skipped: {url}")
            continue
            
        print(f"\nProcessing: {domain} → {title}")
        
        if download_high_quality_png(domain, title, category, logos_dir):
            success_count += 1
        else:
            fail_count += 1

print("\n" + "="*70)
print(f"समाप्त! कुल domains प्रोसेस: {success_count + fail_count}")
print(f"सफल हाई क्वालिटी PNG डाउनलोड: {success_count}")
print(f"फेल/नहीं मिले: {fail_count}")
print(f"सभी PNG फाइलें यहाँ सेव: {logos_dir}")
print("="*70)
