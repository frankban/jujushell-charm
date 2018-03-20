DEBDEPS=python3-virtualenv
SNAPDEPS=charm
VENVDEPS=charmhelpers charms.reactive coverage flake8 pylxd pyyaml

VENV=.venv
BIN=$(VENV)/bin
PYTHON=$(BIN)/python

all: devenv

$(PYTHON):
	virtualenv -p python3 $(VENV)
	$(BIN)/pip install $(VENVDEPS)

.PHONY: build
build: clean
	/snap/bin/charm build

.PHONY: check
check: lint test

.PHONY: clean
clean:
	-rm -rf $(VENV)
	-rm -rf builds
	-rm -rf deps

.PHONY: devenv
devenv: $(PYTHON)

.PHONY: lint
lint: $(PYTHON)
	@$(BIN)/flake8 actions/* hooks/collect-metrics lib/charms/layer/*.py reactive/*.py tests/*.py

.PHONY: test
test: $(PYTHON)
	@$(BIN)/coverage run --source jujushell -m unittest discover -v -s tests/
	@$(BIN)/coverage report -m
	@rm .coverage

.PHONY: sysdeps
sysdeps:
	sudo apt install -y $(DEBDEPS)
	sudo snap install $(SNAPDEPS)
