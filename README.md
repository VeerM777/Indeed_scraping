# Indeed Job Scraping Project

This project is a Python web scraper designed to collect job market data for "Data Analyst" positions from Indeed.com. It fulfills the requirements of the Python Web Scraper Internship practical assessment from International Credit Score. The scraper performs a multi-stage process: it gathers summary information (job title, company name, location, salary, and URL) from the first two pages of Indeed's search results, then scrapes detailed job descriptions from individual job pages, and stores the data in a PostgreSQL database.

## Features
- Scrapes up to 20 job listings (2 pages) using Selenium.
- Extracts job descriptions with fallback selectors for robustness.
- Stores data in a PostgreSQL `job_listings` table, recreated on each run.
- Implements random delays to mimic human behavior and avoid anti-bot detection.

## Technical Approach

### Libraries
- **Selenium**: Handles Indeed's dynamic content and anti-bot measures, chosen over `requests` and `BeautifulSoup` due to dynamic loading and bot protection.
- **psycopg2**: Manages PostgreSQL database connectivity.
- **BeautifulSoup**: Parses HTML from Selenium-rendered pages.
- **python-dotenv**: Secures environment variables.

### Data Flow
1. **Setup**: Drops and recreates the `job_listings` table in PostgreSQL on each run.
2. **Listing Scraping**: Collects summary data from Indeed search results (pages 0-10) and inserts it into the database.
3. **Description Scraping**: Retrieves stored job URLs, visits each page, and updates the database with job descriptions using primary and fallback selectors.

### Error Handling
- Robust `try...except` blocks handle timeouts, missing elements, and network issues.
- Fallback selectors (e.g., `.jobsearch-JobComponent-description`) ensure description scraping resilience.
- Graceful cleanup of WebDriver and database connections.

## Setup and Execution

### Prerequisites
- Python 3.x installed.
- PostgreSQL server running.
- Chrome browser and ChromeDriver installed (paths configured in `scraping.py`).

### Database Setup
1. Create a new database (e.g., `internship_assessment`):
   ```sql
   CREATE DATABASE internship_assessment;
   ```
2. The script automatically drops and recreates the `job_listings` table on each run.

### Local Environment Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/VeerM777/Indeed_scraping.git
   ```
2. Navigate to the project directory:
   ```bash
   cd Indeed_scraping/webscrapping_task
   ```
3. Create a virtual environment (recommended):
   - Windows: `python -m venv env` then `env\Scripts\activate`
   - macOS/Linux: `python -m venv env` then `source env/bin/activate`
4. Install dependencies (generate `requirements.txt` if needed):
   ```bash
   pip install beautifulsoup4 psycopg2-binary python-dotenv selenium
   pip freeze > requirements.txt
   ```

### Configuration
1. Create a `.env` file in the `webscrapping_task` directory:
   ```
   DB_NAME="your_database_name"
   DB_USER="your_username"
   DB_PASS="your_password"
   DB_HOST="your_host"
   ```
2. Update `CHROME_BINARY_PATH` and `CHROMEDRIVER_PATH` in `scraping.py` to match your system (e.g., `C:\path\to\chrome.exe` and `C:\path\to\chromedriver.exe`).

### Running the Script
Execute the script from the `webscrapping_task` directory:
```bash
python scraping.py
```
- The script will:
  - Recreate the `job_listings` table.
  - Scrape job listings from the first two pages.
  - Scrape job descriptions and update the database.
- Progress messages (e.g., ✅ for success, ❌ for errors) will be displayed.

