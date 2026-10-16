PYTHON ?= python3

.PHONY: build install check

build:
	$(PYTHON) scripts/build.py

install: build
	$(PYTHON) scripts/install.py

check: build
	$(PYTHON) -m unittest discover -s tests -v
	git diff --check
