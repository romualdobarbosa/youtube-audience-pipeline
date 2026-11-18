.PHONY: all install lint test dashboard dbt-copa dbt-podcasts

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

# dbt build dos podcasts contra uma fixture SQLite sintética (tests/fixtures/), sem
# data/youtube.db nem Turso. Depois gera uma fixture com duas versões vigentes pra
# mesma chave e confere que os testes de invariante SCD2 falham nela.
# Cada fixture em pasta própria: o dbt-sqlite anexa todo .db do schema_directory.
PODCASTS_FIXTURE := dbt/target/ci/ok/podcasts.db
PODCASTS_BROKEN := dbt/target/ci/broken/podcasts.db

dbt-podcasts:
	uv run --group dbt-podcasts python -m tests.fixtures.make_podcasts_fixture $(PODCASTS_FIXTURE)
	cd dbt && PODCASTS_SQLITE_PATH=../$(PODCASTS_FIXTURE) PODCASTS_SCHEMA_DIR=target/ci/ok \
		uv run --group dbt-podcasts dbt build --profiles-dir .
	uv run --group dbt-podcasts python -m tests.fixtures.make_podcasts_fixture --broken $(PODCASTS_BROKEN)
	cd dbt && ! PODCASTS_SQLITE_PATH=../$(PODCASTS_BROKEN) PODCASTS_SCHEMA_DIR=target/ci/broken \
		uv run --group dbt-podcasts dbt test --profiles-dir . \
		--select assert_single_current_channel assert_single_current_video \
		> target/ci/broken/dbt_test.log
	grep -q "FAIL 1 assert_single_current_channel" dbt/target/ci/broken/dbt_test.log
	grep -q "FAIL 1 assert_single_current_video" dbt/target/ci/broken/dbt_test.log
	@echo "ok: invariante SCD2 pegou a fixture quebrada"
