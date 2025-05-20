import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin

def get_user_input():
    website_url = input("Enter the website URL to scrape: ")
    num_pages = int(input("Enter the number of pages to scrape: "))
    return website_url, num_pages

def detect_pagination_pattern(url):
    """Detect the pagination pattern from the URL"""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Common pagination parameter names
    pagination_params = ['page', 'p', 'pg', 'pageno', 'pagenumber', 'page_number']
    
    # Check if URL already has a pagination parameter
    for param in pagination_params:
        if param in query_params:
            return param
    
    # If no pagination parameter found, return default
    return 'page'

def construct_pagination_url(url, page_num, pagination_param):
    """Construct URL with proper pagination"""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Remove existing pagination parameter if it exists
    for param in ['page', 'p', 'pg', 'pageno', 'pagenumber', 'page_number']:
        if param in query_params:
            del query_params[param]
    
    # Add new pagination parameter
    query_params[pagination_param] = [str(page_num)]
    
    # Reconstruct URL
    new_query = urlencode(query_params, doseq=True)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

def find_next_page_link(driver, soup):
    """Find the next page link in the current page"""
    print("\nSearching for next page link...")
    
    # Common patterns for next page links
    next_link_patterns = [
        "//a[contains(@class, 'next')]",
        "//a[contains(@class, 'pagination-next')]",
        "//a[contains(@rel, 'next')]",
        "//a[contains(text(), 'Next')]",
        "//a[contains(text(), 'Next Page')]",
        "//a[contains(@aria-label, 'Next')]",
        "//a[contains(@title, 'Next')]",
        "//a[contains(@class, 'pagination') and contains(text(), '»')]",
        "//a[contains(@class, 'pagination') and contains(text(), '>')]",
        "//a[contains(@class, 'pagination')]//following-sibling::a",
        "//a[contains(@class, 'pagination')]//following::a[1]"
    ]
    
    # Try to find next link using Selenium
    for pattern in next_link_patterns:
        try:
            print(f"Trying XPath pattern: {pattern}")
            next_element = driver.find_element(By.XPATH, pattern)
            if next_element and next_element.is_displayed():
                href = next_element.get_attribute('href')
                print(f"Found next link with pattern {pattern}: {href}")
                return href
        except Exception as e:
            print(f"Pattern {pattern} not found: {str(e)}")
            continue
    
    # If Selenium fails, try BeautifulSoup
    print("\nTrying BeautifulSoup selectors...")
    
    # Try different BeautifulSoup selectors
    selectors = [
        ('a', {'class_': lambda x: x and ('next' in x.lower() or 'pagination-next' in x.lower())}),
        ('a', {'rel': 'next'}),
        ('a', {'string': lambda x: x and 'Next' in x}),
        ('a', {'class_': 'pagination-next'}),
        ('a', {'class_': 'next'}),
        ('a', {'aria-label': lambda x: x and 'Next' in x}),
        ('a', {'title': lambda x: x and 'Next' in x})
    ]
    
    for tag, attrs in selectors:
        try:
            print(f"Trying selector: {tag} with {attrs}")
            next_link = soup.find(tag, attrs)
            if next_link and next_link.get('href'):
                href = next_link['href']
                print(f"Found next link with selector {tag}: {href}")
                return href
        except Exception as e:
            print(f"Selector {tag} not found: {str(e)}")
            continue
    
    print("No next page link found")
    return None

def get_page_content(driver, url):
    """Get page content with proper waiting and verification"""
    try:
        print(f"\nNavigating to URL: {url}")
        driver.get(url)
        
        # Wait for body to be present
        print("Waiting for body element...")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Wait for page to be fully loaded
        print("Waiting for page to be fully loaded...")
        WebDriverWait(driver, 20).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        
        # Additional wait for dynamic content
        print("Waiting for dynamic content...")
        time.sleep(5)
        
        # Get current URL to verify we're on the correct page
        current_url = driver.current_url
        print(f"Current URL after navigation: {current_url}")
        
        # Additional wait for any JavaScript content to load
        print("Waiting for JavaScript content...")
        time.sleep(2)
        
        # Get page source
        html_content = driver.page_source
        print(f"Page content length: {len(html_content)} characters")
        
        # Basic content verification
        if len(html_content) < 100:
            print(f"Warning: Page content seems too short ({len(html_content)} characters)")
            return None
            
        return html_content
    except Exception as e:
        print(f"Error getting page content: {str(e)}")
        return None

def scrape_multiple_pages(website_url, num_pages):
    """Scrape multiple pages by following 'Next' links"""
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    all_pages_content = []
    current_url = website_url
    pages_scraped = 0
    
    try:
        print(f"\nStarting multi-page scraping for URL: {website_url}")
        print(f"Number of pages to scrape: {num_pages}")
        
        while pages_scraped < num_pages:
            print(f"\nProcessing page {pages_scraped + 1} of {num_pages}")
            print(f"Current URL: {current_url}")
            
            # Get page content
            html_content = get_page_content(driver, current_url)
            if not html_content:
                print("Failed to get page content")
                break
                
            # Parse the content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Process the content
            body_content = extract_body_content(html_content)
            cleaned_content = clean_body_content(body_content)
            
            # Verify content is different from previous page
            if len(all_pages_content) > 0 and cleaned_content == all_pages_content[-1]:
                print("Warning: Page content is identical to previous page")
                break
                
            # Add the cleaned content to our list
            all_pages_content.append(cleaned_content)
            pages_scraped += 1
            print(f"Successfully scraped page {pages_scraped}")
            
            # Find next page link
            if pages_scraped < num_pages:
                next_url = find_next_page_link(driver, soup)
                if not next_url:
                    print("No next page link found")
                    break
                    
                # Make sure the next URL is absolute
                next_url = urljoin(current_url, next_url)
                print(f"Found next page URL: {next_url}")
                
                # Update current URL
                current_url = next_url
                
                # Add delay between page requests
                print("Waiting before next page request...")
                time.sleep(3)
            else:
                print("Reached desired number of pages")
                break
            
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
    finally:
        driver.quit()
    
    print(f"\nScraping complete. Retrieved {len(all_pages_content)} unique pages.")
    return all_pages_content

# Function to scrape the raw HTML content of a website
def scrape_website(website_url):
    # Use ChromeDriverManager to automatically handle driver installation
    service = Service(ChromeDriverManager().install())
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
    # Use ChromeDriverManager to automatically handle driver installation
    service = Service(ChromeDriverManager().install())
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

def main():
    website_url, num_pages = get_user_input()
    
    if num_pages > 1:
        # Scrape multiple pages
        all_pages_content = scrape_multiple_pages(website_url, num_pages)
        
        # Save the content to separate files
        for i, content in enumerate(all_pages_content, 1):
            filename = f"scraped_page_{i}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Content from page {i} saved to {filename}")
    else:
        # Scrape single page
        html_content = scrape_website(website_url)
        body_content = extract_body_content(html_content)
        cleaned_content = clean_body_content(body_content)
        
        # Save the content to a file
        with open("scraped_content.txt", "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        print("Content saved to scraped_content.txt")

if __name__ == "__main__":
    main()
