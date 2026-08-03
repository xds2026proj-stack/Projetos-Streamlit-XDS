import streamlit as st
import pandas as pd
import numpy as np

st.header("📊 Página 1 - Análise de Dados")

st.markdown("Exemplo de visualização de dados com Streamlit")

# Criar dados de exemplo
data = {
    "Mês": ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho"],
    "Vendas": [100, 150, 120, 200, 180, 220],
    "Custos": [50, 70, 60, 90, 85, 100]
}

df = pd.DataFrame(data)

# Exibir tabela
st.subheader("Dados da Tabela")
st.dataframe(df, use_container_width=True)

# Gráfico
st.subheader("Visualização")
col1, col2 = st.columns(2)

with col1:
    st.line_chart(df.set_index("Mês"))

with col2:
    st.bar_chart(df.set_index("Mês"))

# Métricas
st.subheader("Resumo")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total de Vendas", f"R$ {df['Vendas'].sum()}")

with col2:
    st.metric("Total de Custos", f"R$ {df['Custos'].sum()}")

with col3:
    lucro = df['Vendas'].sum() - df['Custos'].sum()
    st.metric("Lucro", f"R$ {lucro}")
