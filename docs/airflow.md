# Airflow (Astro CLI)

A pasta `airflow/` é um projeto Astro separado que reimplementa as duas ingestões como DAGs do Apache Airflow. As DAGs foram validadas localmente de ponta a ponta com `astro dev start`, com scheduler real e dados reais.

Em produção quem rodou a coleta foi o GitHub Actions (`.github/workflows/podcasts-ingest.yml`). Fiz o Airflow pra aprender a ferramenta, e colocar no ar exigiria pagar (o Astro Cloud não tem plano gratuito permanente), o que não faz sentido pra um projeto de portfólio. Então ele fica como implementação alternativa, validada localmente.

## As DAGs

- `podcasts_ingest_dbt` faz ingestão no Turso, espelha o Turso pra SQLite local, roda `dbt run` e `dbt test`. Não tem o passo `push_marts_to_turso.py` do workflow. O schedule era `0 6 * * *` e hoje é `schedule=None`, porque a coleta foi encerrada.
- `copa2026_ingest_dbt` faz a coleta única da Copa e roda o dbt. `schedule=None`, disparo manual pela UI.

## Como subir

```bash
cd airflow
./sync_repo_code.sh   # espelha src/, copa2026/ e dbt/ pra airflow/include/repo/
astro dev start       # precisa do Astro CLI e de Docker ou podman
```

O `astro dev` só enxerga arquivos dentro de `airflow/`, que é o build context do projeto. O `sync_repo_code.sh` copia o código da raiz pra `airflow/include/repo/` (gerado e fora do git) e precisa rodar antes de `astro dev start` ou `astro dev parse`.

## Detalhes da imagem

- Runtime fixo em `astrocrpublic.azurecr.io/runtime:3.1-1`, que vem com Python 3.12. O `dbt-sqlite` quebra no 3.14.
- O `airflow/Dockerfile` copia `include/repo/` pra `/usr/local/airflow/repo`, fora de `include/`. Em modo dev o `include/` vira bind mount (virtiofs, dentro da VM do podman) e ignora `chmod`, então as tasks davam `PermissionError` ao criar `data/` e `logs/` ali.
- Uma venv por projeto dbt, construída em build-time (`dbt_venvs/podcasts` e `dbt_venvs/copa2026`), isolada do ambiente do Airflow e uma da outra. É o mesmo conflito de versões descrito em [dbt.md](dbt.md).
- As tasks dbt rodam com `cwd` na pasta do projeto, porque o `profiles.yml` resolve o caminho do banco contra o diretório do processo e não contra `--project-dir`.
- As tasks dos podcasts passam dado por arquivo local (`data/youtube.db`). Funciona porque o `astro dev start` roda tudo num container só. Com vários workers isso não seria garantido.

## Por que não usei o astronomer-cosmos

Testei o cosmos pra rodar o dbt e achei um import circular determinístico dessa versão com o Airflow 3.1. Um `import airflow` sozinho já quebrava, porque o cosmos se registra como plugin do Airflow via entrypoint. Descartei e fiquei com `BashOperator` chamando o binário de cada venv.
