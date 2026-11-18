# ADR 0001. DuckDB pra Copa 2026, Turso pros podcasts

Status: aceito (set/2026)

## Contexto

O repo tem duas análises em cima do mesmo cliente da YouTube Data API v3, e cada uma acessa os dados de um jeito.

A Copa 2026 olha três janelas de datas que já passaram. A coleta roda uma vez, carrega tudo e o trabalho pesado é analítico (joins, agregações e window functions por canal e janela).

Os podcasts precisam de coleta recorrente pra que as dimensões SCD2 acumulem histórico. Cada execução faz muitas escritas pequenas (um upsert por canal e por vídeo) e roda num runner do GitHub Actions, que é efêmero e perde o disco no fim de cada job.

## Decisão

A Copa usa DuckDB num arquivo local, `data/copa2026.duckdb`, versionado no repo. É um caso típico de OLAP local, carga única e consulta pesada, e o arquivo commitado deixa o dashboard rodar sem API key e sem banco externo.

Os podcasts usam Turso (libSQL gerenciado). A carga é transacional e recorrente, e o store precisa sobreviver entre execuções de um runner sem disco persistente.

O dbt dos podcasts usa o adapter `dbt-sqlite`, que só lê arquivo SQLite local e não fala libSQL remoto. Por isso `dbt/sync_replica.py` espelha as tabelas do Turso pra `data/youtube.db` antes do `dbt run`, e `dbt/push_marts_to_turso.py` devolve os marts pro Turso depois, pro dashboard publicado conseguir ler.

## Consequências

- O fluxo dos podcasts ganha dois passos de cópia (Turso pra SQLite e marts de volta pro Turso). O `dbt/profiles.yml` aponta sempre pro arquivo local, venha ele de onde vier.
- Cada escrita no Turso custa um round-trip de rede (medi uns 0,2 s por vídeo na época, comentário em `src/config.py`). Foi isso que me fez cortar a lista de 19 pra 5 canais.
- O plano free do Turso tem cota de escrita. Reescrever o mart `video_growth` inteiro todo dia estourou essa cota em set/2026, e o cron foi desligado. O `push_marts_to_turso.py` passou a mandar só o top 1.000 desse mart, caso a coleta volte.
- Pra atualizar a Copa é preciso rodar a ingestão e o dbt localmente e commitar o `.duckdb` de novo. Como as janelas estão no passado, isso não deve acontecer.
