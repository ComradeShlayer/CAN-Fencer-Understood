# this will scrape the fencing data from the website and save it to a csv file
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.askfred.net"
url = "https://www.askfred.net/results?weapon=&gender=&age=&name=&date_by=on&date=&entries_count=&division_id=&location=&radius=&authority=&has_results=1"


CANADIAN_PROVINCES = ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.askfred.net/results",
}

res = requests.get(url, headers=headers, timeout=20)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")

tournament_links = []
for row in soup.select("table tr"):
    
    cells = row.select("td")
    if not cells:
        continue
    print("Row cells:")

    for i, cell in enumerate(cells):
        print(f"  Column {i}: {cell.get_text(strip=True)[:80]}")
    
    link_tag = row.select_one("a[href*='/tournaments/'][href$='/results']")
    if not link_tag:
        continue

    # Only add if location in Canada
    location_cell = cells[2] if len(cells) > 2 else None
    if not location_cell:
        continue
    location_text = location_cell.get_text(strip=True)
    
    if not any(province in location_text for province in CANADIAN_PROVINCES):
        continue
    
    href = link_tag["href"]
    tournament_links.append(BASE_URL + href)
    print(f"  ✓ Added: {location_text} - {href}\n")


# dedupe
tournament_links = list(dict.fromkeys(tournament_links))

print("count:", len(tournament_links))
print(tournament_links[:10])