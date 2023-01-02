.PHONY: download
download:
	mkdir -p ./data/
	src/download_all_iam_actions

.PHONY: clean
clean:
	rm -rf ./data/
