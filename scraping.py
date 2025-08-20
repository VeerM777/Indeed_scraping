import psycopg2
import time
import os
import random
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
CHROME_BINARY_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"


def setup_database():
    """Sets up the PostgreSQL database and the job_listings table."""
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cur = conn.cursor()
        print("Database connection successful. ✅")
        # Use DROP TABLE IF EXISTS to ensure a clean slate for each run
        cur.execute("DROP TABLE IF EXISTS job_listings;")
        cur.execute("""
            CREATE TABLE job_listings (
                id SERIAL PRIMARY KEY,
                job_title VARCHAR(255),
                company_name VARCHAR(255),
                location VARCHAR(255),
                job_url VARCHAR(512) UNIQUE,
                salary_info TEXT,
                job_description TEXT,
                source_site VARCHAR(100),
                scraped_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("Table 'job_listings' is ready. ✅")
    except Exception as e:
        print(f"Database setup error: {e} ❌")
    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()

def get_webdriver():
    """Returns a new configured WebDriver instance."""
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    service = Service(executable_path=CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def scrape_list_pages():
    """
    Scrapes job listings from Indeed using Selenium and inserts them into the database.
    """
    source_site = "Indeed"
    base_url = "https://www.indeed.com/jobs?q=Data+Analyst"
    
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cur = conn.cursor()

        for page_num in range(0, 20, 10):
            driver = get_webdriver()
            url_to_scrape = f"{base_url}&start={page_num}"
            try:
                driver.get(url_to_scrape)
                print(f"Successfully loaded page {page_num//10 + 1} with Selenium. ✅")

                # Increased wait time for job listings to appear
                wait = WebDriverWait(driver, 30)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "job_seen_beacon")))
                time.sleep(random.uniform(5, 10))

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                job_listings = soup.find_all('div', class_='job_seen_beacon')
                
                if not job_listings:
                    print(f"No job listings found on page {page_num//10 + 1}. Check selectors. ⚠️")
                    continue

                for job in job_listings:
                    try:
                        job_title_elem = job.find('h2', class_='jobTitle')
                        job_title_span = job_title_elem.find('span')
                        job_title = job_title_span['title'].strip() if job_title_span and 'title' in job_title_span.attrs else 'Not specified'

                        company_elem = job.find('span', {'data-testid': 'company-name'})
                        company_name = company_elem.text.strip() if company_elem else 'Not specified'

                        location_elem = job.find('div', {'data-testid': 'text-location'})
                        location = location_elem.text.strip() if location_elem else 'Not specified'

                        salary_elem = job.find('div', class_='css-5ooe72')
                        salary_info = salary_elem.text.strip() if salary_elem else 'Not specified'
                        
                        job_link = job.find('a', class_='jcs-JobTitle')
                        job_url = f"https://www.indeed.com{job_link['href']}" if job_link and 'href' in job_link.attrs else None

                        if job_url:
                            cur.execute("""
                                INSERT INTO job_listings (job_title, company_name, location, job_url, salary_info, source_site)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (job_url) DO NOTHING;
                            """, (job_title, company_name, location, job_url, salary_info, source_site))
                            print(f"Inserted job: {job_title} ✅")
                        else:
                            print("Skipped job with missing URL. ⚠️")
                            
                    except Exception as e:
                        print(f"Error processing job: {e} ❌")
                        continue
                        
                conn.commit()
                print(f"Page {page_num//10 + 1} jobs inserted. ✅")
            
            except Exception as e:
                print(f"Error loading page {page_num//10 + 1}: {e} ❌")
                continue
            finally:
                driver.quit()
                print(f"WebDriver for page {page_num//10 + 1} closed. 🚪")
                time.sleep(random.uniform(5, 10)) # Delay between page loads

    except Exception as e:
        print(f"Scraping error: {e} ❌")
    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()
            print("PostgreSQL connection closed. 🚪")


def scrape_job_descriptions():
    """
    Iterates through stored job URLs and scrapes descriptions using Selenium.
    """
    driver = None
    conn = None
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cur = conn.cursor()
        
        cur.execute("SELECT id, job_url FROM job_listings WHERE job_description IS NULL;")
        jobs_to_scrape = cur.fetchall()

        if not jobs_to_scrape:
            print("No new jobs to scrape descriptions for. 📝")
            return

        print(f"Found {len(jobs_to_scrape)} jobs to scrape descriptions for.")

        driver = get_webdriver()
        wait = WebDriverWait(driver, 30)

        for job_id, job_url in jobs_to_scrape:
            try:
                driver.get(job_url)
                
                # Check for an overlay or popup that might block access
                try:
                    close_button = driver.find_element(By.CSS_SELECTOR, 'button.icl-CloseButton')
                    close_button.click()
                except (NoSuchElementException, WebDriverException):
                    pass # No popup found

                # Wait for the job description to be visible
                description_elem = wait.until(EC.visibility_of_element_located((By.ID, "jobDescriptionText"))) 
                job_description = description_elem.text.strip()

                cur.execute("""
                    UPDATE job_listings
                    SET job_description = %s
                    WHERE id = %s;
                """, (job_description, job_id))
                conn.commit()
                print(f"Updated job ID {job_id} with description ✅")
                time.sleep(random.uniform(2, 5))

            except TimeoutException:
                print(f"Timeout while scraping description for URL {job_url}. Retrying with different selector... ⚠️")
                try:
                    # Alternative selector if primary fails
                    description_elem = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.jobsearch-JobComponent-description')))
                    job_description = description_elem.text.strip()
                    cur.execute("""
                        UPDATE job_listings
                        SET job_description = %s
                        WHERE id = %s;
                    """, (job_description, job_id))
                    conn.commit()
                    print(f"Updated job ID {job_id} with description using alternative selector ✅")
                except Exception as e:
                    print(f"Failed to scrape {job_url} after retrying: {e} ❌")
                    continue
            except Exception as e:
                print(f"Failed to scrape {job_url}: {e} ❌")
                continue

        print("Part 3 completed: Job descriptions updated. ✅")

    except Exception as e:
        print(f"Scraping descriptions error: {e} ❌")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
            print("WebDriver closed. 🚪")
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()
            print("PostgreSQL connection closed. 🚪")

if __name__ == "__main__":
    setup_database()
    scrape_list_pages()
    scrape_job_descriptions()