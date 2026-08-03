import gspread
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Entregas XDS", page_icon="🚚", layout="wide"
)

# URL da sua planilha (Formato limpo)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1xvInELpQ5BeRlNKOXQJ9xLhftv77W2bkFvSFhz10JIg/edit"

# -----------------------------------------------------------------------------
# 2. SISTEMA DE LOGIN E CONTROLE DE ACESSO
# -----------------------------------------------------------------------------
# Usuários e Perfis Mockados (Você pode mover isso para o secrets.toml no futuro)
USUARIOS = {
    "admin": {"senha": "123", "nome": "Gestor XDS", "perfil": "Admin"},
    "operador": {
        "senha": "123",
        "nome": "Operador Logístico",
        "perfil": "Operador",
    },
    "user": {"senha": "123", "nome": "Cliente / Consulta", "perfil": "Leitor"},
}


def realizar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("## 🔐 Acesso ao Sistema de Entregas")
            with st.form("login_form"):
                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                btn_login = st.form_submit_button(
                    "Entrar", use_container_width=True, type="primary"
                )

                if btn_login:
                    if (
                        usuario in USUARIOS
                        and USUARIOS[usuario]["senha"] == senha
                    ):
                        st.session_state.autenticado = True
                        st.session_state.usuario_logado = USUARIOS[usuario]
                        st.success(
                            f"Bem-vindo(a), {USUARIOS[usuario]['nome']}!"
                        )
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
        return False
    return True


if not realizar_login():
    st.stop()


# -----------------------------------------------------------------------------
# 3. CONEXÃO COM GOOGLE SHEETS VIA GSPREAD
# -----------------------------------------------------------------------------
@st.cache_resource
def conectar_gsheets():
    credentials = dict(st.secrets["connections"]["gsheets"])
    gc = gspread.service_account_from_dict(credentials)
    return gc


@st.cache_data(ttl=60)
def carregar_dados():
    gc = conectar_gsheets()
    sh = gc.open_by_url(URL_PLANILHA)
    worksheet = sh.get_worksheet(0)
    dados = worksheet.get_all_records()
    df = pd.DataFrame(dados)

    # Tratamento básico de datas se a coluna existir
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors="coerce")

    return df, worksheet


try:
    df_raw, worksheet_ref = carregar_dados()
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 4. SIDEBAR - PERFIL DO USUÁRIO & REFRESH
# -----------------------------------------------------------------------------
perfil_user = st.session_state.usuario_logado

st.sidebar.title("👤 Usuário Logado")
st.sidebar.info(
    f"**Nome:** {perfil_user['nome']}\n\n**Perfil:** {perfil_user['perfil']}"
)

if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🚪 Sair / Logout"):
    st.session_state.autenticado = False
    st.rerun()

# -----------------------------------------------------------------------------
# 5. BARRA DE FILTROS MULTI-CRITÉRIO
# -----------------------------------------------------------------------------
st.title("🚚 Acompanhamento Operacional de Entregas")

with st.expander("🔍 **Painel de Filtros Avançados**", expanded=True):
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    # Filtro de Cliente
    clientes = (
        ["Todos"] + list(df_raw["Cliente"].unique())
        if "Cliente" in df_raw.columns
        else ["Todos"]
    )
    cliente_sel = f_col1.selectbox("Cliente", clientes)

    # Filtro de Motorista
    motoristas = (
        ["Todos"] + list(df_raw["Motorista"].unique())
        if "Motorista" in df_raw.columns
        else ["Todos"]
    )
    motorista_sel = f_col2.selectbox("Motorista", motoristas)

    # Filtro de Status
    status_list = (
        ["Todos"] + list(df_raw["Status"].unique())
        if "Status" in df_raw.columns
        else ["Todos"]
    )
    status_sel = f_col3.selectbox("Status", status_list)

    # Filtro de Ocorrência (se a coluna existir na planilha)
    ocorrencias = (
        ["Todas"] + list(df_raw["Ocorrência"].unique())
        if "Ocorrência" in df_raw.columns
        else ["Todas"]
    )
    ocorrencia_sel = f_col4.selectbox("Ocorrência", ocorrencias)

# Aplicação dos Filtros
df_filtrado = df_raw.copy()

if cliente_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Cliente"] == cliente_sel]
if motorista_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Motorista"] == motorista_sel]
if status_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status"] == status_sel]
if ocorrencia_sel != "Todas" and "Ocorrência" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Ocorrência"] == ocorrencia_sel]

# -----------------------------------------------------------------------------
# 6. ESTRUTURA EM ABAS (TABS)
# -----------------------------------------------------------------------------
tab_visao_geral, tab_operacao, tab_analises = st.tabs(
    ["📊 Visão Geral & Métricas", "✏️ Gestão Operacional", "📈 Indicadores"]
)

# -----------------------------------------------------------------------------
# ABA 1: VISÃO GERAL
# -----------------------------------------------------------------------------
with tab_visao_geral:
    # Métricas Dinâmicas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Pedidos", len(df_filtrado))
    m2.metric(
        "Pendentes",
        len(df_filtrado[df_filtrado["Status"] == "Pendente"])
        if "Status" in df_filtrado.columns
        else 0,
    )
    m3.metric(
        "Em Trânsito",
        len(df_filtrado[df_filtrado["Status"] == "Em Trânsito"])
        if "Status" in df_filtrado.columns
        else 0,
    )
    m4.metric(
        "Entregues",
        len(df_filtrado[df_filtrado["Status"] == "Entregue"])
        if "Status" in df_filtrado.columns
        else 0,
    )

    st.divider()
    st.subheader("📋 Tabela Consolidada de Entregas")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ABA 2: EDITAR & ATUALIZAR STATUS (Apenas Admin/Operador)
# -----------------------------------------------------------------------------
with tab_operacao:
    st.subheader("✏️ Atualização Direta de Status e Motoristas")

    if perfil_user["perfil"] == "Leitor":
        st.warning(
            "🔒 Seu perfil de acesso (Leitor) permite apenas a visualização de dados."
        )
    else:
        st.caption(
            "Altere os valores na tabela abaixo e clique em 'Salvar na NFe/Planilha'."
        )

        motoristas_op = ["Não Atribuído", "João", "Carlos", "Ana", "Roberto"]
        status_op = ["Pendente", "Em Trânsito", "Entregue", "Cancelado"]

        col_config = {}
        if "Motorista" in df_filtrado.columns:
            col_config["Motorista"] = st.column_config.SelectboxColumn(
                "Motorista Responsável", options=motoristas_op, required=True
            )
        if "Status" in df_filtrado.columns:
            col_config["Status"] = st.column_config.SelectboxColumn(
                "Status da Entrega", options=status_op, required=True
            )

        # Editor interativo
        df_editado = st.data_editor(
            df_filtrado,
            column_config=col_config,
            disabled=[
                col
                for col in df_filtrado.columns
                if col not in ["Motorista", "Status", "Ocorrência"]
            ],
            hide_index=True,
            use_container_width=True,
            key="editor_operacional",
        )

        if st.button("💾 Salvar Alterações na Nuvem", type="primary"):
            try:
                # Atualiza a planilha mantendo o cabeçalho
                # Mescla as alterações do filtro de volta no dataframe base
                df_raw.update(df_editado)

                # Prepara os dados para salvar de volta no gspread
                dados_atualizados = [df_raw.columns.values.tolist()] + df_raw.astype(
                    str
                ).values.tolist()
                worksheet_ref.clear()
                worksheet_ref.update("A1", dados_atualizados)

                st.success("✅ Planilha atualizada com sucesso no Google Sheets!")
                st.cache_data.clear()
            except Exception as err:
                st.error(f"Erro ao salvar alterações: {err}")

# -----------------------------------------------------------------------------
# ABA 3: INDICADORES VISUAIS
# -----------------------------------------------------------------------------
with tab_analises:
    st.subheader("📊 Indicadores de Desempenho")

    if len(df_filtrado) > 0:
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("##### Status das Entregas")
            st.bar_chart(df_filtrado["Status"].value_counts())

        with c2:
            st.markdown("##### Atribuição por Motorista")
            if "Motorista" in df_filtrado.columns:
                st.bar_chart(df_filtrado["Motorista"].value_counts())
    else:
        st.info("Nenhum dado encontrado para os filtros selecionados.")