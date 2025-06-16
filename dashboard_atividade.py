import streamlit as st
import pandas as pd
import requests

# 🔐 Token seguro
token = st.secrets["SHAREPOINT_TOKEN"]
headers = {"Authorization": f"Bearer {token}"}


site_id = st.secrets["SHAREPOINT_SITE_ID"]
list_id = st.secrets["SHAREPOINT_LIST_ID"]

@st.cache_data
def carregar_dados():
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields"
    r = requests.get(url, headers=headers).json()
    if "value" not in r:
        st.error("Erro ao buscar dados")
        st.stop()
    return pd.DataFrame([i["fields"] for i in r["value"]])

df = carregar_dados()
df["Data"] = pd.to_datetime(df["Data"])

# Interface igual ao que montamos antes (resumo, filtros, gráficos, tabela)...
