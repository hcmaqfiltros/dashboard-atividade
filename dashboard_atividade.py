import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from streamlit_plotly_events import plotly_events
import plotly.graph_objects as go

# === CONFIGURAÇÕES ===
SITE_ID = "maqfiltros3.sharepoint.com,68b563be-e515-4193-9b5b-4dcf121342e8,347a1963-1db4-4613-8841-056a68baf7ec"
LIST_ID = "418a9527-5b59-432e-8d95-bad94ef6aed1"
ACCESS_TOKEN = st.secrets["SHAREPOINT_TOKEN"]

HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

def get_sharepoint_items(site_id, list_id):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields&$top=999"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    items = [item["fields"] for item in data["value"]]
    return pd.DataFrame(items)

# === CARREGAMENTO E RENOMEAÇÃO ===
df_original = get_sharepoint_items(SITE_ID, LIST_ID)

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
df = df_original.rename(columns=FIELD_MAPPING)

# CONVERSÃO DAS DATAS
for campo in ["Data de Emissão", "Data de Início", "Data Início", "Data Final"]:
    if campo in df.columns:
        df[campo] = pd.to_datetime(df[campo], errors='coerce')

# === INTERFACE ===
st.set_page_config(page_title="Dashboard de Atividades", layout="wide")
st.title("📊 Painel de Acompanhamento das Atividades")

# === FILTROS ===
col1, col2 = st.columns(2)
with col1:
    operadores = st.multiselect("Filtrar por Operador", sorted(df["Operador"].dropna().unique()), default=sorted(df["Operador"].dropna().unique()))
with col2:
    equipe = st.selectbox("Filtrar por Equipe", ["Todas"] + sorted(df["Equipe"].dropna().unique()))

with st.expander("🗓️ Filtrar por Data de Emissão"):
    data_min = df["Data de Emissão"].min().date()
    data_max = df["Data de Emissão"].max().date()
    data_inicio, data_fim = st.date_input("Intervalo:", value=(data_min, data_max), min_value=data_min, max_value=data_max)

# === BASE PRINCIPAL COM FILTROS GERAIS ===
df_total_filtrado = df.copy()

if operadores:
    df_total_filtrado = df_total_filtrado[df_total_filtrado["Operador"].isin(operadores)]
if equipe != "Todas":
    df_total_filtrado = df_total_filtrado[df_total_filtrado["Equipe"] == equipe]

df_total_filtrado = df_total_filtrado[
    (df_total_filtrado["Data de Emissão"].dt.date >= data_inicio) &
    (df_total_filtrado["Data de Emissão"].dt.date <= data_fim)
]

st.markdown(f"### Total de Atividades na Visualização: **{len(df_total_filtrado)}**")


# === GRÁFICO 1: Atividades por Operador ===
df_grouped = df_total_filtrado.groupby(["Operador", "Atividade"]).size().reset_index(name="Contagem")

fig = px.histogram(
    df_total_filtrado,
    x="Operador",
    barmode="stack",
    text_auto=True,
    labels={"Contagem": "Contagem"},
    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white",
)

st.subheader("Atividades por Operador")


selected = plotly_events(fig, click_event=True, key="grafico_operadores")

if selected:
    operador_selecionado = selected[0]["x"]  # valor clicado no eixo X
    st.success(f"Operador selecionado: {operador_selecionado}")
    df_total_filtrado = df[df["Operador"] == operador_selecionado]



# === GRÁFICO 2: Atividades em Atraso por Operador ===
hoje = pd.Timestamp.now().normalize()

df_atrasadas = df_total_filtrado[df_total_filtrado["Data Final"].notna()]
df_atrasadas = df_atrasadas[df_atrasadas["Data Final"].dt.date <= hoje.date()]

df_operador_atraso = df_atrasadas.groupby("Operador").size().reset_index(name="Atividades em Atraso")

fig_atraso = px.histogram(
    df_atrasadas,
    x="Operador",
    text_auto=True,
    labels={"Atividades em Atraso": "Qtd. Atrasadas"},
    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"
)

st.subheader("Operador X Atividades em Atraso")
selected_atraso = plotly_events(fig_atraso, click_event=True, key="grafico2")

# === GRÁFICO 3: Tipo de Atividade por Cliente ===
df_atividade_cliente = df_total_filtrado.groupby(["Atividade", "Cliente"]).size().reset_index(name="Contagem")

fig_atividade_cliente = px.histogram(
    df_total_filtrado,
    x="Cliente",
    color="Atividade",
    text_auto=True,
    barmode="stack",
    labels={"Contagem": "Nº Atividades"},
    template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"
)

st.subheader("Tipo de Atividade X Cliente")
selected_cliente = plotly_events(fig_atividade_cliente, click_event=True, key="grafico3")

# === APLICANDO FILTROS DE CLIQUES ===
df_filtrado = df_total_filtrado.copy()

if selected:
    operador_selecionado = selected[0]["x"]
    st.success(f"Operador selecionado no gráfico 1: **{operador_selecionado}**")
    df_filtrado = df_filtrado[df_filtrado["Operador"] == operador_selecionado]

if selected_atraso:
    operador_atraso = selected_atraso[0]["x"]
    st.success(f"Operador selecionado no gráfico 2: **{operador_atraso}**")
    df_filtrado = df_filtrado[
        (df_filtrado["Operador"] == operador_atraso) &
        (df_filtrado["Data Final"].notna()) &
        (df_filtrado["Data Final"].dt.date <= hoje.date())
    ]

if selected_cliente:
    cliente_sel = selected_cliente[0]["x"]
    st.success(f"Cliente selecionado no gráfico 3: **{cliente_sel}**")
    df_filtrado = df_filtrado[df_filtrado["Cliente"] == cliente_sel]

df_filtrado["Data Final"] = pd.to_datetime(df_filtrado["Data Final"], errors="coerce")

# Cria a coluna apenas para atividades atrasadas
df_filtrado["Data Final"] = pd.to_datetime(df_filtrado["Data Final"], errors="coerce").dt.tz_localize(None)
df_filtrado["Dias em Atraso"] = (hoje - df_filtrado["Data Final"]).dt.days
df_filtrado.loc[df_filtrado["Dias em Atraso"] < 0, "Dias em Atraso"] = None  # ou 0, se preferir



# === TABELA DE ATIVIDADES ===
df_filtrado["Data Final"] = df_filtrado["Data Final"].dt.strftime("%d/%m/%y")
df_filtrado["Data Início"] = df_filtrado["Data Início"].dt.strftime("%d/%m/%y")

st.subheader("📋 Tabela de Atividades")
st.dataframe(df_filtrado[[
    "Atividade", "Cliente", "Operador", "Equipe", "Data Início", "Data Final", "Descrição da Atividade", "Dias em Atraso"
]].sort_values("Dias em Atraso"))

# === BOTÃO DE RESET ===
if st.button("🔄 Resetar Filtros de Gráfico"):
    st.rerun()

