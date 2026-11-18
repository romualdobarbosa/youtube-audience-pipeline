"""Dashboard Streamlit: insights sobre canais de podcast brasileiros no YouTube.

Página secundária — a página padrão do app é a análise da Copa do Mundo 2026
(src/dashboard.py). Esta aqui mostra o mesmo pipeline (ingestão YouTube API → dbt)
aplicado a um segundo problema: ranking de canais de podcast.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    # quando importado como pacote (python -m / testes)
    from ..database import get_engine
except ImportError:
    # quando executado direto: `streamlit run src/dashboard.py` (esta página é
    # descoberta automaticamente em src/pages/)
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.database import get_engine


@st.cache_data(ttl=300)
def load(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_engine())


# Rótulos amigáveis para colunas técnicas (usados em tabelas e eixos dos gráficos).
COLUMN_LABELS = {
    "name": "Canal",
    "handle": "Handle",
    "video_count": "Nº de vídeos",
    "videos": "Nº de vídeos",
    "total_views": "Views totais",
    "avg_views": "Média de views",
    "avg_engagement_rate": "Engajamento médio",
    "short_count": "Shorts",
    "long_count": "Vídeos longos",
    "video_type": "Tipo",
    "catalog_share": "% do catálogo",
    "views_share": "% das views",
    "title": "Título",
    "views": "Views",
    "engagement_rate": "Engajamento",
    "like_rate": "Taxa de likes",
    "comment_rate": "Taxa de comentários",
    "views_per_day": "Views/dia",
    "likes": "Likes",
    "comments": "Comentários",
    "favorites": "Favoritos",
    "duration_seconds": "Duração (s)",
    "category_id": "Categoria",
    "published_at": "Publicado em",
    "collected_at": "Coleta",
    "prev_collected_at": "Coleta anterior",
    "subscriber_count": "Inscritos",
    "subscriber_delta": "Variação de inscritos",
    "total_views_delta": "Variação de views totais",
    "views_delta": "Variação de views",
    "views_per_day_delta": "Variação de views/dia",
    "uploads": "Uploads",
    "weekday": "Dia (nº)",
    "dia": "Dia",
}


def table(df: pd.DataFrame) -> None:
    """Mostra um DataFrame sem o índice, sem channel_id e com rótulos amigáveis."""
    df = df.drop(columns=["channel_id"], errors="ignore").rename(columns=COLUMN_LABELS)
    st.dataframe(df, use_container_width=True, hide_index=True)


st.set_page_config(page_title="Podcasts BR no YouTube", layout="wide")
st.title("Podcasts brasileiros no YouTube")
st.caption(
    "A mesma ingestão e o mesmo dbt da análise da Copa 2026, aqui usados pra "
    "comparar cinco canais de podcast."
)

# Num clone sem data/youtube.db (e sem DB_BACKEND=turso) os marts não existem:
# mostra o aviso em vez de estourar o traceback.
try:
    ranking = load("SELECT * FROM channel_ranking")
except pd.errors.DatabaseError:
    ranking = pd.DataFrame()

if ranking.empty:
    st.warning(
        "Sem dados de podcasts neste ambiente. Pra coletar, siga o docs/podcasts.md "
        "(ingestão com `uv run python -m src.main` e depois o dbt)."
    )
    st.stop()

svl = load("SELECT * FROM short_vs_long")
latest = load("SELECT * FROM latest_video_metrics")
growth = load("SELECT * FROM channel_growth")
vgrowth = load("SELECT * FROM video_growth")
cadence = load("SELECT * FROM upload_cadence")

TIPOS = {"short": "Shorts", "long": "Vídeos longos"}
for df in (svl, latest, vgrowth):
    if "video_type" in df.columns:
        df["video_type"] = df["video_type"].map(TIPOS).fillna(df["video_type"])

# --- Ranking de canais --------------------------------------------------------
st.header("Ranking de canais")
metric = st.selectbox(
    "Ordenar por",
    ["total_views", "avg_views", "avg_engagement_rate", "video_count"],
    format_func=lambda c: COLUMN_LABELS.get(c, c),
)
ranked = ranking.sort_values(metric, ascending=False)
st.plotly_chart(
    px.bar(
        ranked,
        x="name",
        y=metric,
        title=f"Canais por {COLUMN_LABELS.get(metric, metric)}",
        labels=COLUMN_LABELS,
    ),
    use_container_width=True,
)
table(ranked)

# --- Shorts vs vídeos longos: catálogo x views ----------------------------------
st.header("Shorts e vídeos longos")
if not svl.empty:
    agg = svl.groupby("video_type")[["videos", "total_views"]].sum().reset_index()
    agg["catalog_share"] = agg["videos"] / agg["videos"].sum()
    agg["views_share"] = agg["total_views"] / agg["total_views"].sum()
    # Texto calculado dos próprios dados, pra nunca contradizer o gráfico.
    for row in agg.sort_values("video_type", ascending=False).itertuples():
        st.caption(
            f"{row.video_type} são {row.catalog_share:.0%} do catálogo e levam "
            f"{row.views_share:.0%} das views."
        )
    comp = agg.melt(
        id_vars="video_type",
        value_vars=["catalog_share", "views_share"],
        var_name="métrica",
        value_name="proporção",
    )
    comp["métrica"] = comp["métrica"].map(
        {"catalog_share": "Fatia no catálogo", "views_share": "Fatia nas views"}
    )
    st.plotly_chart(
        px.bar(
            comp,
            x="métrica",
            y="proporção",
            color="video_type",
            barmode="group",
            title="Fatia no catálogo e fatia nas views",
            labels={**COLUMN_LABELS, "métrica": "", "proporção": "Proporção"},
        ),
        use_container_width=True,
    )
    table(svl)

# --- Picos de interesse em episódios ------------------------------------------
st.header("Episódios em destaque")
tab_top, tab_spikes = st.tabs(["Mais vistos", "Maiores saltos"])
with tab_top:
    top = latest.sort_values("views", ascending=False).head(20)
    st.plotly_chart(
        px.bar(
            top,
            x="title",
            y="views",
            color="video_type",
            title="Os 20 vídeos mais vistos",
            labels=COLUMN_LABELS,
        ),
        use_container_width=True,
    )
    table(top[["title", "video_type", "views", "engagement_rate", "views_per_day"]])
with tab_spikes:
    if vgrowth.empty:
        st.info("Os saltos só aparecem depois de pelo menos 2 coletas.")
    else:
        spikes = vgrowth.sort_values("views_delta", ascending=False).head(20)
        st.plotly_chart(
            px.bar(
                spikes,
                x="title",
                y="views_delta",
                title="Maiores saltos de views entre coletas",
                labels=COLUMN_LABELS,
            ),
            use_container_width=True,
        )
        table(spikes)

# --- Crescimento de inscritos -------------------------------------------------
st.header("Crescimento de inscritos")
if growth.empty:
    st.info("O crescimento só aparece depois de pelo menos 2 coletas.")
else:
    st.plotly_chart(
        px.bar(
            growth.sort_values("subscriber_delta", ascending=False),
            x="name",
            y="subscriber_delta",
            title="Inscritos ganhos entre coletas",
            labels=COLUMN_LABELS,
        ),
        use_container_width=True,
    )
    table(growth)

# --- Cadência de upload -------------------------------------------------------
st.header("Cadência de upload")
if not cadence.empty:
    dias = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}
    cad = cadence.merge(ranking[["channel_id", "name"]], on="channel_id", how="left")
    cad["dia"] = cad["weekday"].map(dias)
    st.plotly_chart(
        px.bar(
            cad,
            x="dia",
            y="avg_views",
            color="name",
            title="Views médias por dia de publicação",
            labels=COLUMN_LABELS,
        ),
        use_container_width=True,
    )
    table(cad.drop(columns=["weekday"]))
