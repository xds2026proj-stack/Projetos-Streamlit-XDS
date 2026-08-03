import gspread
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestão de Entregas", layout="wide")
st.title("🚚 Acompanhamento de Entregas")

# URL da sua planilha
URL_PLANILHA = (
    "https://docs.google.com/spreadsheets/d/1xvInELpQ5BeRlNKOXQJ9xLhftv77W2bkFvSFhz10JIg/edit?gid=922738788#gid=922738788"
)


# Função para conectar usando gspread nativo através do secrets.toml
@st.cache_resource
def conectar_gsheets():
    # Pega as credenciais direto da seção [connections.gsheets]
    credentials = dict(st.secrets["connections"]["gsheets"])
    # Autentica
    gc = gspread.service_account_from_dict(credentials)
    return gc


try:
    gc = conectar_gsheets()
    # Abre a planilha pela URL
    sh = gc.open_by_url(URL_PLANILHA)

    # Seleciona a primeira aba
    worksheet = sh.get_worksheet(0)

    # Pega todos os registros em um DataFrame Pandas
    dados = worksheet.get_all_records()
    df = pd.DataFrame(dados)

    # Exibe os dados
    st.success("Conectado com sucesso!")
    #st.dataframe(df)

except Exception as e:
    st.error(f"Erro ao conectar: {e}")


# 2. Resumo/Métricas de Evolução
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Pedidos", len(df))
col2.metric("Pendentes", len(df[df["Status"] == "Pendente"]))
col3.metric("Em Trânsito", len(df[df["Status"] == "Em Trânsito"]))
col4.metric("Entregues", len(df[df["Status"] == "Entregue"]))

st.divider()

# 3. Tabela Interativa para Alteração de Motorista e Status
st.subheader("Alterar Motorista e Acompanhar Status")
st.caption("Edite as colunas diretamente na tabela abaixo e clique em 'Salvar Alterações'.")

# Lista de motoristas disponíveis para o menu suspenso
motoristas_disponiveis = ["Não Atribuído", "João", "Carlos", "Ana", "Roberto"]
status_disponiveis = ["Pendente", "Em Trânsito", "Entregue", "Cancelado"]

# Tabela editável
df_editado = st.data_editor(
    df,
    column_config={
        "Motorista": st.column_config.SelectboxColumn(
            "Motorista Responsável",
            options=motoristas_disponiveis,
            required=True
        ),
        "Status": st.column_config.SelectboxColumn(
            "Status da Entrega",
            options=status_disponiveis,
            required=True
        ),
    },
    disabled=["ID_Pedido", "Cliente", "Endereço"], # Trava colunas que não devem ser alteradas
    hide_index=True,
    width='stretch'
)

# 4. Botão para Salvar as Alterações de Volta na Planilha
if st.button("💾 Salvar Alterações", type="primary"):
    conn.update(data=df_editado)
    st.success("Planilha atualizada com sucesso!")

