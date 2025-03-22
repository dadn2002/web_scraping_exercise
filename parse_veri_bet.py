import requests
import urllib3
import time
import json
import os

from datetime import datetime, timezone
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from header import *
from problem_parameters import Item

"""
    Would like to inform that i'm playing a chess tournament so i'm really tired, also i could'nt find
    a better way to directly select the parameters from the table odds-picks. I slept while doing that
    and i would say i spent over 3 hours doing that (A lot of distractions but in the end it worked at
    least).

    Note: I know it's not perfect, it did not reached the instructions, but the path is already there,
    just minor position finding. I spent most of my time trying to do things in a "nicer" way, didn't
    worked well...

    Note2: Check header.py if you want more feedback, just uncomment the functions.
"""


# gecko_path = "/usr/local/bin/geckodriver"
gecko_path = "dependences/geckodriver"
url = "https://veri.bet/odds-picks"
main_table_id = "odds-picks"
max_attempts = 10000

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def compare_and_update_items(items_list, old_items):
    updated_items = []
    
    old_items_dict = {item.team1 + item.team2 + item.event_date_utc: item for item in old_items}
    
    for new_item in items_list:
        key = new_item.team1 + new_item.team2 + new_item.event_date_utc
        if key not in old_items_dict:
            updated_items.append(("new", new_item))
        else:
            old_item = old_items_dict[key]
            if (new_item.price != old_item.price or new_item.spread != old_item.spread or new_item.side != old_item.side):
                updated_items.append(("updated", new_item))

    return updated_items

def print_updated_items(updated_items):
    """Print updated or new items in human-readable format and JSON format."""
    output_list = []
    for status, item in updated_items:
        status_str = "New" if status == "new" else "Updated"
        info(f"{status_str} Item: {item.team1} vs {item.team2}, Date: {item.event_date_utc}, Price: {item.price}, Spread: {item.spread}, Total: {item.side}")
        
        item_dict = {
            "team1": item.team1,
            "team2": item.team2,
            "event_date_utc": item.event_date_utc,
            "price": item.price,
            "spread": item.spread,
            "side": item.side,
            "line_type": item.line_type,
            "sport_league": item.sport_league,
            "period": item.period
        }
        output_list.append(item_dict)

    info("\nJSON Output:")
    print(json.dumps(output_list, indent=4))

def setup_driver() -> webdriver.Firefox:
    driver = None

    try:
        options = Options()
        options.headless = True
        service = Service(gecko_path)

        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        driver = webdriver.Firefox(service=service, options=options)

        return driver
    except Exception as e:
        warn(f"Failed to setup driver with code: {e}")
        return None

def get_response_of_url(driver: webdriver.Firefox, url: str = "") -> str:
    """
        Returns response of a request to $url.
    """
    
    if url is None:
        warn(f"Empty url, could'nt make a request")
        return None
    
    try:
        driver.get(url)
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, main_table_id))
        )
        return driver.page_source
    except Exception as e:
        warn(f"Request failed with code: {e}")
        return None

def extract_objects_text_from_response(soup: BeautifulSoup):
    odds_picks_table = soup.find('table', {'id': main_table_id})
    rows = odds_picks_table.find_all('tr')    
    content = [[cell.get_text(strip=True).replace("\t", "").replace("\n", " ") for cell in row.find_all(['td', 'th'])] for row in rows]

    return content

def parse_table_to_items_from_data(table_data: list) -> list[Item]:
    items = []
    current_league = ""
    for element in table_data:
        if type(element) is not list:
            continue
        if len(element) == 1:
            continue
        
        if "TrendSpotter" in element[1]:
            current_league = element[1].split(" ")[0]
            # print(f"League: {current_league}")
        
        if len(element) > 11 and "FULL GAME  ODD" in element[0]:
            del element[0]

            for i in range(0, len(element), 8):
                # print(element)

                team1   = element[4]
                team2   = element[14]
                pitcher = ""
                period  = element[25].replace("NBA", "")

                # Placeholder
                event_date_utc = "2025-03-22T00:00:00Z"

                for line_type in [["moneyline", 8, 19], ["spread", 10, 21], ["over/under", 12, 23]]:
                    item1 = Item(
                        sport_league=current_league,
                        event_date_utc=event_date_utc,
                        team1=team1,
                        team2=team2,
                        pitcher=pitcher,
                        period=period,
                        line_type=str(line_type[0]),
                        price=str(element[line_type[1]].split("(")[1].replace(")", "")) if "(" in element[line_type[2]] else str(element[line_type[2]]),
                        side=element[12][0] if line_type[0] == "over/under" else team1,
                        # spread=float(element[line_type[1]].split(" ")[1] if line_type[0] == "SPREAD" else 0),
                        spread = 0
                    )

                    item2 = Item(
                        sport_league=current_league,
                        event_date_utc=event_date_utc,
                        team1=team1,
                        team2=team2,
                        pitcher=pitcher,
                        period=period,
                        line_type=str(line_type[0]),
                        price=str(element[line_type[2]].split("(")[1].replace(")", "")) if "(" in element[line_type[2]] else str(element[line_type[2]]),
                        side=element[23][0] if line_type[0] == "over/under" else team2,
                        # spread=float(element[line_type[2]].split(" ")[1] if line_type[0] == "SPREAD" else 0),
                        spread = 0
                    )

                    items.append(item1)
                    items.append(item2)
                
            print("Data processed and items created.")

    return items


def debug_print_and_save_variable(variable: any, name: str) -> None:
    if not os.path.exists("trash"):
        os.makedirs("trash")

    print(variable)
    with open(f"trash/{name}.txt", "w") as file:
        file.write(str(variable))
        wait()

def main():
    for _ in range(max_attempts): # Remember to replace with while true
        info("Setting up driver")
        for attempt in range(max_attempts):
            # print(f"Attempt {attempt + 1} of {max_attempts}...", end="\r", flush=True)
            driver = setup_driver()
            if driver is not None: 
                # print("")
                okay("Success")
                break
        else:
            warn("Driver is None")
            continue

        old_items = []
        for _ in range(max_attempts):
            info("Getting response from url")
            for attempt in range(max_attempts):
                # print(f"Attempt {attempt + 1} of {max_attempts}...", end="\r", flush=True)
                response = get_response_of_url(driver, url)
                if response is not None:
                    # print("")
                    okay("Success")
                    break
                warn("Response is None")
                continue
            # debug_print_and_save_variable(response, "response")
            
            soup = BeautifulSoup(response, "html.parser")
            data = {}

            extracted_text = extract_objects_text_from_response(soup)
            if extracted_text is None:
                warn("List of items is empty")
                continue
            # debug_print_and_save_variable(extracted_text, "extracted_text")

            items_list = parse_table_to_items_from_data(extracted_text)
            if items_list is None:
                warn("List of items is empty")
                continue
            # debug_print_and_save_variable(items_list, "items_list")

            updated_items = compare_and_update_items(items_list, old_items)
            if updated_items:
                clear_screen()
                print_updated_items(updated_items)
                
                old_items = items_list.copy()
                time.sleep(5)


    driver.quit()

if __name__ == "__main__":
    main()
    
