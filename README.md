# AWS IAM Actions Database
Scrapping [AWS Documentation](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html) for all IAM Actions for offline querying.


## Usage
### Download/Update
```shell
make clean download  # ~3 min
```

### JQ Examples
```shell
# All IAM Actions starting with "Get"
jq -r '.actions |to_entries[] |select(.key|startswith("Get")) |.key' ./data/iam/*.json

# All IAM Actions that support Condition Key "iam:PermissionsBoundary"
jq -r '.actions |to_entries[] |select(.value.conditionKeys|index("iam:PermissionsBoundary")) |.key' ./data/iam/*.json

# All IAM Actions that aren't "Read" or "List"
jq -r '.actions |to_entries[] |select(.value.accessLevel != "Read" and .value.accessLevel != "List") |.key' ./data/iam/*.json
```


## TODO
- dockerize
- add argparse to:
  - choose save location
  - filter by service name
  - remove data files not updated in all pass
- parallelize
- more comments
- clean/polish code
