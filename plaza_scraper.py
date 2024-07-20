from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import time

# URL of the rental finder website
url = "https://plaza.newnewnew.space/en/availables-places/living-place#?gesorteerd-op=prijs%2B&land=524&locatie=Maastricht-Nederland%2B-%2BLimburg"

# Path to the JSON file to store previously seen items
json_file_path = "previous_items.json"


def fetch_rental_places(url):
    # Initialize the WebDriver. Define options
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Start the WebDriver
    driver = webdriver.Chrome(
        options=options, service=ChromeService(ChromeDriverManager().install())
    )
    driver.get(url)
    # Wait for the page to load and display the elements
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/main/div/div[3]/div/div/div/div/div/div/div/div/div/div[3]/div/div[2]",
            )
        )
    )

    # Extract the desired div using XPath
    rental_div = driver.find_element(
        By.XPATH,
        "/html/body/main/div/div[3]/div/div/div/div/div/div/div/div/div/div[3]/div/div[2]",
    )
    rental_sections = rental_div.find_elements(By.TAG_NAME, "section")

    # Get the address and cost from each section
    rental_places = []
    for section in rental_sections:

        # Extract the href associated with the section
        link_element = section.find_element(By.TAG_NAME, "a")
        link = link_element.get_attribute("href")

        # Extract the address
        address_element = section.find_element(By.CLASS_NAME, "address-part.ng-binding")
        address = address_element.text
        cost_element = section.find_element(By.CLASS_NAME, "kosten.ng-scope")

        # Extract the cost and format it
        cost = cost_element.text
        # Remove the ' p.m' from the cost
        cost = cost.replace(" p.m", "")
        # Transform the part that says 'Total rental price: €XXX.XX' to '(total: €XXX.XX)'
        cost = cost.replace("Total rental price: ", "(total: ")
        cost = cost + ")"
        # Remove newline from cost
        cost = cost.replace("\n", "")

        # Create a dictionary with the address, cost, and link
        listing = {"address": address, "cost": cost, "link": link}
        rental_places.append(listing)

    driver.quit()
    return rental_places


def load_previous_items(json_file_path):
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return []


def save_current_items(json_file_path, items):
    items_to_save = [{k: v for k, v in item.items() if k != "link"} for item in items]
    with open(json_file_path, "w", encoding="utf-8") as file:
        json.dump(items_to_save, file, ensure_ascii=False, indent=4)


def main():
    current_items = fetch_rental_places(url)
    previous_items = load_previous_items(json_file_path)

    current_items_without_links = [
        {k: v for k, v in item.items() if k != "link"} for item in current_items
    ]
    new_items = [
        item
        for item in current_items
        if {k: v for k, v in item.items() if k != "link"} not in previous_items
    ]
    removed_items = [
        item for item in previous_items if item not in current_items_without_links
    ]

    if new_items:
        print("New rental places found:")
        for item in new_items:
            print(f"{item['address']}, {item['cost']}")

    if removed_items:
        print("Removed rental places:")
        for item in removed_items:
            print(f"{item['address']}, {item['cost']}")

    save_current_items(json_file_path, current_items)


if __name__ == "__main__":
    main()
