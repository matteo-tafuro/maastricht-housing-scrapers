import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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


def send_email(new_items, gmail_user, gmail_password, recipient_emails):
    """
    Sends an email with the details of new rental places.

    Args:
        new_items (list): A list of dictionaries representing the new rental places.
        gmail_user (str): The Gmail username used to send the email.
        gmail_password (str): The Gmail password used to send the email.
        recipient_emails (list): A list of email addresses to send the email to.

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
