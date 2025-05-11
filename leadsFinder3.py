import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import tldextract
import time
from urllib.parse import urljoin

API_KEY = "AIzaSyDI8EcD4na2KfqDyi3xV2ZbMnSAvF7dHVQ"  # <-- Vul hier je Google Places API Key in

BRANCHES = ["bakkerij", "kapper", "fysiotherapie"]
LOCATIES = {
    "Amsterdam": "52.3676,4.9041",
    "Rotterdam": "51.9225,4.47917",
    "Utrecht": "52.0907,5.1214"
}
RADIUS = 5000
MAX_EMAILS_TOTAL = 10
MAX_EMAILS_PER_BRANCHE = 4

def get_places(api_key, location, radius, keyword):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": location,
        "radius": radius,
        "keyword": keyword,
        "key": api_key
    }

    all_places = []
    while True:
        res = requests.get(url, params=params)
        data = res.json()
        all_places.extend(data.get("results", []))
        if "next_page_token" in data:
            time.sleep(2)
            params["pagetoken"] = data["next_page_token"]
        else:
            break
    return all_places

def sanitize_url(url):
    if not url:
        return None
    if not url.startswith("http"):
        return "http://" + url
    return url

def extract_emails(text):
    return list(set(re.findall(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", text)))

def find_email_on_site(base_url):
    pages_to_try = ["", "/contact", "/contact.html", "/about", "/over-ons", "/over"]
    headers = {"User-Agent": "Mozilla/5.0"}
    emails = set()

    for page in pages_to_try:
        try:
            full_url = urljoin(base_url, page)
            res = requests.get(full_url, headers=headers, timeout=8)
            soup = BeautifulSoup(res.text, "html.parser")

            for tag in soup.find_all("a", href=True):
                if "mailto:" in tag["href"]:
                    email = tag["href"].split("mailto:")[1].split("?")[0].strip()
                    if "@" in email:
                        emails.add(email)

            text = soup.get_text(separator=' ', strip=True)
            extracted = extract_emails(text)
            emails.update(extracted)

        except Exception:
            continue

    return list(emails)[0] if emails else None

def main():
    resultaten = []
    total_emails_found = 0
    emails_per_branche = {branche: 0 for branche in BRANCHES}

    for stad, coord in LOCATIES.items():
        for branche in BRANCHES:
            if total_emails_found >= MAX_EMAILS_TOTAL:
                break
            if emails_per_branche[branche] >= MAX_EMAILS_PER_BRANCHE:
                continue

            print(f"🔍 Zoeken naar '{branche}' in {stad}...")
            bedrijven = get_places(API_KEY, coord, RADIUS, branche)

            for bedrijf in bedrijven:
                if total_emails_found >= MAX_EMAILS_TOTAL:
                    break
                if emails_per_branche[branche] >= MAX_EMAILS_PER_BRANCHE:
                    break

                naam = bedrijf.get("name")
                place_id = bedrijf.get("place_id")

                detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
                params = {
                    "place_id": place_id,
                    "fields": "website",
                    "key": API_KEY
                }

                try:
                    detail_res = requests.get(detail_url, params=params)
                    website = detail_res.json().get("result", {}).get("website")
                    website = sanitize_url(website)
                    email = find_email_on_site(website) if website else None

                    if email:
                        resultaten.append({
                            "Naam": naam,
                            "Branche": branche,
                            "Stad": stad,
                            "Website": website,
                            "Email": email
                        })
                        total_emails_found += 1
                        emails_per_branche[branche] += 1
                        print(f"✅ {naam} ({stad}) - {email}")
                except Exception as e:
                    print(f"⚠️ Fout bij {naam}: {e}")
                    continue

    df = pd.DataFrame(resultaten)
    df.to_csv("bedrijven_leads.csv", index=False, encoding="utf-8-sig")
    print("📁 CSV opgeslagen als 'bedrijven_leads.csv'")

if __name__ == "__main__":
    main()
