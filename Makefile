# Makefile for Project Automation

.PHONY: install format lint type-check test coverage clean run dev-server

# Variables
PACKAGE_NAME = app
TEST_DIR = tests
PYTHON = poetry run python
PYTEST = poetry run pytest
COVERAGE = poetry run coverage
BLACK = poetry run black
ISORT = poetry run isort
RUFF = poetry run ruff
MYPY = poetry run mypy

# Install project dependencies
install:
	poetry install

# Format code
format:
	$(BLACK) $(PACKAGE_NAME) $(TEST_DIR)
	$(ISORT) $(PACKAGE_NAME) $(TEST_DIR)

# Linting
lint:
# $(RUFF) check $(PACKAGE_NAME) $(TEST_DIR)
	$(BLACK) --check $(PACKAGE_NAME) $(TEST_DIR)
	$(ISORT) --check-only $(PACKAGE_NAME) $(TEST_DIR)

# Type checking
# type-check:
# 	$(MYPY) $(PACKAGE_NAME)

# Run tests
test:
	$(PYTEST) $(TEST_DIR) -v

# Run tests with coverage
coverage:
	$(PYTEST) --cov=$(PACKAGE_NAME) --cov-report=xml --cov-report=html $(TEST_DIR)

# Run development server
dev-server:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Clean up
clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf coverage.xml
	rm -rf dist
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Run all checks
check: format lint type-check test
