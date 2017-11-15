FLAKE8?=flake8

.PHONY: lint
lint: lib/charms/layer/jujushell.py reactive/jujushell.py
	$(FLAKE8) $^
