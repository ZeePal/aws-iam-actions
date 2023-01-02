import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Tag

from aws_action import AwsAction
from aws_action import find_all_actions
from aws_condition_key import AwsConditionKey
from aws_condition_key import find_all_condition_keys
from aws_resource_type import AwsResourceType
from aws_resource_type import find_all_resource_types
from utils import get_soup

URL = "https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html"  # noqa
RE_SERVICE_PREFIX = re.compile(r"\s\(service\s+prefix\b", re.IGNORECASE)


class AwsService:
    def __init__(self, name: str, url: str):
        self.name: str = name
        self.url: str = url

    def fetch(self) -> None:
        soup = get_soup(self.url)
        self.prefix: str = self._extract_prefix(soup)

        self.actions: dict[str, AwsAction] = find_all_actions(self.url, soup)
        self.resource_types: dict[str, AwsResourceType] = find_all_resource_types(self.url, soup)
        self.condition_keys: dict[str, AwsConditionKey] = find_all_condition_keys(self.url, soup)

    def _extract_prefix(self, soup: BeautifulSoup) -> str:
        # Searching for:
        # <p>
        # Identity And Access Management (service prefix: <code class="code">iam</code>) provides the following
        # service-specific resources, actions, and condition context keys for use in IAM permission
        # policies.
        # </p>
        texts = soup.find_all(string=RE_SERVICE_PREFIX)
        if len(texts) != 1:
            raise Exception(f"Unable to locate the Services Description: {self.url}")
        if not isinstance(texts[0], NavigableString):
            raise Exception(f"Unknown Service Description: {texts[0]}")

        prefix_code = texts[0].next_element
        if not isinstance(prefix_code, Tag):
            raise Exception(f"Unknown Service Prefix Code: {prefix_code}")
        if prefix_code.name.lower() != "code":
            raise Exception(f"Unknown Service Prefix Code type: {prefix_code}")
        if len(prefix_code.contents) != 1:
            raise Exception(f"Unknown Service Prefix Contents: {prefix_code}")
        if not isinstance(prefix_code.contents[0], NavigableString):
            raise Exception(f"Unknown Service Prefix Content: {prefix_code}")

        prefix = str(prefix_code.contents[0]).strip()
        if not prefix:
            raise Exception(f"Unable to locate Service Prefix: {prefix_code}")

        return prefix

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "prefix": self.prefix,
            "url": self.url,
            "actions": {key: value.to_json_dict() for key, value in sorted(self.actions.items())},
            "resourceTypes": {key: value.to_json_dict() for key, value in sorted(self.resource_types.items())},
            "conditionKeys": {key: value.to_json_dict() for key, value in sorted(self.condition_keys.items())},
        }


def find_all_aws_services() -> list[AwsService]:
    soup = get_soup(URL)
    # Searching for:
    # <p><strong>Topics</strong></p>
    # <ul>
    # <li><a href="./list_awsaccountmanagement.html">AWS Account Management</a></li>
    # <li><a href="./list_awsactivate.html">AWS Activate</a></li>
    # SNIP
    # </ul>

    headers = soup.find_all("p", string="Topics")
    if len(headers) != 1:
        raise Exception(f"Unable to locate the Topics Header: {URL}")

    lists = headers[0].find_next_siblings("ul")
    if len(lists) != 1:
        raise Exception(f"Unable to locate the Topics List: {URL}")

    output = []
    for item in lists[0].find_all("li"):
        text, href = _extract_hyperlink(item)
        output.append(AwsService(text, urljoin(URL, href)))

    if not output:
        raise Exception(f"Unable to find any AWS Services: {URL}")
    return output


def _extract_hyperlink(item: Tag) -> tuple[str, str]:
    if len(item.contents) != 1:
        raise Exception(f"Unknown Topics Item: {item}")

    hyperlink = item.find("a")
    if not isinstance(hyperlink, Tag):
        raise Exception(f"Unable to locate hyperlink in Topics Item: {item}")

    if len(hyperlink.contents) != 1:
        raise Exception(f"Unknown Topics Hyperlink: {hyperlink}")
    if not isinstance(hyperlink.contents[0], NavigableString):
        raise Exception(f"Unknown Topics Hyperlink Content: {hyperlink}")

    text = str(hyperlink.contents[0]).strip()
    if not text:
        raise Exception(f"Unable to locate Topics Hyperlink Text: {hyperlink}")

    href = hyperlink.get("href")
    if not isinstance(href, (str, NavigableString)) or not href:
        raise Exception(f"Unable to locate href in Topics Hyperlink: {hyperlink}")

    return text, href
