import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from aws_service import AwsService

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / ".." / "schema.json"

# AWS Documentation missing entries in the condition keys table for some condition key(s)
MISSING_CONDITION_KEYS: dict[str, set[str]] = yaml.safe_load(
    open(SCRIPT_DIR / ".." / "fixes" / "missing_condition_keys.yml")
)

CACHED_JSONSCHEMA = None

# Check that the output dict is in the correct formate
def check_json_schema(json_dict: dict[str, Any]) -> None:
    if not CACHED_JSONSCHEMA:
        _load_json_schema()

    jsonschema.validate(instance=json_dict, schema=CACHED_JSONSCHEMA)


def _load_json_schema():
    global CACHED_JSONSCHEMA
    with open(SCHEMA_PATH, "r") as file:
        CACHED_JSONSCHEMA = json.load(file)


# Check that all references to dependent actions exist in at least 1 of the AWS Services
def check_all_dependent_actions_exist(all_actions: set[str], aws_service: AwsService) -> None:
    for action_name, action in aws_service.actions.items():
        missing_actions = action.dependent_actions - all_actions
        if missing_actions:
            raise Exception(f"Missing Dependent Actions for Action {action_name}: {missing_actions}")


# Check that all the same service references (condition keys & resource types) mentioned in each table exists in the respective table
def check_all_self_references(aws_service: AwsService) -> None:
    _check_action_resource_type_self_references(aws_service)
    _check_action_resource_type_condition_keys_self_references(aws_service)
    _check_action_condition_key_self_references(aws_service)
    _check_resource_type_condition_key_self_references(aws_service)


# Check all Resource Types mentioned in the Actions table exist in the Resource Types table
def _check_action_resource_type_self_references(aws_service: AwsService) -> None:
    for action_name, action in aws_service.actions.items():
        missing_resource_types = action.resource_types.keys() - aws_service.resource_types.keys()
        if missing_resource_types:
            raise Exception(f"Missing Resource Types for Action {action_name}: {missing_resource_types}")


# Check all Condition Keys mentioned for a Resource Type in the Actions table exist in the Condition Keys table
def _check_action_resource_type_condition_keys_self_references(aws_service: AwsService) -> None:
    for action_name, action in aws_service.actions.items():
        for resource_type_name, resource_type in action.resource_types.items():
            missing_condition_keys = (
                resource_type.condition_keys
                - aws_service.condition_keys.keys()
                - MISSING_CONDITION_KEYS.get(aws_service.prefix, set())
            )
            if missing_condition_keys:
                raise Exception(
                    f"Missing Condition Keys for Action {action_name} for Resource {resource_type_name}: {missing_condition_keys}"
                )


# Check all Condition Keys for an Action in the Actions table exist in the Condition Keys table
def _check_action_condition_key_self_references(aws_service: AwsService) -> None:
    for action_name, action in aws_service.actions.items():
        missing_condition_keys = (
            action.condition_keys
            - aws_service.condition_keys.keys()
            - MISSING_CONDITION_KEYS.get(aws_service.prefix, set())
        )
        if missing_condition_keys:
            raise Exception(f"Missing Condition Keys for Action {action_name}: {missing_condition_keys}")


# Check all Condition Keys for a Resource Type in the Resource Types table exist in the Condition Keys table
def _check_resource_type_condition_key_self_references(aws_service: AwsService) -> None:
    for resource_type_name, resource_type in aws_service.resource_types.items():
        missing_condition_keys = resource_type.condition_keys - aws_service.condition_keys.keys()
        if missing_condition_keys:
            raise Exception(f"Missing Condition Keys for Resource Type {resource_type_name}: {missing_condition_keys}")
