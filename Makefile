.PHONY: setup flake8 mypy lint pytest pytest-log test

SRC := pytheus/
TEST := tests/

PYTEST := pytest --cov pytheus --cov-report term --cov-report html -v $(TEST)

setup:
	pip install .[redis,test]
	mypy --install-types --non-interactive $(SRC) $(TEST)

flake8:
	flake8 $(SRC) $(TEST)

mypy:
	mypy $(SRC) $(TEST)

lint: flake8 mypy

pytest:
	$(PYTEST)

pytest-log:
	$(PYTEST) -o log_cli=true -o log_cli_level=INFO

test: lint pytest