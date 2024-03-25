"""
This file is for web scraping the data from gathered websites and returnining plain text for processing
"""

# Environment Set Up
import requests
import re
from bs4 import BeautifulSoup, Comment

def fetch_website(url):
    """
    Fetch HTML from URLs found via search()

    Input: URL (gathered from the search function)
    Output: HTML
    """
    print("        Fetching text from url ...")

    # Try to fetch URL
    try: 
        response = requests.get(url)
        # If response code is not 200, inform user and move on
        if response.status_code != 200:
            raise Exception(f"Unable to fetch URL. Continuing.")
        html = response.text

        return html

    # Catch any other exception as unable to fetch and move on
    except Exception as e:
        print(f"Unable to fetch URL. Continuing.")
        return None
        
def extract_plain_text(html):
    """
    Extract plain text from HTML using BeautifulSoup

    Input: HTML (fetched from fetch_website)
    Output: Plain text
    """

    # parse html content of the website with beautiful soup
    soup = BeautifulSoup(html, 'html.parser')

    # extract plain text from html
    text = soup.get_text()
    
    # remove extra white space in the text using regex
    processed_text = re.sub('\s+', ' ', text)

    #cut the text to 10000 characters
    if len(processed_text) > 10000:
        print(f"        Trimming webpage content from {len(processed_text)} to 10000 characters")
        processed_text = processed_text[:10000]

    # Return processed plain text
    return processed_text