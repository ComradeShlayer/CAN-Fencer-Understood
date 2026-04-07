# Test script for scraping DE pages from AskFRED using Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Test URL
test_url = "https://www.askfred.net/events/9df29e52-1393-4f6a-ace8-ae8f289e2f2d/round/2"

# Set up Chrome options for headless mode
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Run in background - commented out for testing
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

print("Starting Chrome browser...")
driver = webdriver.Chrome(options=chrome_options)

try:
    print(f"Navigating to: {test_url}")
    driver.get(test_url)

    # Wait for page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # Check if we hit a verification page
    page_source = driver.page_source
    print(f"Page source length: {len(page_source)} characters")
    print("First 500 characters of page source:")
    print(repr(page_source[:500]))

    if "Please Verify You Are Human" in page_source:
        print("Hit verification page. Waiting for manual completion...")
        # Wait up to 60 seconds for user to complete verification
        WebDriverWait(driver, 60).until_not(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Please Verify You Are Human")
        )
        print("Verification completed!")
        page_source = driver.page_source

    if "Forbidden" in page_source:
        print("ERROR: Page shows 'Forbidden' - possible IP blocking")
        print("Full page source:")
        print(page_source)
        driver.quit()
        exit(1)

    soup = BeautifulSoup(page_source, "html.parser")

    # Check page title
    title = soup.find('title')
    if title:
        print(f"Page title: {title.get_text()}")
    else:
        print("No title found")

    print("Page appears to be valid tournament data.")

    # Look for de-table
    de_table = soup.find('div', class_='de-table')
    if not de_table:
        print("No de-table found. Checking for regular table...")
        tables = soup.find_all('table')
        if tables:
            print(f"Found {len(tables)} regular tables instead.")
            # Try parsing the first table as fallback
            table = tables[0]
            rows = table.find_all('tr')
            print(f"Table has {len(rows)} rows")
            if len(rows) > 1:
                header_row = rows[0]
                headers = [cell.get_text(strip=True) for cell in header_row.find_all(['th', 'td'])]
                print(f"Headers: {headers}")
                for i, row in enumerate(rows[1:3], 1):  # Show first 2 data rows
                    cells = [cell.get_text(strip=True) for cell in row.find_all('td')]
                    print(f"Row {i}: {cells}")
        else:
            print("No tables found at all.")
            print("Page body preview:")
            body = soup.find('body')
            if body:
                print(body.get_text()[:1000])
    else:
        print("Found de-table! Parsing DE format...")

        # Parse DE table structure
        row_containers = []
        for child in de_table.find_all(recursive=False):
            if child.name != 'div':
                continue
            if child.find('div', class_=lambda c: c and 'col' in c and 'd-flex' in c and 'flex-columns' in c):
                row_containers.append(child)

        if not row_containers:
            print("No row containers from direct children, trying parent lookup...")
            for col in de_table.find_all('div', class_=lambda c: c and 'col' in c and 'd-flex' in c and 'flex-columns' in c):
                parent = col.find_parent('div', class_=lambda c: c and 'row' in c)
                if parent and parent not in row_containers:
                    row_containers.append(parent)

        print(f"Found {len(row_containers)} DE rows")

        # Parse each row
        for i, row in enumerate(row_containers[:5], 1):  # Show first 5 rows
            cols = row.find_all('div', class_=lambda c: c and 'col' in c)
            if len(cols) < 5:
                print(f"Row {i}: Only {len(cols)} columns, skipping")
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
            for j, col in enumerate(cols[1:-4], start=1):
                round_data[f'round_{j}'] = col.get_text(' ', strip=True)

            touches_scored = cols[-4].get_text(' ', strip=True)
            touches_received = cols[-3].get_text(' ', strip=True)
            indicator = cols[-2].get_text(' ', strip=True)
            place = cols[-1].get_text(' ', strip=True)

            print(f"Row {i}: {place}. {competitor} ({club}) - TS:{touches_scored} TR:{touches_received} Ind:{indicator}")

finally:
    driver.quit()

print("Test complete.")
