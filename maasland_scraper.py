import os

from dotenv import load_dotenv, find_dotenv
from selenium import webdriver
from selenium.common import (
    StaleElementReferenceException,
    TimeoutException,
    NoSuchElementException,
)
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from utils import load_previous_items, send_email, save_current_items

# Load environment variables from .env file
load_dotenv(find_dotenv())

# URLs
HOMEPAGE_URL = "https://maaslandrelocation.nl/en/student-campus"

# Path to the JSON file to store previously seen items
JSON_FILE_PATH = "maasland_previous_items.json"

# Email settings
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAILS = os.getenv("RECIPIENT_EMAILS").split(",")

WEBSITE_NAME = "Maasland"

# Website credentials
MAASLAND_EMAIL = os.getenv("MAASLAND_EMAIL")
MAASLAND_PASSWORD = os.getenv("MAASLAND_PASSWORD")


def initialize_webdriver():
    """
    Initializes the WebDriver with the specified options and returns it.

    Returns:
        WebDriver: The initialized WebDriver
        WebDriverWait: The WebDriverWait object
    """
    # Initialize the WebDriver. Define options
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Set window size to ensure elements are correctly positioned and visible.
    options.add_argument("--window-size=1920,1080")

    # Start the WebDriver
    driver = webdriver.Chrome(
        options=options, service=ChromeService(ChromeDriverManager().install())
    )

    # Define wait object
    wait = WebDriverWait(driver, 20)

    return driver, wait


def login_on_website(driver, wait):
    """
    Logs in to the website using the provided credentials.

    Args:
        driver (WebDriver): The WebDriver object.
        wait (WebDriverWait): The WebDriverWait object.
    """
    # Navigate to the homepage
    driver.get(HOMEPAGE_URL)

    while True:
        try:
            # Wait for the button element with class 'account-name login' to be clickable
            login_link = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[@id='header-top']/section[1]/nav/div/ul/li/a")
                )
            )
            # Click the button
            login_link.click()
            break
        except StaleElementReferenceException:
            # Retry finding the element and clicking it
            continue

    # Wait for the page to load and display the elements
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))

    # Wait for the email input field to be visible using XPath
    email_input = wait.until(
        EC.visibility_of_element_located((By.XPATH, "//input[@type='email']"))
    )

    # Wait for the password input field to be visible using XPath
    password_input = wait.until(
        EC.visibility_of_element_located((By.XPATH, "//input[@type='password']"))
    )

    # You can now interact with the email and password input fields
    email_input.send_keys(MAASLAND_EMAIL)
    password_input.send_keys(MAASLAND_PASSWORD)

    # Wait for the sign-in button to be clickable (if needed)
    sign_in_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
    )

    # Click the sign-in button
    sign_in_button.click()

    # Wait for the homepage to load by waiting for the div element with class 'offer-results' to be visible
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "offer-results")))


def fetch_rental_places_url(driver, wait):
    """
    Fetches rental places URLs from the Maasland homepage using Selenium.

    Args:
        driver (WebDriver): The WebDriver object.
        wait (WebDriverWait): The WebDriverWait object

    Returns:
        list: A list of URLs of all available rental places.
    """

    # Go to the homepage URL if not there already
    if driver.current_url != HOMEPAGE_URL:
        driver.get(HOMEPAGE_URL)

    # Wait for the div element with class 'offer-results' to be visible
    offer_results = wait.until(
        EC.visibility_of_element_located((By.CLASS_NAME, "offer-results"))
    )

    # Find all div elements with class 'offer' within the offer-results div
    offers = offer_results.find_elements(By.CLASS_NAME, "offer")

    # Initialize an empty list to store hrefs
    offer_hrefs = []

    # Loop through each offer and extract the href attribute
    for offer in offers:
        href = offer.find_element(By.TAG_NAME, "a").get_attribute("href")
        offer_hrefs.append(href)

    return offer_hrefs


def is_property_relevant(place_url, driver, wait):
    """
    Discerns whether a property is relevant based on its metadata. First, it checks whether the
    property is eligible for allowance. If yes, it is considered a relevant property. If not, this
    info is not available or cannot be found, it looks for the keyword 'Single-Ed' in the property
    description.

    Args:
        place_url (str): The URL of the property.
        driver (WebDriver): The WebDriver object.
        wait (WebDriverWait): The WebDriverWait object.

    Returns:
        bool: True if the property is relevant, False otherwise.
    """

    if driver.current_url != place_url:
        # Navigate to the property URL
        driver.get(place_url)

    # Wait for the relevant metadata to be visible
    try:
        metadata_section = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div.detail-section.rent")
            )
        )
        description_section = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "section.intro > article > div.description.prose")
            )
        )
    except TimeoutException:
        return False

    # Check for housing allowance information
    try:
        housing_allowance = metadata_section.find_element(
            By.XPATH,
            ".//dt[contains(text(), 'housing allowance')]/following-sibling::dd",
        ).text
        if "housing allowance possible" in housing_allowance.lower():
            return True
    except NoSuchElementException:
        pass

    # Check for 'Single-Ed' in the description
    description_text = description_section.text
    if "single-ed" in description_text.lower():
        return True

    return False


def fetch_relevant_properties(properties_urls, driver, wait):
    """
    Given a list of properties URLs, find the ones that are relevant (i.e. studios that are eligible
    for the rent allowance) and returns a list of dictionaries with their basic metadata (address, cost, link).

    Args:
        properties_urls: A list of URLs of the properties.
        driver: The WebDriver object.
        wait: The WebDriverWait object.

    Returns:
        A list of dictionaries containing the basic metadata of the relevant properties.
    """
    relevant_properties = []

    for url in properties_urls:
        if is_property_relevant(url, driver, wait):
            try:
                # Navigate to the property URL if not already there
                if driver.current_url != url:
                    driver.get(url)

                # Wait for the name section to be visible
                name_section = wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "section.intro > article > h2")
                    )
                )
                address = name_section.text.strip()

                # Wait for the cost section to be visible
                cost_section = wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "div.detail-section.rent")
                    )
                )
                basic_rent = (
                    cost_section.find_element(
                        By.XPATH,
                        ".//dt[contains(text(), 'basic rent')]/following-sibling::dd",
                    )
                    .text.replace(" / month", "")
                    .replace("\u2009", "")
                    .strip()
                )
                total_rent = (
                    cost_section.find_element(
                        By.XPATH,
                        ".//dt[contains(text(), 'rent total')]/following-sibling::dd",
                    )
                    .text.replace(" / month", "")
                    .replace("\u2009", "")
                    .strip()
                )

                cost = f"{basic_rent} (total: {total_rent})"

                # Append the relevant property metadata to the list
                relevant_properties.append(
                    {"address": address, "cost": cost, "link": url}
                )
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Error fetching property metadata: {e}")
                continue

    return relevant_properties


def main():
    """
    Main function that fetches current rental places, compares them with previous items,
    and sends an email if there are new rental places. Saves current items only if email
    was sent successfully.
    """

    print("Starting Maasland scraper...")

    driver, wait = initialize_webdriver()

    # Log in to the website
    login_on_website(driver, wait)

    # Get all the rental places URLs
    properties_urls = fetch_rental_places_url(driver, wait)

    # Extract the properties of the relevant rental places
    current_items = fetch_relevant_properties(properties_urls, driver, wait)

    # Now compare the newly found properties with the previous ones and send email if needed
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
        print("No new rental places found on Maasland.")
        return

    was_email_successful = False
    if new_items:
        print("New rental places found on Maasland:")
        for item in new_items:
            print(f"{item['address']}, {item['cost']}")
        was_email_successful = send_email(
            WEBSITE_NAME, new_items, GMAIL_USER, GMAIL_PASSWORD, RECIPIENT_EMAILS
        )

    if removed_items:
        print("Rental places removed from Maasland:")
        for item in removed_items:
            print(f"{item['address']}, {item['cost']}")

    if was_email_successful:
        save_current_items(JSON_FILE_PATH, current_items)


if __name__ == "__main__":
    main()
