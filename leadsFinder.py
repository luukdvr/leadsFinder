import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import tldextract
import time

GOOGLE_API_KEY = "AIzaSyDI8EcD4na2KfqDyi3xV2ZbMnSAvF7dHVQ"  # <-- Zet hier je werkende key
LOCATION = "52.3676,4.9041"  # Amsterdam (latitude,longitude)
RADIUS = 5000  # in meters
SEARCH_TERM = "bakkerij"  # Pas aan op je branche

def get_places(api_key, location, radius, keyword):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": location,
        "radius": radius,
        "keyword": keyword,
        "key": api_key
    }

    places = []
    while True:
        response = requests.get(url, params=params)
        data = response.json()
        if "results" in data:
            places.extend(data["results"])
        if "next_page_token" in data:
            params["pagetoken"] = data["next_page_token"]
            time.sleep(2)  # wachten voor Google rate limits
        else:
            break
    return places

def extract_email_from_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # E-mail zoeken op alle tekst
        text = soup.get_text()
        emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text))
        return list(emails)[0] if emails else None
    except:
        return None

def sanitize_url(url):
    if not url:
        return None
    if not url.startswith("http"):
        return "http://" + url
    return url

def run():
    places = get_places(GOOGLE_API_KEY, LOCATION, RADIUS, SEARCH_TERM)

    results = []
    for place in places:
        name = place.get("name")
        business_type = ", ".join(place.get("types", []))
        website_url = None
        place_id = place.get("place_id")

        # Stap 1: haal gedetailleerde info op om website te krijgen
        detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
        detail_params = {
            "place_id": place_id,
            "fields": "website",
            "key": GOOGLE_API_KEY
        }

        detail_res = requests.get(detail_url, params=detail_params)
        detail_json = detail_res.json()
        website_url = detail_json.get("result", {}).get("website")
        website_url = sanitize_url(website_url)

        # Stap 2: scrape e-mail van website
        email = extract_email_from_website(website_url) if website_url else None

        results.append({
            "Bedrijfsnaam": name,
            "Branche": business_type,
            "Website": website_url,
            "Email": email
        })
        print(f"✅ {name} - {email}")

    # Opslaan als CSV
    df = pd.DataFrame(results)
    df.to_csv("bedrijven_met_emails.csv", index=False, encoding="utf-8-sig")
    print("📁 CSV-bestand opgeslagen als 'bedrijven_met_emails.csv'")

if __name__ == "__main__":
    run()
