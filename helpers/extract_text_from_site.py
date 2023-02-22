"""
This module contains a single function, get_text_in_url, which is used to extract text from a website. The function takes in a single argument, a url, and returns the text on the webpage as a string. It uses the urlopen function from the urllib library to open the url, then uses the BeautifulSoup library to parse the HTML of the webpage. It removes all script and style elements from the HTML, then uses the .get_text() method from BeautifulSoup to extract the text from the webpage. The function then performs additional text cleaning operations such as removing leading and trailing whitespace, breaking multi-headlines into a line each, and dropping blank lines. The module also includes logging feature, which logs the information like fetching HTML, removing script and style elements and cleaning extracted text.
"""


from urllib.request import urlopen
from bs4 import BeautifulSoup
import argparse
import logging


logging.basicConfig(level=logging.INFO)


def get_text_in_url(url):
    """
    This function takes in a single argument, a url, and returns the text on the webpage as a string. It uses the urlopen function from the urllib library to open the url, then uses the BeautifulSoup library to parse the HTML of the webpage. It removes all script and style elements from the HTML, then uses the .get_text() method from BeautifulSoup to extract the text from the webpage. The function then performs additional text cleaning operations such as removing leading and trailing whitespace, breaking multi-headlines into a line each, and dropping blank lines.

    Args:
    url (str): The url of the webpage from which text will be extracted

    Returns:
    str : A string containing the cleaned text from the webpage
    """
    logging.info(f"Fetching HTML from {url}")
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    logging.info("Removing script and style elements from HTML")
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()  # rip it out

    # get text
    text = soup.get_text()

    logging.info("Cleaning extracted text")
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="extracts text from a website")

    parser.add_argument(
        "url", metavar="url", type=str, help="url of website to extract text"
    )

    args = parser.parse_args()

    result = get_text_in_url(url=args.url)
    print(result)
