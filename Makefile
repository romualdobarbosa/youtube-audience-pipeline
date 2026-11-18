.PHONY: all install lint test dashboard dbt-copa

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

# dbt build da Copa numa cópia do .duckdb em target/ (gitignored): o build regrava
# os marts, e o arquivo versionado em data/ tem que ficar intacto.
dbt-copa:
	mkdir -p copa2026/dbt/target/ci
	cp data/copa2026.duckdb copa2026/dbt/target/ci/copa2026.duckdb
	cd copa2026/dbt && COPA_DUCKDB_PATH=target/ci/copa2026.duckdb \
		uv run --group dbt-copa dbt build --profiles-dir .
