import streamlit as st
import numpy as np

st.header("📈 Página 2 - Gráficos Interativos")

st.markdown("Exemplos de gráficos interativos com Streamlit")

# Slider
st.subheader("Controles Interativos")
num_points = st.slider("Número de pontos", 10, 1000, 100)

# Gerar dados aleatórios
data = np.random.randn(num_points, 3).cumsum()

st.line_chart(data)

# Seletor
st.subheader("Filtros")
option = st.selectbox(
    "Escolha um tipo de visualização:",
    ["Linha", "Área", "Coluna"]
)

if option == "Linha":
    st.line_chart(data)
elif option == "Área":
    st.area_chart(data)
else:
    st.bar_chart(data)

# Checkbox
if st.checkbox("Mostrar dados em formato de tabela"):
    st.dataframe(data)

# Botão
if st.button("Gerar novos dados"):
    st.balloons()
    st.write("✅ Novos dados gerados com sucesso!")
