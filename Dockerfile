FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:${PATH}"

# Instala as dependências primeiro para aproveitar o cache de layers do Docker
# em rebuilds que só mudam código-fonte. Só o runtime: sem o grupo dev e sem os
# grupos dbt (ver nota abaixo).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

COPY src/ ./src/
COPY copa2026/ ./copa2026/
COPY dbt/ ./dbt/

# data/ e logs/ são criados em runtime pelo próprio código (config.py / database.py)
# e devem ser montados como volume — nunca ficam embutidos na imagem.
#
# Os grupos dbt-podcasts e dbt-copa (pyproject.toml) não entram na imagem de
# propósito: pinam versões de dbt-core diferentes e incompatíveis entre si
# (dbt-sqlite vs dbt-duckdb), por isso estão em [tool.uv] conflicts. Os serviços
# "dbt" e "copa-dbt" do docker-compose sincronizam cada um o seu grupo na hora
# de rodar, em vez de tudo pré-instalado nesta imagem.

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard.py", "--server.address=0.0.0.0"]
