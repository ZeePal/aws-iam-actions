from dataclasses import dataclass
import re
from typing import Any, Optional

from bs4 import BeautifulSoup
from bs4 import Tag

from html_table import find_table
from html_table import iterate_spanless_table
from utils import get_first_url_from_tag

RE_TABLE_HEADER = re.compile(r"^Condition\skeys\sfor\s", re.IGNORECASE)
RE_EMPTY_TABLE = re.compile(r"\shas\sno\sservice-specific\scontext\skeys\s", re.IGNORECASE)


@dataclass(frozen=True)
class AwsConditionKey:
    description: str
    type: str
    url: Optional[str]

    @classmethod
    def from_row(cls, source_url: str, row: dict[str, Tag]) -> "AwsConditionKey":
        description = row["description"].get_text().strip()
        if not description:
            raise Exception("No Description Found")

        type_ = row["type"].get_text().strip()
        if not type_:
            raise Exception("No Type Found")

        return cls(
            description=description,
            type=type_,
            url=get_first_url_from_tag(source_url, row["condition_keys"]),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "type": self.type,
            "url": self.url,
        }


def find_all_condition_keys(source_url: str, soup: BeautifulSoup) -> dict[str, AwsConditionKey]:
    table = find_table(soup, h2_pattern=RE_TABLE_HEADER, empty_table=RE_EMPTY_TABLE)
    if table is None:
        return {}

    output = {}
    rows = iterate_spanless_table(
        table,
        column_map={
            "Condition keys": "condition_keys",
            "Description": "description",
            "Type": "type",
        },
    )
    for row in rows:
        name = row["condition_keys"].get_text().strip()
        if not name:
            raise Exception("No Condition Key Found")
        if name in output:
            raise Exception("Duplicate Condition Key")

        output[name] = AwsConditionKey.from_row(source_url, row)

    return output
