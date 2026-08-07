from bs4 import BeautifulSoup
from urllib.parse import urljoin


def extract_links(html: str, base_url: str):
    """
    Extract all links from a webpage.
    Returns a list of dictionaries:
        {
            "text": "...",
            "url": "..."
        }
    """

    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):

        text = a.get_text(" ", strip=True)

        href = urljoin(base_url, a["href"])

        links.append(
            {
                "text": text,
                "url": href
            }
        )

    return links