"""
HTML Web Scraper
Scrapes web pages and saves content in structured markdown format.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import os


def fetch_page_selenium(url: str) -> BeautifulSoup:
    """
    Fetch the HTML content using Selenium (for JavaScript-heavy sites).
    
    Args:
        url: The URL to scrape
        
    Returns:
        BeautifulSoup object or None if failed
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        print("Using Selenium with Chrome...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Get page source
        page_source = driver.page_source
        driver.quit()
        
        return BeautifulSoup(page_source, 'html.parser')
    except ImportError:
        print("Selenium not installed. Install with: pipenv install selenium")
        return None
    except Exception as e:
        print(f"Error with Selenium: {e}")
        print("Make sure Chrome/Chromium and ChromeDriver are installed.")
        return None


def fetch_page(url: str, max_retries: int = 3) -> BeautifulSoup:
    """
    Fetch the HTML content from the URL with retry logic.
    
    Args:
        url: The URL to scrape
        max_retries: Maximum number of retry attempts
        
    Returns:
        BeautifulSoup object or None if failed
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}...")
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=60, allow_redirects=True)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        except Exception as e:
            print(f"Error fetching page on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    
    return None


def extract_title(soup: BeautifulSoup) -> str:
    """Extract the page title."""
    if not soup:
        return "Untitled"
    
    # Try h1 first
    title = soup.find('h1')
    if title:
        return title.get_text(strip=True)
    
    # Try title tag
    title = soup.find('title')
    if title:
        return title.get_text(strip=True)
    
    return "Untitled"


def extract_tables(soup: BeautifulSoup) -> List[List[List[str]]]:
    """Extract all tables from the page."""
    if not soup:
        return []
    
    tables_data = []
    tables = soup.find_all('table')
    
    for table in tables:
        table_data = []
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if any(row_data):  # Only add non-empty rows
                table_data.append(row_data)
        
        if table_data:
            tables_data.append(table_data)
    
    return tables_data


def extract_lists(soup: BeautifulSoup) -> List[Dict[str, any]]:
    """Extract all lists (ul, ol) from the page."""
    if not soup:
        return []
    
    lists_data = []
    for list_tag in soup.find_all(['ul', 'ol']):
        list_type = 'ordered' if list_tag.name == 'ol' else 'unordered'
        items = []
        
        for li in list_tag.find_all('li', recursive=False):
            items.append(li.get_text(strip=True))
        
        if items:
            lists_data.append({'type': list_type, 'items': items})
    
    return lists_data


def extract_paragraphs(soup: BeautifulSoup) -> List[str]:
    """Extract all paragraph text."""
    if not soup:
        return []
    
    paragraphs = []
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text:
            paragraphs.append(text)
    
    return paragraphs


def extract_shortcuts(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract keyboard shortcuts specifically for AutoCAD shortcuts page.
    This looks for common patterns in shortcut documentation.
    """
    if not soup:
        return []
    
    shortcuts = []
    
    # Look for tables with shortcuts
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                shortcut = cells[0].get_text(strip=True)
                description = cells[1].get_text(strip=True)
                if shortcut and description:
                    shortcuts.append({
                        'shortcut': shortcut,
                        'description': description
                    })
    
    return shortcuts


def convert_to_markdown(soup: BeautifulSoup, url: str) -> str:
    """
    Convert extracted content to markdown format.
    
    Args:
        soup: BeautifulSoup object with parsed HTML
        url: Original URL for reference
        
    Returns:
        Markdown formatted string
    """
    if not soup:
        return "# Error\n\nFailed to fetch page content."
    
    md_content = []
    
    # Add title
    title = extract_title(soup)
    md_content.append(f"# {title}\n")
    md_content.append(f"**Source:** {url}\n")
    md_content.append("---\n")
    
    # Try to extract shortcuts first (specific to AutoCAD page)
    shortcuts = extract_shortcuts(soup)
    if shortcuts:
        md_content.append("## Keyboard Shortcuts\n")
        for shortcut in shortcuts:
            md_content.append(f"- **{shortcut['shortcut']}**: {shortcut['description']}")
        md_content.append("\n")
    
    # Extract tables
    tables = extract_tables(soup)
    if tables:
        md_content.append("## Tables\n")
        for i, table in enumerate(tables, 1):
            if len(table) > 0:
                md_content.append(f"### Table {i}\n")
                
                # Create markdown table
                if len(table) > 0:
                    # Header
                    header = table[0]
                    md_content.append("| " + " | ".join(header) + " |")
                    md_content.append("| " + " | ".join(["---"] * len(header)) + " |")
                    
                    # Data rows
                    for row in table[1:]:
                        # Pad row if needed
                        while len(row) < len(header):
                            row.append("")
                        md_content.append("| " + " | ".join(row) + " |")
                
                md_content.append("\n")
    
    # Extract lists
    lists = extract_lists(soup)
    if lists:
        md_content.append("## Lists\n")
        for lst in lists:
            if lst['type'] == 'ordered':
                for i, item in enumerate(lst['items'], 1):
                    md_content.append(f"{i}. {item}")
            else:
                for item in lst['items']:
                    md_content.append(f"- {item}")
            md_content.append("\n")
    
    # Extract paragraphs
    paragraphs = extract_paragraphs(soup)
    if paragraphs:
        md_content.append("## Content\n")
        for para in paragraphs:
            md_content.append(f"{para}\n")
    
    return "\n".join(md_content)


def save_to_file(content: str, filepath: str) -> bool:
    """
    Save content to a file.
    
    Args:
        content: Content to save
        filepath: Path to save the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Content saved to {filepath}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False


def process_html_file(html_file: str, output_file: str, source_url: str = "") -> bool:
    """
    Process an HTML file and convert to markdown.
    
    Args:
        html_file: Path to HTML file to process
        output_file: Path to save the markdown file
        source_url: Optional source URL for reference
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Reading HTML file: {html_file}...")
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("Converting to markdown...")
        markdown_content = convert_to_markdown(soup, source_url or html_file)
        
        print(f"Saving to {output_file}...")
        return save_to_file(markdown_content, output_file)
    except Exception as e:
        print(f"Error processing HTML file: {e}")
        return False


def scrape_and_save(url: str, output_file: str) -> bool:
    """
    Scrape a URL and save to file.
    
    Args:
        url: URL to scrape
        output_file: Path to save the markdown file
        
    Returns:
        True if successful, False otherwise
    """
    print(f"Fetching {url}...")
    
    soup = fetch_page(url)
    
    if not soup:
        print("Failed to fetch page")
        return False
    
    print("Converting to markdown...")
    markdown_content = convert_to_markdown(soup, url)
    
    print(f"Saving to {output_file}...")
    return save_to_file(markdown_content, output_file)


if __name__ == "__main__":
    import sys
    
    # Check if URL is provided as command line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "modules/module_b/c3d.md"
    else:
        # Default URL
        url = "https://www.autodesk.com/shortcuts/autocad"
        output_file = "modules/module_b/c3d.md"
    
    print(f"Scraping {url}...")
    print(f"Output file: {output_file}")
    print("-" * 50)
    
    if scrape_and_save(url, output_file):
        print("-" * 50)
        print(f"[SUCCESS] Scraping completed successfully! Content saved to: {output_file}")
    else:
        print("-" * 50)
        print("[FAILED] Scraping failed. Some websites block automated scraping.")