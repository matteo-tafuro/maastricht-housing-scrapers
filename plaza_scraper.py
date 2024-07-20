import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv, find_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os

# Load environment variables from .env file
load_dotenv(find_dotenv())

# URL of the rental finder website
url = (
    "https://plaza.newnewnew.space/en/availables-places/living-place"
    "#?gesorteerd-op=prijs%2B&land=524&locatie=Maastricht-Nederland%2B-%2BLimburg"
)

# Path to the JSON file to store previously seen items
json_file_path = "previous_items.json"

# Email settings
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_APP_PASSWORD")
recipient_emails = os.getenv("RECIPIENT_EMAILS").split(",")


def fetch_rental_places(url):
    """
    Fetches rental places from the specified URL using Selenium.

    Args:
        url (str): The URL of the rental finder website.

    Returns:
        list: A list of dictionaries, each containing the address, cost, and link of a rental place.
    """
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
        if cost:
            # Remove the ' p.m' from the cost
            cost = cost.replace(" p.m", "")
            # Transform the part that says 'Total rental price: €XXX.XX' to '(total: €XXX.XX)'
            cost = cost.replace("Total rental price: ", "(total: ")
            cost = cost + ")"
            # Remove newline from cost
            cost = cost.replace("\n", "")
        else:
            cost = "N/A"

        # Create a dictionary with the address, cost, and link
        listing = {"address": address, "cost": cost, "link": link}
        rental_places.append(listing)

    driver.quit()
    return rental_places


def load_previous_items(json_file_path):
    """
    Loads the previously seen rental places from a JSON file.

    Args:
        json_file_path (str): The path to the JSON file.

    Returns:
        list: A list of dictionaries representing previously seen rental places.
    """
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return []


def save_current_items(json_file_path, items):
    """
    Saves the current rental places to a JSON file.

    Args:
        json_file_path (str): The path to the JSON file.
        items (list): A list of dictionaries representing the current rental places.
    """
    items_to_save = [{k: v for k, v in item.items() if k != "link"} for item in items]
    with open(json_file_path, "w", encoding="utf-8") as file:
        json.dump(items_to_save, file, ensure_ascii=False, indent=4)


def send_email(new_items):
    """
    Sends an email with the details of new rental places.

    Args:
        new_items (list): A list of dictionaries representing the new rental places.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    # Set up the email content
    subject = (
        f"{len(new_items)} new rental place{'s' if len(new_items) > 1 else ''} found!"
    )
    body = "New rental places found:\n\n"
    for item in new_items:
        body += f"{item['address']}, {item['cost']}\n{item['link']}\n\n"

    # Create the email
    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipient_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Send the email
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        text = msg.as_string()
        server.sendmail(gmail_user, recipient_emails, text)
        server.quit()
        print("Email sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def main():
    """
    Main function that fetches current rental places, compares them with previous items,
    and sends an email if there are new rental places. Saves current items only if email
    was sent successfully.
    """
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
        if send_email(new_items):
            save_current_items(json_file_path, current_items)

    if removed_items:
        print("Removed rental places:")
        for item in removed_items:
            print(f"{item['address']}, {item['cost']}")

    if not new_items:
        save_current_items(json_file_path, current_items)


if __name__ == "__main__":
    main()
