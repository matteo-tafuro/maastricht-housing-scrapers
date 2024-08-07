import os
import time

from dotenv import load_dotenv, find_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from utils import send_email, save_current_items, load_previous_items

# Load environment variables from .env file
load_dotenv(find_dotenv())

# URL of the rental finder website
HOMEPAGE_URL = (
    "https://plaza.newnewnew.space/en/availables-places/living-place"
    "#?gesorteerd-op=prijs%2B&land=524&locatie=Maastricht-Nederland%2B-%2BLimburg"
)

# Path to the JSON file to store previously seen items
JSON_FILE_PATH = "plaza_previous_items.json"

# Email settings
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAILS = os.getenv("RECIPIENT_EMAILS").split(",")

WEBSITE_NAME = "Plaza"


def fetch_rental_places(url):
    """
    Fetches rental places from the specified URL using Selenium.

    Args:
        url (str): The URL of the rental finder website.

    Returns:
        list: A list of dictionaries, each containing the address, cost, and link of a rental place.

    Raises:
        Exception: If unable to fetch rental places with address and cost after multiple retries.
    """
    rental_places = []
    max_retries = 5
    retries = 0

    while retries < max_retries:
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
        for section in rental_sections:
            # Extract the href associated with the section
            link_element = section.find_element(By.TAG_NAME, "a")
            link = link_element.get_attribute("href")

            # Extract the address
            address_element = section.find_element(
                By.CLASS_NAME, "address-part.ng-binding"
            )
            address = address_element.text
            cost_element = section.find_element(By.CLASS_NAME, "kosten.ng-scope")

            # Extract the cost and format it
            cost = cost_element.text
            if cost:
                # Remove the ' p.m' from the cost
                cost = cost.replace(" p.m", "")
                # Transform the part that says 'Total rental price: €XXX.XX' to '(total: €XXX.XX)'
                cost = cost.replace("Total rental price: ", "(total: ")
                cost = cost + ")"
                # Remove newline from cost
                cost = cost.replace("\n", "")
            else:
                cost = ""

            # Check if both address and cost are available
            if address and cost:
                # Create a dictionary with the address, cost, and link
                listing = {"address": address, "cost": cost, "link": link}
                rental_places.append(listing)

        driver.quit()

        if rental_places:
            break
        else:
            retries += 1
            time.sleep(5)  # Wait for 5 seconds before retrying

    if not rental_places:
        raise Exception(
            "Failed to fetch rental places with address and cost after multiple retries."
        )

    return rental_places


def main():
    """
    Main function that fetches current rental places, compares them with previous items,
    and sends an email if there are new rental places. Saves current items only if email
    was sent successfully.
    """
    try:
        current_items = fetch_rental_places(HOMEPAGE_URL)
    except Exception as e:
        print(f"Error: {e}")
        return

    previous_items = load_previous_items(JSON_FILE_PATH)

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

    if not new_items and not removed_items:
        print("No new rental places found on Plaza.")
        return

    was_email_successful = False
    if new_items:
        print("New rental places found on Plaza:")
        for item in new_items:
            print(f"{item['address']}, {item['cost']}")
        was_email_successful = send_email(
            WEBSITE_NAME, new_items, GMAIL_USER, GMAIL_PASSWORD, RECIPIENT_EMAILS
        )

    if removed_items:
        print("Rental places removed from Plaza:")
        for item in removed_items:
            print(f"{item['address']}, {item['cost']}")

    if was_email_successful:
        save_current_items(JSON_FILE_PATH, current_items)


if __name__ == "__main__":
    main()
