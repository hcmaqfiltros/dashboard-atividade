import pandas as pd
import streamlit as st
import plotly.express as px
import requests

# === CONFIGURAÇÕES ===
SITE_ID = "maqfiltros3.sharepoint.com,68b563be-e515-4193-9b5b-4dcf121342e8,347a1963-1db4-4613-8841-056a68baf7ec"
LIST_ID = "418a9527-5b59-432e-8d95-bad94ef6aed1"
ACCESS_TOKEN = st.secrets["SHAREPOINT_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# === FUNÇÃO PARA OBTER DADOS ===
def get_sharepoint_items(site_id, list_id):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields&$top=999"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    items = [item["fields"] for item in data["value"]]
    return pd.DataFrame(items)

# === CARREGAMENTO E RENOMEAÇÃO ===
df = get_sharepoint_items(SITE_ID, LIST_ID)

FIELD_MAPPING = {
    "field_2": "Atividade",
    "field_3": "Cliente",
    "field_5": "Data de Emissão",
    "field_6": "Data de Início",
    "field_8": "Data Final",
    "field_9": "Data Início",
    "field_10": "Descrição da Atividade",
    "field_12": "Emissor",
    "field_16": "Nº Nota Fiscal",
    "field_17": "Qtd. Bombonas",
    "field_19": "Operador",
    "Equipe": "Equipe"
}
df = df.rename(columns=FIELD_MAPPING)

# === LIMPAR CAMPOS DE DATA E REMOVER TIMEZONE ===
for campo in ["Data de Emissão", "Data de Início", "Data Início", "Data Final"]:
    if campo in df.columns:
        df[campo] = pd.to_datetime(df[campo], errors='coerce')
        df[campo] = df[campo].dt.tz_localize(None)

# === DASHBOARD STREAMLIT ===
st.set_page_config(page_title="Dashboard de Atividades", layout="wide")

st.title("📊 Painel de Acompanhamento Operacional")
st.markdown("Este painel mostra as atividades registradas pelos operadores da Maqfiltros.")

# === FILTROS ===
col1, col2 = st.columns(2)
with col1:
    operador = st.selectbox("Filtrar por Operador", ["Todos"] + sorted(df["Operador"].dropna().unique()))
with col2:
    equipe = st.selectbox("Filtrar por Equipe", ["Todas"] + sorted(df["Equipe"].dropna().unique()))

df_filtrado = df.copy()
if operador != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Operador"] == operador]
if equipe != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Equipe"] == equipe]

# === GRÁFICO DE ATIVIDADES POR OPERADOR ===
st.subheader("Distribuição de Atividades por Operador")
fig = px.histogram(df_filtrado, x="Operador", color="Equipe", barmode="group")
st.plotly_chart(fig, use_container_width=True)

# === TAREFAS PENDENTES E URGENTES ===
st.subheader("🚨 Tarefas Não Concluídas e Próximas do Vencimento")
hoje = pd.Timestamp.now().normalize()  # tz-naive

pendentes = df_filtrado[df_filtrado["Data Final"].notna()].copy()
pendentes["Dias Restantes"] = (pendentes["Data Final"] - hoje).dt.days
urgentes = pendentes[pendentes["Dias Restantes"] <= 2]

st.dataframe(urgentes[[
    "Atividade", "Cliente", "Operador", "Equipe", "Data Final", "Dias Restantes"
]].sort_values("Data Final"))

# === TABELA COMPLETA DE ATIVIDADES ===
st.subheader("📋 Tabela de Atividades")
st.dataframe(df_filtrado[[
    "Atividade", "Cliente", "Operador", "Equipe", "Data Início", "Data Final", "Descrição da Atividade"
]].sort_values("Data Final"))
