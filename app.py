import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path

# Configuração da página
st.set_page_config(
    page_title="XDS Torre de Controle",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Arquivo de preferências do usuário
PREFS_FILE = ".streamlit/user_prefs.json"
Path(PREFS_FILE).parent.mkdir(parents=True, exist_ok=True)

# Função para carregar preferências
def load_preferences():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r") as f:
                return json.load(f)
        except:
            return {"theme": "light"}
    return {"theme": "light"}

# Função para salvar preferências
def save_preferences(prefs):
    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f)

# Carregar preferências
prefs = load_preferences()

# Título principal
st.title("🚀 Bem-vindo ao Meu Projeto Streamlit")

st.markdown("""
Este é o ponto de entrada da sua aplicação Streamlit.
Você pode organizar suas páginas na pasta `pages/`.

### Recursos principais:
- 📊 Visualização de dados
- 🎨 Interface interativa
- 📁 Estrutura modular com múltiplas páginas
""")

# Exemplo simples
st.header("Exemplo de Conteúdo")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Métrica 1", "100", "+10%")

with col2:
    st.metric("Métrica 2", "250", "-5%")

with col3:
    st.metric("Métrica 3", "75", "+20%")

# Sidebar
st.sidebar.header("⚙️ Configurações")

# Informação sobre o tema
st.sidebar.markdown("""
### 🎨 Tema
Clique na engrenagem (⚙️) no **canto superior direito** para alterar o tema entre Light e Dark.

**Temas disponíveis:**
- ☀️ Light (Claro)
- 🌙 Dark (Escuro)
""")

st.sidebar.info("💡 **Dica:** Clique no ⚙️ Settings no canto superior direito da página para personalizar o tema e outras configurações!")

st.sidebar.divider()
st.sidebar.header("📑 Menu")
st.sidebar.markdown("""
- [Home](/)
- [Página 1 - Torre de Controle](pages/03_sac7.py)
- 
""")
