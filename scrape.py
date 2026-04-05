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
page = 1
max_pages = 10

while page <= max_pages:
    print(f"\n--- Scraping page {page} ---")
    
    # Build URL with page parameter
    page_url = f"{url}&page={page}" if "?" in url else f"{url}?page={page}"
    res = requests.get(page_url, headers=headers, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    
    rows = soup.select("table tr")
    if not rows or len(rows) == 1:  
        print("No more results. Stopping pagination.")
        break
    
    page_found = 0
    for row in rows:
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
        page_found += 1
        print(f"  ✓ Added: {location_text} - {href}\n")
    
    print(f"Found {page_found} Canadian tournaments on page {page}.")
    
    page += 1
# dedupe
tournament_links = list(dict.fromkeys(tournament_links))

print("count:", len(tournament_links))
print(tournament_links[:10])

# Now scrape individual tournament results
all_results = []

for link in tournament_links:
    print(f"\n--- Scraping tournament: {link} ---")
    res = requests.get(link, headers=headers, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Find all result tables on the page
    tables = soup.find_all('table')
    print(f"Found {len(tables)} result tables")
    
    for table_idx, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) < 2:  # Skip tables with no data rows
            continue
            
        # Extract table header to identify the event
        header_row = rows[0]
        table_headers = [cell.get_text(strip=True) for cell in header_row.find_all(['th', 'td'])]
        event_name = table_headers[0] if table_headers else f"Event {table_idx + 1}"
        
        print(f"  Processing table {table_idx + 1}: {event_name} ({len(rows)-1} fencers)")
        
        # Process each fencer row
        for row_idx, row in enumerate(rows[1:], start=1):  # Skip header row
            cells = row.find_all('td')
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            print(f"    row {row_idx}: {len(cells)} cells -> {cell_texts}")

            if len(cells) < 3:  # Skip malformed rows
                print("      skip: not enough cells")
                continue

            # Extract fencer data
            place = cells[0].get_text(strip=True)
            fencer_name = cells[1].get_text(strip=True)
            club = cells[2].get_text(strip=True)
            if not club:
                club = "unaffiliated"
            # rating = cells[3].get_text(strip=True)
            # earned = cells[4].get_text(strip=True)
            
            # Skip "No Results Available" entries
            if "No Results Available" in fencer_name:
                print("      skip: No Results Available")
                continue

            result = {
                'tournament_url': link,
                'event': event_name,
                'place': place,
                'fencer': fencer_name,
                'club': club
                # 'rating': rating,
                # 'earned': earned
            }
            all_results.append(result)
            print(f"      append: {place}. {fencer_name} ({club})")

print(f"\n--- Total results collected: {len(all_results)} ---")

# Optional: Save to CSV
import csv
if all_results:
    with open('fencing_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['tournament_url', 'event', 'place', 'fencer', 'club', 'rating', 'earned']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print("Results saved to fencing_results.csv")
