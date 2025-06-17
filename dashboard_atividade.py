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
    "field_7": "Data de Término",
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

hoje = pd.Timestamp.now().normalize()
# Cálculo da taxa de atraso por equipe
df_equipes = df_total_filtrado.copy()
df_equipes["Data Final"] = pd.to_datetime(df_equipes["Data Final"], errors="coerce")
df_equipes["Data de Término"] = pd.to_datetime(df_equipes["Data de Término"], errors="coerce")

def taxa_atraso_grupo(df, grupo):
    taxas = []
    for item, grupo_df in df.groupby(grupo):
        grupo_df["Data Final"] = pd.to_datetime(grupo_df["Data Final"]).dt.tz_localize(None)
        grupo_df["Data de Término"] = pd.to_datetime(grupo_df["Data de Término"]).dt.tz_localize(None)
        em_aberto = grupo_df[grupo_df["Data de Término"].isna() & (grupo_df["Data Final"] < hoje)]
        fora_prazo = grupo_df[(grupo_df["Data de Término"].notna()) & (grupo_df["Data de Término"] > grupo_df["Data Final"])]
        total = len(grupo_df)
        taxa = (len(em_aberto) + len(fora_prazo)) / total * 100 if total > 0 else 0
        taxas.append((item, taxa))
    return sorted(taxas, key=lambda x: x[1])



# Equipes ordenadas por melhor performance
ranking_equipes = taxa_atraso_grupo(df, "Equipe")

# Operadores ordenados por melhor performance
ranking_operadores = taxa_atraso_grupo(df, "Operador")

ranking_clientes = df["Cliente"].value_counts().head(3)

st.markdown("### 🥇 Pódios de Desempenho")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**🏆 Melhor Equipe**")
    for i, (equipe, taxa) in enumerate(ranking_equipes[:3], start=1):
        st.metric(f"{i}º - {equipe}", f"{taxa:.1f}%", help="Menor taxa de atraso")

with col2:
    st.markdown("**🏅 Melhor Colaborador**")
    for i, (operador, taxa) in enumerate(ranking_operadores[:3], start=1):
        st.metric(f"{i}º - {operador}", f"{taxa:.1f}%", help="Menor taxa de atraso")

with col3:
    st.markdown("**📦 Cliente com Mais Atividades**")
    for i, (cliente, qtd) in enumerate(ranking_clientes.items(), start=1):
        st.metric(f"{i}º - {cliente}", f"{qtd} atividades")



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

df_total_filtrado["Data Final"] = pd.to_datetime(df_total_filtrado["Data Final"], errors="coerce").dt.tz_localize(None)
df_total_filtrado["Data de Término"] = pd.to_datetime(df_total_filtrado["Data de Término"], errors="coerce").dt.tz_localize(None)
hoje = pd.Timestamp.now().normalize()



df_atrasadas = df_total_filtrado[
    df_total_filtrado["Data de Término"].isna() &
    df_total_filtrado["Data Final"].notna() &
    (df_total_filtrado["Data Final"] < hoje)
]

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


df_filtrado["Data Final"] = pd.to_datetime(df_filtrado["Data Final"], errors="coerce").dt.tz_localize(None)
df_filtrado["Dias em Atraso"] = df_filtrado.apply(
    lambda row: (hoje - row["Data Final"]).days if pd.isna(row["Data de Término"]) and pd.notna(row["Data Final"]) and row["Data Final"] < hoje else None,
    axis=1
)

#ppc

st.title("Painel de Processos e Controle")

import streamlit as st
import pandas as pd


df_filtrado["Data Final"] = pd.to_datetime(df_filtrado["Data Final"], errors="coerce")
df_filtrado["Data Início"] = pd.to_datetime(df_filtrado["Data Início"], errors="coerce")

# Hoje sem fuso
hoje = pd.Timestamp.now().normalize()

def calcular_taxa_fora_prazo(df, atividades):
    df_atividade = df[df["Atividade"].isin(atividades)].copy()
    if df_atividade.empty:
        return 0.0

    concluida = df_atividade[df_atividade["Data de Término"].notna()].copy()
    em_aberto = df_atividade[df_atividade["Data de Término"].isna()]

    # Corrigindo timezone (ponto-chave para evitar erro)
    concluida["Data Início"] = pd.to_datetime(concluida["Data Início"]).dt.tz_localize(None)
    concluida["Data Final"] = pd.to_datetime(concluida["Data Final"]).dt.tz_localize(None)
    concluida["Data de Término"] = pd.to_datetime(concluida["Data de Término"]).dt.tz_localize(None)

    concluida_no_prazo = concluida[concluida["Data de Término"] <= concluida["Data Final"]]
    concluida_fora_prazo = concluida[concluida["Data de Término"] > concluida["Data Final"]]

    total = len(concluida_no_prazo) + len(concluida_fora_prazo) + len(em_aberto)
    if total == 0:
        return 0.0

    return (len(concluida_fora_prazo) + len(em_aberto)) / total * 100



# === CÁLCULOS DAS TAXAS ===
tx_instalacoes = calcular_taxa_fora_prazo(df_filtrado, ["INSTALACAO"])
tx_entregas = calcular_taxa_fora_prazo(df_filtrado, ["ENTREGA DE MERCADORIA"])
tx_manutencoes = calcular_taxa_fora_prazo(df_filtrado, ["TROCA DE CARGAS"])
tx_visitas = calcular_taxa_fora_prazo(df_filtrado, ["VISITA TÉCNICA", "OPERAÇÃO CONTRATUAL"])

# === VALORES DE REFERÊNCIA (RÉGUAS) ===
limites = {
    "instalacoes": 30,
    "entregas": 20,
    "manutencoes": 20,
    "visitas": 10
}

def criar_card(texto, valor, limite):
    cor = "#2ecc71" if valor <= limite else "#e74c3c"  # verde ou vermelho
    return f"""
    <div style='
        background-color:{cor};
        padding:20px;
        border-radius:10px;
        margin-bottom:10px;
        text-align:center;
        color:white;
        font-weight:bold;
        font-size:18px;
    '>
        {texto}<br><span style='font-size:28px'>{valor:.2f}%</span>
    </div>
    """

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    st.markdown(criar_card("Tx. Instalações fora do prazo", tx_instalacoes, limites["instalacoes"]), unsafe_allow_html=True)

with col2:
    st.markdown(criar_card("Tx. Entregas fora do prazo", tx_entregas, limites["entregas"]), unsafe_allow_html=True)

with col3:
    st.markdown(criar_card("Tx. Manutenções fora do prazo", tx_manutencoes, limites["manutencoes"]), unsafe_allow_html=True)

with col4:
    st.markdown(criar_card("Tx. Visitas fora do prazo", tx_visitas, limites["visitas"]), unsafe_allow_html=True)

with st.expander("ℹ️ Como os Indicadores são Calculados"):
    st.markdown("""
**📌 Metodologia dos Indicadores Operacionais**

Cada taxa representa a **porcentagem de atividades que não foram concluídas no prazo** estipulado. O prazo considerado é a **“Data Final”** informada para a atividade.

- **Tx. Instalações fora do prazo:**  
  Considera atividades com tipo `INSTALACAO`.

- **Tx. Entregas fora do prazo:**  
  Considera atividades com tipo `ENTREGA DE MERCADORIA`.

- **Tx. Manutenções fora do prazo:**  
  Considera atividades com tipo `TROCA DE CARGAS`.

- **Tx. Visitas fora do prazo:**  
  Considera atividades com tipo `VISITA TÉCNICA` e `OPERAÇÃO CONTRATUAL`.

A fórmula utilizada:

(Atividades em aberto (sem data de término) + Concluídas fora do prazo) ÷ Total de atividades analisadas × 100)
""")




# === TABELA DE ATIVIDADES ===
df_filtrado["Data Final"] = df_filtrado["Data Final"].dt.strftime("%d/%m/%y")
df_filtrado["Data Início"] = df_filtrado["Data Início"].dt.strftime("%d/%m/%y")

st.subheader("📋 Tabela de Atividades")
st.dataframe(df_filtrado[[
    "Atividade", "Cliente", "Operador", "Equipe", "Data Início", "Data Final","Data de Término","Dias em Atraso", "Descrição da Atividade", 
]].sort_values("Dias em Atraso"))

# === BOTÃO DE RESET ===
if st.button("🔄 Resetar Filtros de Gráfico"):
    st.rerun()

