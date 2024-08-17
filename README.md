# Rental Scraper

This project is a scraper that checks rental listing websites for new places and sends an email notification if new places are found. The scraper uses Selenium to fetch rental data and Gmail to send email notifications.

The websites currently supported are:
- [Maasland](https://maaslandrelocation.nl/en/)
- [Plaza](https://plaza.newnewnew.space/en/)

## Prerequisites

- Python 3.9
- Google Chrome
- ChromeDriver

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/rental-scraper.git
cd rental-scraper
```

### 2. Create a Virtual Environment
```bash
conda env create -f environment.yaml
conda activate rental_scraper
```



### 3. Set Up Environment Variables
Create a .env file in the project directory and add the following variables (see `.env.example` for reference):
```bash
GMAIL_USER=your@email.com
GMAIL_APP_PASSWORD=your_password
RECIPIENT_EMAILS=first@recipient.com,second@recipient.com

MAASLAND_EMAIL=your@email.com
MAASLAND_PASSWORD=your_password
```

The Maasland credentials are used to preview available rental places that are not publicly listed on the website yet.

**Important:** The `GMAIL_APP_PASSWORD` is not the same as your regular Gmail account password. It is an app-specific password that you need to generate in your Google account settings. You can find detailed instructions on how to create an app password on the [Google Account Help page](https://support.google.com/accounts/answer/185833?hl=en).

## Usage

Run the scraper:
```
python <website_name>_scraper.py
```
The script will:
1. Fetch current rental places from the specified URL. Info about the currently available places are saved to a JSON file.
2. Compare the current rental places with previously seen items.
3. Send an email if new rental places are found.
4. Save the current rental places to a JSON file if the email is sent successfully.

## Automation
You can use a cron job to automate the process. For example, to run the script every 5 minutes, you can add the following line to your crontab file:

```bash
*/5 * * * * /path/to/your/conda/environment/bin/python /path/to/your/rental_scraper.py
```
To edit your crontab file, run:
```bash
crontab -e
```

Make sure to replace `/path/to/your/conda/environment/bin/python` with the path to your Python interpreter and `/path/to/your/rental_scraper.py` with the path to your script.