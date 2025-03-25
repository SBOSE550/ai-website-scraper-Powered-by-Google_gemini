import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Function to scrape the raw HTML content of a website
def scrape_website(website_url):
    # Path to the Chrome WebDriver executable
    webdriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
    service = Service(webdriver_path)
    driver = webdriver.Chrome(service=service)
    try:
        # Open the website URL
        driver.get(website_url)
        # Wait until the page body is fully loaded
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # Additional wait time to allow the website to load completely
        time.sleep(2)
        # Get the page source (HTML content)
        html_content = driver.page_source
        return html_content
    finally:
        # Ensure the browser is closed after scraping
        driver.quit()

# Function to extract the body content from the HTML
def extract_body_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # Extract the <body> tag content
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""

# Function to clean the body content by removing scripts, styles, and extra whitespace
def clean_body_content(body_content):
    soup = BeautifulSoup(body_content, "html.parser")
    # Remove all <script> and <style> tags
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()
    # Extract and clean the text content
    cleaned_content = soup.get_text(separator="\n")
    # Remove empty lines and strip extra spaces
    cleaned_content = "\n".join(line.strip() for line in cleaned_content.splitlines() if line.strip())
    return cleaned_content

# Function to split large DOM content into smaller chunks
def split_dom_content(dom_content, max_length=5000):
    # Split the content into chunks of specified maximum length
    return [dom_content[i : i + max_length] for i in range(0, len(dom_content), max_length)]

# Function to detect if a login form is present on the page
def detect_login_required(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # Check for the presence of an <input> tag with type="password"
    return bool(soup.find("input", {"type": "password"}))

# Function to log in to a website and scrape content after authentication
def login_and_scrape(website_url, username, password):
    # Path to the Chrome WebDriver executable
    webdriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
    service = Service(webdriver_path)
    driver = webdriver.Chrome(service=service)
    try:
        # Open the website URL
        driver.get(website_url)
        # Wait until the login form (password field) is present
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        
        # Locate the username field (try multiple selectors for flexibility)
        try:
            user_field = driver.find_element(By.XPATH, "//input[@name='username'] | //input[@id='username']")
        except Exception:
            # Fallback to a generic text input field
            user_field = driver.find_element(By.XPATH, "//input[@type='text']")
        
        # Locate the password field
        password_field = driver.find_element(By.XPATH, "//input[@type='password']")
        
        # Enter the username and password
        user_field.send_keys(username)
        password_field.send_keys(password)
        
        # Locate and click the submit button (try multiple selectors for flexibility)
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
        submit_btn.click()
        
        # Wait until the login form disappears (indicating successful login)
        WebDriverWait(driver, 10).until_not(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        time.sleep(5)  # Additional delay after login for page content to load
        # Wait until the page body is fully loaded after login
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Get the page source (HTML content) after login
        html_content = driver.page_source
        return html_content
    finally:
        # Ensure the browser is closed after scraping
        driver.quit()
