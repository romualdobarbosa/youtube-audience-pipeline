"""Ponto de entrada do dashboard Streamlit (o Streamlit Cloud aponta pra este arquivo).

Só define a navegação. A análise principal (Copa 2026) está em src/copa.py e a
secundária (podcasts BR) em src/pages/. Com st.navigation o Streamlit não
descobre src/pages/ sozinho, então cada página é listada aqui.
"""

import streamlit as st

st.set_page_config(layout="wide")

st.navigation(
    [
        st.Page("copa.py", title="Copa do Mundo", icon="⚽", default=True),
        st.Page("pages/1_🎙️_Podcasts_BR.py", title="Podcasts BR", icon="🎙️"),
    ]
).run()
