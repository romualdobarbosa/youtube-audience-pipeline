.PHONY: all install lint test dashboard

all: lint test

install:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest

dashboard:
	uv run streamlit run src/dashboard.py
