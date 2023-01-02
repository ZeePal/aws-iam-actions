from dataclasses import dataclass
import re
from typing import Any, Iterator, Optional

from bs4 import BeautifulSoup
from bs4 import Tag

from html_table import find_table
from html_table import get_spanless_table_header
from utils import get_first_url_from_tag

RE_TABLE_HEADER = re.compile(r"^Actions\sdefined\sby\s", re.IGNORECASE)
RE_PERMISSION_ONLY = re.compile(r"^(\S+)\s*\[permission\s+only\]\s*$")
RE_DESCRIPTION_SCENARIO = re.compile(r"^SCENARIO:", re.IGNORECASE)


@dataclass(frozen=True)
class AwsActionResourceType:
    required: Optional[bool]
    condition_keys: set[str]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "conditionKeys": sorted(self.condition_keys),
        }


@dataclass(frozen=True)
class AwsAction:
    description: str
    access_level: str
    permission_only: bool
    resource_types: dict[str, AwsActionResourceType]
    condition_keys: set[str]
    dependent_actions: set[str]
    url: Optional[str]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "accessLevel": self.access_level,
            "permissionOnly": self.permission_only,
            "resourceTypes": {key: value.to_json_dict() for key, value in sorted(self.resource_types.items())},
            "conditionKeys": sorted(self.condition_keys),
            "dependentActions": sorted(self.dependent_actions),
            "url": self.url,
        }


def find_all_actions(source_url: str, soup: BeautifulSoup) -> dict[str, AwsAction]:
    table = find_table(soup, h2_pattern=RE_TABLE_HEADER, ignore_attributes={"rowspan"})
    if not table:
        raise Exception(f"Unable to locate the Actions Table: {table}")

    table_header = get_spanless_table_header(
        table,
        expected_columns=[
            "Actions",
            "Description",
            "Access level",
            "Resource types (*required)",
            "Condition keys",
            "Dependent actions",
        ],
    )

    rows = table_header.find_next_siblings("tr")
    iter_rows = iter(rows)  # manually creating iterator so spanned rows can be next()'d

    output = {}
    for row in iter_rows:
        if not isinstance(row, Tag):
            raise Exception(f"Unknown Table Row: {row}")

        name, action = _extract_action(source_url, row, iter_rows)
        if name in output:
            raise Exception("Duplicate Action")
        output[name] = action
    return output


def _extract_action(source_url: str, top_row: Tag, iter_rows: Iterator[Any]) -> tuple[str, AwsAction]:
    action_name, permission_only, url, row_span, rows = _extract_action_init(top_row, iter_rows, source_url)
    try:
        columns = _action_rows_to_columns(row_span, rows)

        description = _extract_action_description(columns[1])
        access_level = _extract_action_access_level(columns[2])

        resource_types, condition_keys = _extract_action_resource_types_with_conditions(columns[3], columns[4])

        dependent_actions = _extract_action_dependent_actions(columns[5])
    except Exception as ex:
        raise Exception(f"Exception during Action: {action_name}") from ex

    return action_name, AwsAction(
        description=description,
        access_level=access_level,
        permission_only=permission_only,
        resource_types=resource_types,
        condition_keys=condition_keys,
        dependent_actions=dependent_actions,
        url=url,
    )


def _extract_action_init(
    top_row: Tag, iter_rows: Iterator[Any], source_url: str
) -> tuple[str, bool, str, int, list[list[Tag]]]:
    top_cells = []
    for cell in top_row.find_all("td"):
        if not isinstance(cell, Tag):
            raise Exception(f"Unknown Table Cell: {cell}")
        top_cells.append(cell)

    action_cell = top_cells[0]
    action_name = action_cell.get_text().strip()
    permission_only = False
    if match := RE_PERMISSION_ONLY.match(action_name):
        action_name = match.group(1)
        permission_only = True
    if not action_name:
        raise Exception(f"Unable to locate the Action Name: {action_cell} ({action_name})")

    row_span = int(action_cell.get("rowspan", 1))
    if row_span < 1:
        raise NotImplementedError("Unsupported full table spanning")

    rows = [top_cells]
    for _ in range(row_span - 1):
        extra_row = []
        x = next(iter_rows)
        if not isinstance(x, Tag):
            raise Exception(f"Unknown Table Row: {x}")
        for cell in x.find_all("td"):
            if not isinstance(cell, Tag):
                raise Exception(f"Unknown Table Cell: {cell}")
            extra_row.append(cell)
        rows.append(extra_row)

    url = get_first_url_from_tag(source_url, action_cell)
    return action_name, permission_only, url, row_span, rows


def _action_rows_to_columns(action_span: int, rows: list[list[Tag]]) -> list[list[Tag]]:
    columns = [[i] for i in rows[0]]  # seed with all cells in top row
    for column in columns:
        top_cell = column[0]
        top_row_span = int(top_cell.get("rowspan", 1))
        if top_row_span < 1:
            raise NotImplementedError("Unsupported full table spanning")
        elif top_row_span > action_span:
            raise Exception("Action Cells spanning past their own action")

        next_row_index = top_row_span
        while next_row_index != action_span:
            row = rows[next_row_index]
            cell = row.pop(0)
            column.append(cell)

            row_span = int(cell.get("rowspan", 1))
            if row_span < 1:
                raise NotImplementedError("Unsupported full table spanning")
            next_row_index += row_span
            if row_span > action_span:
                raise Exception("Action Cells spanning past their own action")

    return columns


def _extract_action_description(column: list[Tag]) -> str:
    description = None
    for cell in column:
        text = cell.get_text().strip()
        if description is None:  # top cell is the description
            description = text
            continue

        if not text:  # extra cell thats empty
            continue

        if RE_DESCRIPTION_SCENARIO.match(text):  # extra cell for "scenarios" which we will ignore
            continue

        raise Exception(f"Extra Description found: {text}")

    if not description:
        raise Exception(f"Unable to locate the Action Description: {column}")
    return description


def _extract_action_access_level(column: list[Tag]) -> str:
    access_level = None
    for cell in column:
        text = cell.get_text().strip()
        if access_level is None:  # top cell is the description
            access_level = text
            continue

        if not text:  # extra cell thats empty
            continue

        if text != access_level:  # extra cell that repeats the same access_level which we will ignore
            continue

        raise Exception(f"Extra Access Level found: {text}")

    if not access_level:
        raise Exception(f"Unable to locate the Action Access Level: {column}")
    return access_level


def _extract_action_resource_types_with_conditions(
    column_resource_types: list[Tag], column_condition_keys: list[Tag]
) -> tuple[dict[str, AwsActionResourceType], set[str]]:
    if len(column_resource_types) != len(column_condition_keys):
        raise Exception(
            f"Mismatching resource types & condition keys counts: {len(column_resource_types)} vs {len(column_condition_keys)}"
        )

    action_condition_keys = set()
    action_resource_types = {}
    for i in range(len(column_resource_types)):
        condition_keys = {line.strip() for line in column_condition_keys[i].get_text().strip().splitlines()}
        condition_keys.discard("")

        resource_types = {line.strip() for line in column_resource_types[i].get_text().strip().splitlines()}
        resource_types.discard("")
        if not resource_types:
            # empty resource types cell, so the matching condition keys are action specific
            action_condition_keys.update(condition_keys)
            continue

        for resource_type in resource_types:
            required = False
            if resource_type[-1] == "*":
                required = True
                resource_type = resource_type[:-1]

            if resource_type not in action_resource_types:
                # first time seeing this resource type for this action
                action_resource_types[resource_type] = AwsActionResourceType(
                    required=required,
                    condition_keys=condition_keys,
                )
                continue

            action_resource_type = action_resource_types[resource_type]
            if required != action_resource_type.required:
                # some resource types appear multiple times but change their required status
                # marking required as None/null as its then a conditional requirement
                required = None

            action_resource_types[resource_type] = AwsActionResourceType(
                required=required,
                condition_keys=action_resource_type.condition_keys | condition_keys,
            )

    return action_resource_types, action_condition_keys


def _extract_action_dependent_actions(column: list[Tag]) -> set[str]:
    dependent_actions = None
    for cell in column:
        lines = {line.strip() for line in cell.get_text().strip().splitlines()}
        lines.discard("")
        if dependent_actions is None:  # top cell is the description
            dependent_actions = lines
            continue

        if not lines:  # extra cell thats empty
            continue

        raise Exception(f"Extra Dependent Actions found: {lines}")

    if dependent_actions is None:
        raise Exception(f"Unable to locate the Action Dependent Actions: {column}")
    return dependent_actions
