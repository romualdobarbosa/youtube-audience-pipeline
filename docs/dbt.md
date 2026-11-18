# Os dois projetos dbt

O repo tem dois projetos dbt separados, um por análise.

| Projeto | Pasta | Adapter | Grupo uv |
| --- | --- | --- | --- |
| Copa 2026 | `copa2026/dbt/` | `dbt-duckdb` | `dbt-copa` |
| Podcasts BR | `dbt/` | `dbt-sqlite` | `dbt-podcasts` |

## Por que dois grupos em conflito

Os dois adapters pedem versões de `dbt-core` incompatíveis entre si, então as dependências de cada um ficam num grupo próprio do `pyproject.toml`, declarados em `[tool.uv] conflicts`.

- `dbt-sqlite` não acompanha os releases recentes de `dbt-core` e `dbt-adapters`. Juntar tudo na última versão quebra o import do adapter. A combinação que eu testei com `dbt run` e `dbt test` de verdade é `dbt-core==1.11.14`, `dbt-adapters==1.16.7` e `dbt-sqlite==1.10.0`. Ela precisa de Python 3.11 ou 3.12, porque o `dbt-common` (via `mashumaro`) quebra no 3.14.
- `dbt-duckdb` acompanha o `dbt-core` bem mais de perto (`dbt-core==1.12.3`, `dbt-adapters==1.24.5`, `dbt-duckdb==1.11.0`).

Nenhum dos dois grupos entra na imagem do `Dockerfile`. Os serviços `dbt` e `copa-dbt` do `docker-compose.yml` sincronizam o próprio grupo na hora de rodar. No Airflow o mesmo conflito se resolve com uma venv por projeto (ver [airflow.md](airflow.md)).

## Como rodar

Sempre de dentro da pasta do projeto e com `--profiles-dir .`. Os `profiles.yml` são versionados porque só guardam caminho de arquivo, e esse caminho é relativo ao diretório de onde o dbt roda.

```bash
# Copa 2026, contra data/copa2026.duckdb
cd copa2026/dbt && uv run --group dbt-copa dbt build --profiles-dir .

# Podcasts, contra data/youtube.db (gerado pela ingestão ou pelo sync_replica.py)
cd dbt && uv run --group dbt-podcasts dbt build --profiles-dir .
```

Pra testar sem os bancos reais existe o `make dbt-test`.

- `make dbt-copa` copia o `.duckdb` versionado pra `copa2026/dbt/target/ci/` e roda `dbt build` na cópia, assim o arquivo em `data/` fica intacto.
- `make dbt-podcasts` gera uma fixture SQLite sintética (`tests/fixtures/make_podcasts_fixture.py`) e roda `dbt build` nela. Depois gera uma fixture quebrada, com duas versões vigentes pra mesma chave, e confere que os testes `assert_single_current_channel` e `assert_single_current_video` falham nela.

Cada fixture fica numa pasta própria porque o `dbt-sqlite` anexa todo `.db` que achar no `schema_directory`.

## Modelos

Copa 2026: `stg_copa_videos` classifica cada vídeo numa janela (as datas ficam em `vars` no `copa2026/dbt/dbt_project.yml`), e os marts `channel_window_metrics` e `channel_window_comparison` agregam por canal e janela.

Podcasts: quatro modelos de staging em cima das dimensões SCD2 e dos fatos de snapshot, e seis marts (`channel_ranking`, `short_vs_long`, `upload_cadence`, `channel_growth`, `video_growth`, `latest_video_metrics`). O DDL de referência do modelo dimensional está em [esquema.sql](esquema.sql).
