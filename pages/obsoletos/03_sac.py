import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Configuração da página
st.set_page_config(
    page_title="Dashboard SAC",
    page_icon="🎧",
    layout="wide"
)

# 2. Função para gerar dados simulados de SAC
@st.cache_data
def carregar_dados():
    np.random.seed(42)
    n = 300
    datas = pd.date_range(end=pd.Timestamp.today(), periods=60, freq='D')
    
    df = pd.DataFrame({
        'ID_Chamado': [f"SAC-{1000 + i}" for i in range(n)],
        'Data': np.random.choice(datas, size=n),
        'Canal': np.random.choice(['WhatsApp', 'Telefone', 'E-mail', 'Chat Web'], size=n, p=[0.4, 0.25, 0.2, 0.15]),
        'Categoria': np.random.choice(['Dúvida', 'Reclamação', 'Cancelamento', 'Elogio', 'Suporte Técnico'], size=n, p=[0.3, 0.3, 0.15, 0.05, 0.2]),
        'Status': np.random.choice(['Concluído', 'Em Andamento', 'Pendente'], size=n, p=[0.7, 0.2, 0.1]),
        'SLA': np.random.choice(['Dentro do SLA', 'Fora do SLA'], size=n, p=[0.85, 0.15]),
        'Tempo_Resposta_Min': np.random.exponential(scale=15, size=n).round(1),
        'CSAT_Nota': np.random.choice([1, 2, 3, 4, 5], size=n, p=[0.05, 0.1, 0.15, 0.3, 0.4])
    })
    return df

df_sac = carregar_dados()

# 3. Sidebar - Filtros
st.sidebar.header("🔍 Filtros de Atendimento")

canais_selecionados = st.sidebar.multiselect(
    "Canal de Atendimento:",
    options=df_sac['Canal'].unique(),
    default=df_sac['Canal'].unique()
)

status_selecionados = st.sidebar.multiselect(
    "Status do Chamado:",
    options=df_sac['Status'].unique(),
    default=df_sac['Status'].unique()
)

categorias_selecionadas = st.sidebar.multiselect(
    "Categoria:",
    options=df_sac['Categoria'].unique(),
    default=df_sac['Categoria'].unique()
)

# Aplicação dos filtros ao DataFrame
df_filtrado = df_sac[
    (df_sac['Canal'].isin(canais_selecionados)) &
    (df_sac['Status'].isin(status_selecionados)) &
    (df_sac['Categoria'].isin(categorias_selecionadas))
]

# 4. Cabeçalho Principal
st.title("🎧 Acompanhamento de Performance - SAC")
st.markdown("Visão geral dos atendimentos, prazos de SLA e satisfação do cliente (CSAT).")
st.markdown("---")

# 5. KPIs Principais
col1, col2, col3, col4 = st.columns(4)

total_atendimentos = len(df_filtrado)
media_csat = df_filtrado['CSAT_Nota'].mean() if total_atendimentos > 0 else 0
tempo_medio_resposta = df_filtrado['Tempo_Resposta_Min'].mean() if total_atendimentos > 0 else 0
taxa_sla = (df_filtrado['SLA'] == 'Dentro do SLA').mean() * 100 if total_atendimentos > 0 else 0

with col1:
    st.metric("Total de Chamados", total_atendimentos)

with col2:
    st.metric("Média CSAT (1-5)", f"⭐ {media_csat:.2f}")

with col3:
    st.metric("Tempo Médio de Resposta", f"⏱️ {tempo_medio_resposta:.1f} min")

with col4:
    st.metric("Atendimento no SLA", f"🎯 {taxa_sla:.1f}%")

st.markdown("---")

# 6. Gráficos Visualizadores
if total_atendimentos > 0:
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        # Gráfico 1: Volume por Canal
        fig_canal = px.pie(
            df_filtrado, 
            names='Canal', 
            title='Distribuição de Chamados por Canal',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig_canal, use_container_width=True)

        # Gráfico 2: Resolução por Categoria
        fig_cat = px.bar(
            df_filtrado,
            x='Categoria',
            color='Status',
            title='Volume por Categoria e Status',
            barmode='stack',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with g_col2:
        # Gráfico 3: Evolução Temporal dos Atendimentos
        df_tempo = df_filtrado.groupby(df_filtrado['Data'].dt.date).size().reset_index(name='Quantidade')
        fig_tempo = px.line(
            df_tempo,
            x='Data',
            y='Quantidade',
            title='Evolução do Volume Diario de Chamados',
            markers=True
        )
        st.plotly_chart(fig_tempo, use_container_width=True)

        # Gráfico 4: Satisfação por Canal (CSAT)
        fig_csat = px.box(
            df_filtrado,
            x='Canal',
            y='CSAT_Nota',
            color='Canal',
            title='Distribuição da Nota CSAT por Canal'
        )
        st.plotly_chart(fig_csat, use_container_width=True)

    # 7. Tabela Detalhada dos Dados
    st.markdown("### 📋 Tabela Detalhada de Chamados")
    st.dataframe(
        df_filtrado[['ID_Chamado', 'Data', 'Canal', 'Categoria', 'Status', 'SLA', 'CSAT_Nota']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")