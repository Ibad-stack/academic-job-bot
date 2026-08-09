from bs4 import BeautifulSoup
from urllib.parse import urljoin


def extract_links(html: str, base_url: str):
    """
    Extract navigational links from a webpage.

    Iframes are included because several university career pages embed their
    live job board rather than exposing postings as normal anchors.
    """

    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = urljoin(base_url, a["href"])
        links.append({
            "text": text,
            "url": href,
            "type": "anchor",
        })

    for iframe in soup.find_all("iframe", src=True):
        href = urljoin(base_url, iframe["src"])
        links.append({
            "text": "Embedded career/job board",
            "url": href,
            "type": "iframe",
        })

    return links
