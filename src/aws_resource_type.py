from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Optional

from bs4 import BeautifulSoup
from bs4 import Tag
import yaml

from html_table import find_table
from html_table import iterate_spanless_table
from utils import get_first_url_from_tag

RE_TABLE_HEADER = re.compile(r"^Resource\stypes\sdefined\sby\s", re.IGNORECASE)
RE_EMPTY_TABLE = re.compile(r"\sdoes\snot\ssupport\sspecifying\sa\sresource\s", re.IGNORECASE)


# Fix typo's in AWS Documentation
SCRIPT_DIR = Path(__file__).resolve().parent
FIXED_ARN: dict[str, str] = yaml.safe_load(open(SCRIPT_DIR / ".." / "fixes" / "resource_type_arn.yml"))


@dataclass(frozen=True)
class AwsResourceType:
    arn: str
    condition_keys: set[str]
    url: Optional[str]

    @classmethod
    def from_row(cls, source_url: str, row: dict[str, Tag]) -> "AwsResourceType":
        arn = row["arn"].get_text().strip()
        if not arn:
            raise Exception("No ARN Template Found")
        arn = FIXED_ARN.get(arn, arn)

        condition_keys = set(line.strip() for line in row["condition_keys"].get_text().strip().splitlines())
        condition_keys.discard("")

        return cls(
            arn=arn,
            condition_keys=condition_keys,
            url=get_first_url_from_tag(source_url, row["resource_types"]),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "arn": self.arn,
            "conditionKeys": sorted(self.condition_keys),
            "url": self.url,
        }


def find_all_resource_types(source_url: str, soup: BeautifulSoup) -> dict[str, AwsResourceType]:
    table = find_table(soup, h2_pattern=RE_TABLE_HEADER, empty_table=RE_EMPTY_TABLE)
    if table is None:
        return {}

    output = {}
    rows = iterate_spanless_table(
        table,
        column_map={
            "Resource types": "resource_types",
            "ARN": "arn",
            "Condition keys": "condition_keys",
        },
    )
    for row in rows:
        name = row["resource_types"].get_text().strip()
        if not name:
            raise Exception("No Resource Type Found")
        if name in output:
            raise Exception("Duplicate Resource Type")

        output[name] = AwsResourceType.from_row(source_url, row)

    return output
