from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Tag
import requests


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, timeout=3)
    response.raise_for_status()
    return BeautifulSoup(response.text, features="lxml")


def get_first_url_from_tag(source_url: str, tag: Tag) -> Optional[str]:
    for hyperlink in tag.find_all("a"):
        if isinstance(hyperlink, Tag):
            href = hyperlink.get("href")
            if isinstance(href, (str, NavigableString)) and href:
                return urljoin(source_url, href)
    return None
