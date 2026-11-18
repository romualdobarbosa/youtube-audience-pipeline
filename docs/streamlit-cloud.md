# Deploy no Streamlit Community Cloud

O app publicado fica em https://youtubeviewcounter.streamlit.app/ e é deployado a partir da branch `main` deste repo.

## Configuração do app

- Main file path: `src/dashboard.py`
- Python version (Advanced settings): `3.11`, a mesma do `Dockerfile` e dos workflows do GitHub Actions.
- Dependências. O Streamlit Cloud procura o arquivo de dependências primeiro na pasta do main file e só depois na raiz. Por isso existe `src/requirements.txt`, gerado do `uv.lock` (só o runtime) pelo hook `uv-export` do pre-commit. Não edite à mão.

## Secrets

No painel do app, fora do repo:

```toml
DB_BACKEND = "turso"
TURSO_DATABASE_URL = "libsql://..."
TURSO_AUTH_TOKEN = "..."
```

São as mesmas credenciais do workflow `.github/workflows/podcasts-ingest.yml`, pra página Podcasts BR ler do mesmo banco que o Actions alimentava. A ingestão foi encerrada em 28/09/2026, então a página mostra o último snapshot dessa data.

## Página da Copa 2026

Não depende de secret. Ela lê `data/copa2026.duckdb`, que é commitado no repo (exceção deliberada ao `*.duckdb` do `.gitignore`). Como as janelas da análise estão no passado, não tem reingestão automática. Pra atualizar, rode `python -m copa2026.ingest` e o dbt localmente e commite o `.duckdb` de novo (motivo em [ADR 0001](adr/0001-duckdb-vs-turso.md)).

## App dormindo

Apps do Community Cloud dormem depois de um tempo sem acesso. Quem abre o link nessa hora vê uma tela pra acordar o app, e ele leva alguns segundos pra voltar.
