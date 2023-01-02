from re import Pattern
import sys
from typing import Iterator, Optional

from bs4 import BeautifulSoup
from bs4 import Tag

assert sys.version_info >= (3, 7)  # Depending on "Dictionary order is guaranteed to be insertion order."

UNSUPPORTED_TABLE_TAGS = {
    "caption",
    "col",
    "colgroup",
    "tbody",  # currently no tbody's in use just 1 thead
    "tfoot",
}
SUPPORTED_TABLE_TAGS = {"thead", "tr", "th", "td"}
UNSUPPORTED_ATTRIBUTES = {"span", "colspan", "rowspan", "headers", "scope"}


def find_table(
    soup: BeautifulSoup,
    h2_pattern: Pattern[str],
    empty_table: Optional[Pattern[str]] = None,
    ignore_attributes: Optional[set[str]] = None,
) -> Optional[Tag]:
    # Locate the header just above the table
    html_headers = soup.find_all("h2", string=h2_pattern)
    if len(html_headers) != 1:
        raise Exception("Unable to locate the H2 Header before the Table")

    if empty_table is not None:
        # This table doesn't always exist, check that the text under the header says that
        description = html_headers[0].find_next("p")
        if not description:
            raise Exception("Unable to locate the Description before the Table")

        if empty_table.search(description.get_text()):
            return None

    # Grab the first table under the located header
    table = html_headers[0].find_next("table")
    if not isinstance(table, Tag):
        raise Exception(f"Unable to locate the Table: {table}")

    # Make sure the table doesn't contain unsupported table tags
    bad_tags = table.find_all(UNSUPPORTED_TABLE_TAGS)
    if bad_tags:
        raise Exception(f"Found Table contains bad html tags: {bad_tags}")

    # Make sure the supported table tags dont contain unsupported attributes
    bad_attributes = UNSUPPORTED_ATTRIBUTES
    if ignore_attributes:
        bad_attributes = UNSUPPORTED_ATTRIBUTES - ignore_attributes
    for tag in table.find_all(SUPPORTED_TABLE_TAGS):
        if tag.attrs.keys() & bad_attributes:
            raise NotImplementedError(f"Found Table contains tags with bad attributes: {tag}")

    return table


def iterate_spanless_table(table: Tag, column_map: dict[str, str]) -> Iterator[dict[str, Tag]]:
    table_header = get_spanless_table_header(table, list(column_map.keys()))
    columns_by_index = list(column_map.values())

    for row in table_header.find_next_siblings("tr"):
        if not isinstance(row, Tag):
            raise Exception(f"Unknown Table Row: {row}")

        output = {}
        for i, cell in enumerate(row.find_all("td")):
            if not isinstance(cell, Tag):
                raise Exception(f"Unknown Table Cell: {cell}")

            column = columns_by_index[i]
            if column in output:
                raise Exception(f"Already processed this column?: {column}")

            output[column] = cell
        yield output


def get_spanless_table_header(table: Tag, expected_columns: list[str]) -> Tag:
    # Locate the tables header row(s)
    heads = table.find_all("thead")
    if len(heads) != 1:
        raise Exception("Unable to locate the Table Header")
    head = heads[0]
    if not isinstance(head, Tag):
        raise Exception(f"Unknown Table Header: {head}")

    # Locate the cells in the header
    columns = head.find_all(["th", "td"])
    if len(columns) != len(expected_columns):
        raise Exception(f"Bad Table Column count: {len(columns)} (expected {len(expected_columns)})")

    # Make sure the found column cells match the expected columns
    for i, expected_column in enumerate(expected_columns):
        if not isinstance(columns[i], Tag):
            raise Exception(f"Unknown Table Column: {columns[i]}")

        if columns[i].attrs.keys() & UNSUPPORTED_ATTRIBUTES:
            raise NotImplementedError(f"Found Table Column with bad attributes: {columns[i]}")

        column = columns[i].get_text().strip()
        if column != expected_column:
            raise Exception(f"Unexpected Table Column: {column} (expected {expected_column})")

    return head
