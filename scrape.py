# this will scrape the fencing data from the website and save it to a csv file
import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://www.askfred.net"
url = "https://www.askfred.net/results?weapon=&gender=&age=&name=&date_by=on&date=&entries_count=&division_id=&location=&radius=&authority=&has_results=1"


CANADIAN_PROVINCES = ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.askfred.net/results",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

time.sleep(1)
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
    time.sleep(1)
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
round_results = []

for link in tournament_links:
    print(f"\n--- Scraping tournament: {link} ---")
    time.sleep(1)
    res = requests.get(link, headers=headers, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Extract tournament metadata from page title
    # Format: "TOURNAMENT NAME Results | Organizer | City, Province | AskFRED"
    title_text = soup.find('title')
    if title_text:
        title_parts = [p.strip() for p in title_text.get_text().split('|')]
        tournament_name = title_parts[0].replace(' Results', '')
        organizer = title_parts[1] if len(title_parts) > 1 else "Unknown"
        location = title_parts[2] if len(title_parts) > 2 else "Unknown"
        
        # Parse location into city and province
        if ',' in location:
            city, province = location.split(',', 1)
            city = city.strip()
            province = province.strip()
        else:
            city = location
            province = ""
    else:
        tournament_name = "Unknown"
        organizer = "Unknown"
        city = "Unknown"
        province = ""
    
    print(f"  Tournament: {tournament_name}")
    print(f"  Organizer: {organizer}")
    print(f"  Location: {city}, {province}")
    
    # Find "View Round Results" links for this tournament
    round_links = []
    for a in soup.find_all('a', href=True):
        if 'View Round Results' in a.get_text():
            href = a['href']
            if href.startswith('/'):
                href = 'https://www.askfred.net' + href
            round_links.append(href)
    
    print(f"  Found {len(round_links)} round result links")
    
    de_links = []
    # Scrape round results for each event
    for round_link in round_links:
        print(f"    Scraping round results: {round_link}")
        time.sleep(1)
        res = requests.get(round_link, headers=headers, timeout=20)
        res.raise_for_status()
        round_soup = BeautifulSoup(res.text, "html.parser")
        
        # get de links for this round
        for a in round_soup.find_all('a', href=True):
            if 'Next Round' in a.get_text():
                href = a['href']
                if href.startswith('/'):
                    href = 'https://www.askfred.net' + href
                de_links.append(href)

        # Get event name from title
        title = round_soup.find('title')
        if title:
            title_text = title.get_text()
            # Extract event name from "TOURNAMENT | EVENT | AskFRED"
            title_parts = title_text.split('|')
            if len(title_parts) >= 2:
                event_name = title_parts[1].strip()
            else:
                event_name = "Unknown Event"
        else:
            event_name = "Unknown Event"
        
        # Find the results table
        tables = round_soup.find_all('table')
        if not tables:
            continue
            
        table = tables[0]  # Usually the first table
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
            
        # Get column headers
        header_row = rows[0]
        table_headers = [cell.get_text(strip=True) for cell in header_row.find_all(['th', 'td'])]
        
        # Process each fencer row
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < len(table_headers):
                continue
                
            # Extract data
            competitor_club = cells[0].get_text(strip=True)
            
            # Parse competitor and club
            if '(' in competitor_club and competitor_club.endswith(')'):
                competitor, club_part = competitor_club.rsplit('(', 1)
                club = club_part.rstrip(')')
                competitor = competitor.strip()
            else:
                competitor = competitor_club
                club = "unaffiliated"
            
            # Round results (columns 1 to len(table_headers)-4, since last 4 are V(%), TS, TR, Ind, Pl)
            round_data = {}
            for i in range(1, len(table_headers) - 4):
                if i < len(cells):
                    round_data[f'round_{i}'] = cells[i].get_text(strip=True)
            
            # Summary stats (skip V(%), keep TS, TR, Ind, Pl)
            touches_scored = cells[len(table_headers)-4].get_text(strip=True) if len(cells) > len(table_headers)-4 else ""
            touches_received = cells[len(table_headers)-3].get_text(strip=True) if len(cells) > len(table_headers)-3 else ""
            indicator = cells[len(table_headers)-2].get_text(strip=True) if len(cells) > len(table_headers)-2 else ""
            place = cells[len(table_headers)-1].get_text(strip=True) if len(cells) > len(table_headers)-1 else ""
            
            round_result = {
                'tournament_name': tournament_name,
                'tournament_url': link,
                'organizer': organizer,
                'city': city,
                'province': province,
                'event': event_name,
                'fencer': competitor,
                'club': club,
                'place': place,
                'touches_scored': touches_scored,
                'touches_received': touches_received,
                'indicator': indicator,
                **round_data  # Include all round_X columns
            }
            round_results.append(round_result)
            print(f"      Added round results for: {competitor} ({club})")
    # Scrape additional "Next Round" pages discovered while visiting round result pages
    de_links = list(dict.fromkeys(de_links))
    print(f"  Found {len(de_links)} next-round links to process")
    visited_de_links = set()
    while de_links:
        de_link = de_links.pop(0)
        if de_link in visited_de_links:
            continue
        visited_de_links.add(de_link)

        print(f"      Scraping next round page: {de_link}")
        time.sleep(1)
        res = requests.get(de_link, headers=headers, timeout=20)
        res.raise_for_status()
        de_soup = BeautifulSoup(res.text, "html.parser")

        # Collect any further next-round links from this page
        for a in de_soup.find_all('a', href=True):
            if 'Next Round' in a.get_text():
                href = a['href']
                if href.startswith('/'):
                    href = 'https://www.askfred.net' + href
                if href not in visited_de_links and href not in de_links:
                    de_links.append(href)

        title = de_soup.find('title')
        if title:
            title_text = title.get_text()
            title_parts = title_text.split('|')
            if len(title_parts) >= 2:
                event_name = title_parts[1].strip()
            else:
                event_name = "Unknown Event"
        else:
            event_name = "Unknown Event"

        tables = de_soup.find_all('table')
        if tables:
            table = tables[0]
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue

            header_row = rows[0]
            table_headers = [cell.get_text(strip=True) for cell in header_row.find_all(['th', 'td'])]

            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < len(table_headers):
                    continue

                competitor_club = cells[0].get_text(strip=True)
                if '(' in competitor_club and competitor_club.endswith(')'):
                    competitor, club_part = competitor_club.rsplit('(', 1)
                    club = club_part.rstrip(')')
                    competitor = competitor.strip()
                else:
                    competitor = competitor_club
                    club = "unaffiliated"

                round_data = {}
                for i in range(1, len(table_headers) - 4):
                    if i < len(cells):
                        round_data[f'round_{i}'] = cells[i].get_text(strip=True)

                touches_scored = cells[len(table_headers)-4].get_text(strip=True) if len(cells) > len(table_headers)-4 else ""
                touches_received = cells[len(table_headers)-3].get_text(strip=True) if len(cells) > len(table_headers)-3 else ""
                indicator = cells[len(table_headers)-2].get_text(strip=True) if len(cells) > len(table_headers)-2 else ""
                place = cells[len(table_headers)-1].get_text(strip=True) if len(cells) > len(table_headers)-1 else ""

                round_result = {
                    'tournament_name': tournament_name,
                    'tournament_url': link,
                    'organizer': organizer,
                    'city': city,
                    'province': province,
                    'event': event_name,
                    'fencer': competitor,
                    'club': club,
                    'place': place,
                    'touches_scored': touches_scored,
                    'touches_received': touches_received,
                    'indicator': indicator,
                    **round_data
                }
                round_results.append(round_result)
                print(f"        Added next-round result for: {competitor} ({club})")
        else:
            de_table = de_soup.find('div', class_='de-table')
            if not de_table:
                print(f"        No de-table found on {de_link}")
                continue

            print(f"        Found de-table, inspecting contents...")

            row_containers = []
            for child in de_table.find_all(recursive=False):
                if child.name != 'div':
                    continue
                if child.find('div', class_=lambda c: c and 'col' in c and 'd-flex' in c and 'flex-columns' in c):
                    row_containers.append(child)

            if not row_containers:
                print(f"        No row containers from direct children, trying parent lookup...")
                for col in de_table.find_all('div', class_=lambda c: c and 'col' in c and 'd-flex' in c and 'flex-columns' in c):
                    parent = col.find_parent('div', class_=lambda c: c and 'row' in c)
                    if parent and parent not in row_containers:
                        row_containers.append(parent)
                print(f"        After parent lookup: {len(row_containers)} row containers")

            print(f"        Found {len(row_containers)} DE rows")

            for row in row_containers:
                cols = row.find_all('div', class_=lambda c: c and 'col' in c)
                if len(cols) < 5:
                    continue

                competitor_club = cols[0].get_text(' ', strip=True)
                if '(' in competitor_club and competitor_club.endswith(')'):
                    competitor, club_part = competitor_club.rsplit('(', 1)
                    club = club_part.rstrip(')')
                    competitor = competitor.strip()
                else:
                    competitor = competitor_club
                    club = 'unaffiliated'

                round_data = {}
                for i, col in enumerate(cols[1:-4], start=1):
                    round_data[f'round_{i}'] = col.get_text(' ', strip=True)

                touches_scored = cols[-4].get_text(' ', strip=True)
                touches_received = cols[-3].get_text(' ', strip=True)
                indicator = cols[-2].get_text(' ', strip=True)
                place = cols[-1].get_text(' ', strip=True)

                round_result = {
                    'tournament_name': tournament_name,
                    'tournament_url': link,
                    'organizer': organizer,
                    'city': city,
                    'province': province,
                    'event': event_name,
                    'fencer': competitor,
                    'club': club,
                    'place': place,
                    'touches_scored': touches_scored,
                    'touches_received': touches_received,
                    'indicator': indicator,
                    **round_data
                }
                round_results.append(round_result)
                print(f"        Added next-round result for: {competitor} ({club})")
    
    for table_idx, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) < 2:  # Skip tables with no data rows
            continue
        
        # Get event name from the card header before this table
        # Find the preceding card-header div that contains the event name
        table_parent = table.find_parent('div', class_='card')
        event_name = "Unknown Event"
        if table_parent:
            card_header = table_parent.find('div', class_='card-header')
            if card_header:
                header_text = card_header.get_text(strip=True)
                # Extract event name (everything before the competitor count)
                event_name = header_text.split('Competitors')[0].strip()
        
        print(f"    Processing event: {event_name} ({len(rows)-1} fencers)")
        
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
                'tournament_name': tournament_name,
                'tournament_url': link,
                'organizer': organizer,
                'city': city,
                'province': province,
                'event': event_name,
                'place': place,
                'fencer': fencer_name,
                'club': club
            }
            all_results.append(result)
            print(f"      append: {place}. {fencer_name} ({club})")

print(f"\n--- Total results collected: {len(all_results)} ---")
print(f"--- Total round results collected: {len(round_results)} ---")

# Save to CSV
import csv
if all_results:
    with open('fencing_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['tournament_name', 'organizer', 'city', 'province', 'event', 'place', 'fencer', 'club', 'tournament_url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print("Final results saved to fencing_results.csv")

if round_results:
    # Get all possible round columns dynamically
    all_keys = set()
    for result in round_results:
        all_keys.update(result.keys())
    
    round_fieldnames = ['tournament_name', 'organizer', 'city', 'province', 'event', 'fencer', 'club', 
                       'place', 'touches_scored', 'touches_received', 'indicator', 'tournament_url'] + \
                      sorted([k for k in all_keys if k.startswith('round_')])
    
    with open('fencing_round_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=round_fieldnames)
        writer.writeheader()
        writer.writerows(round_results)
    print("Round results saved to fencing_round_results.csv")
