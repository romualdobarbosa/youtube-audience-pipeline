"""Dashboard Streamlit — página padrão: "Quem ganhou a guerra de relevância no
YouTube brasileiro durante a Copa do Mundo 2026?"

Lê as tabelas persistidas pelo dbt (copa2026/dbt/models/marts/) no
data/copa2026.duckdb. A análise secundária (ranking de podcasts BR, mesmo
pipeline aplicado a outro problema) está em src/pages/.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from .config import PROJECT_ROOT
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.config import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "copa2026.duckdb"

COLUMN_LABELS = {
    "channel_name": "Canal",
    "time_window": "Janela",
    "video_count": "Nº de vídeos",
    "total_views": "Views totais",
    "avg_views": "Média de views",
    "avg_engagement_rate": "Engajamento médio",
    "share_of_voice": "Share of voice",
    "pre_copa_videos": "Vídeos (Pré-Copa)",
    "pre_copa_views": "Views (Pré-Copa)",
    "pre_copa_engagement_rate": "Engajamento (Pré-Copa)",
    "copa_videos": "Vídeos (Copa)",
    "copa_views": "Views (Copa)",
    "copa_engagement_rate": "Engajamento (Copa)",
    "copa_share_of_voice": "Share of voice (Copa)",
    "pos_copa_videos": "Vídeos (Pós-Copa)",
    "pos_copa_views": "Views (Pós-Copa)",
    "pos_copa_engagement_rate": "Engajamento (Pós-Copa)",
    "views_growth_copa_vs_pre": "Variação de views (Copa vs Pré)",
    "views_growth_pct_copa_vs_pre": "% crescimento (Copa vs Pré)",
    "engagement_delta_copa_vs_pre": "Variação de engajamento (Copa vs Pré)",
    "views_delta_pos_vs_copa": "Variação de views (Pós vs Copa)",
    "engagement_delta_pos_vs_copa": "Variação de engajamento (Pós vs Copa)",
}

WINDOW_ORDER = ["Pré-Copa", "Copa", "Pós-Copa"]


@st.cache_data(ttl=300)
def load(query: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(query).df()
    finally:
        con.close()


def table(df: pd.DataFrame) -> None:
    st.dataframe(
        df.drop(columns=["channel_id"], errors="ignore").rename(columns=COLUMN_LABELS),
        use_container_width=True,
        hide_index=True,
    )


st.set_page_config(page_title="Copa 2026 no YouTube", layout="wide")
st.title("Quem ganhou a guerra de relevância no YouTube brasileiro durante a Copa do Mundo 2026?")
st.caption(
    "Performance por vídeo da CazéTV, GE TV, N Sports e TNT Sports Brasil em 3 janelas. "
    "Pré-Copa (01/05 a 10/06), Copa (11/06 a 19/07) e Pós-Copa (20/07 a 31/08)."
)

if not DB_PATH.exists():
    st.warning(
        "Ainda não tem dados aqui. Rode a coleta e depois o dbt:\n\n"
        "```\nuv run python -m copa2026.ingest\n"
        "cd copa2026/dbt && uv run --group dbt-copa dbt build --profiles-dir .\n```"
    )
    st.stop()

with st.expander("Por que 3 janelas de publicação, e não uma curva de inscritos?"):
    st.markdown(
        "A YouTube Data API só informa quantos inscritos e views cada canal tem hoje. "
        "Não existe um jeito público de saber quanto eles tinham em junho, então não dá "
        "pra desenhar uma curva de inscritos.\n\n"
        "Por isso eu comparo os vídeos publicados em cada janela, olhando quantos saíram, "
        "quantas views tiveram, o engajamento e a fatia de views de cada canal. A coleta "
        "usa `playlistItems.list` e `videos.list`, que gastam cerca de 100 vezes menos "
        "cota de API que o `search.list`."
    )

comparison = load("SELECT * FROM channel_window_comparison")
metrics = load("SELECT * FROM channel_window_metrics")

if comparison.empty:
    st.warning(
        "As tabelas estão vazias. Rode `uv run python -m copa2026.ingest` e depois o "
        "`dbt build` em `copa2026/dbt/`."
    )
    st.stop()

# --- Share of voice por janela --------------------------------------------------
st.header("Quem dominou cada janela (share of voice)")
metrics["time_window"] = pd.Categorical(
    metrics["time_window"], categories=WINDOW_ORDER, ordered=True
)
st.plotly_chart(
    px.bar(
        metrics.sort_values("time_window"),
        x="channel_name",
        y="share_of_voice",
        color="time_window",
        barmode="group",
        title="Fatia de cada canal nas views do grupo, por janela",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)
table(metrics.sort_values(["time_window", "total_views"], ascending=[True, False]))

# --- Quem cresceu com a Copa -----------------------------------------------------
st.header("Quem cresceu na Copa")
growth = comparison.sort_values("views_growth_copa_vs_pre", ascending=False)
st.plotly_chart(
    px.bar(
        growth,
        x="channel_name",
        y="views_growth_copa_vs_pre",
        title="Views a mais na Copa em relação à Pré-Copa",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)

# --- Quem reteve engajamento depois -----------------------------------------------
st.header("Quem segurou o engajamento depois da Copa")
retention = comparison.sort_values("engagement_delta_pos_vs_copa", ascending=False)
st.plotly_chart(
    px.bar(
        retention,
        x="channel_name",
        y="engagement_delta_pos_vs_copa",
        title="Variação do engajamento médio da Copa pro Pós-Copa",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)

# --- Tabela comparativa completa --------------------------------------------------
st.header("Tabela comparativa completa")
table(comparison.sort_values("copa_share_of_voice", ascending=False))
