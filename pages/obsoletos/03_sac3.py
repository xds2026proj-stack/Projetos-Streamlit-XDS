import gspread
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Torre de Controle Logística | XDS",
    page_icon="🚚",
    layout="wide",
)

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1xvInELpQ5BeRlNKOXQJ9xLhftv77W2bkFvSFhz10JIg/edit"

# -----------------------------------------------------------------------------
# 2. SISTEMA DE LOGIN E CONTROLE DE ACESSO
# -----------------------------------------------------------------------------
USUARIOS = {
    "admin": {"senha": "123", "nome": "Gestor XDS", "perfil": "Admin"},
    "operador": {
        "senha": "123",
        "nome": "Operador Logístico",
        "perfil": "Operador",
    },
    "user": {"senha": "123", "nome": "Consulta / Cliente", "perfil": "Leitor"},
}


def realizar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("## 🔐 Torre de Controle Logística")
            with st.form("login_form"):
                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", width="stretch", type="primary"):
                    if (
                        usuario in USUARIOS
                        and USUARIOS[usuario]["senha"] == senha
                    ):
                        st.session_state.autenticado = True
                        st.session_state.usuario_logado = USUARIOS[usuario]
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
    return gspread.service_account_from_dict(credentials)


@st.cache_data(ttl=60)
def carregar_dados():
    gc = conectar_gsheets()
    sh = gc.open_by_url(URL_PLANILHA)

    # 1. Carrega dados de Entregas (Aba Principal)
    ws_entregas = sh.get_worksheet(0)
    df_entregas = pd.DataFrame(ws_entregas.get_all_records())

    # 2. Carrega Cadastro de Motoristas (Aba 'Motoristas' ou 'Frota')
    motoristas_ativos = ["Não Atribuído"]
    try:
        ws_motoristas = sh.worksheet("Motoristas")
        df_mot = pd.DataFrame(ws_motoristas.get_all_records())

        # Filtra apenas quem está 'Ativo'
        if "Status" in df_mot.columns:
            df_mot = df_mot[
                df_mot["Status"].astype(str).str.upper() == "ATIVO"
            ]

        # Monta a lista "Nome - Placa" se existir a coluna Placa
        if "Nome" in df_mot.columns and "Placa" in df_mot.columns:
            motoristas_ativos += (
                df_mot["Nome"] + " (" + df_mot["Placa"] + ")"
            ).tolist()
        elif "Nome" in df_mot.columns:
            motoristas_ativos += df_mot["Nome"].tolist()
    except Exception:
        # Fallback caso a aba 'Motoristas' ainda não tenha sido criada na planilha
        motoristas_ativos += ["João", "Carlos", "Ana", "Roberto"]

    return df_entregas, ws_entregas, motoristas_ativos


try:
    df_raw, ws_ref, lista_motoristas = carregar_dados()
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 4. SIDEBAR - USUÁRIO E AÇÕES
# -----------------------------------------------------------------------------
perfil_user = st.session_state.usuario_logado

st.sidebar.markdown(f"### 👤 {perfil_user['nome']}")
st.sidebar.caption(f"Perfil: **{perfil_user['perfil']}**")

st.sidebar.divider()
if st.sidebar.button("🔄 Atualizar Dados", width="stretch"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🚪 Sair", width="stretch"):
    st.session_state.autenticado = False
    st.rerun()

# -----------------------------------------------------------------------------
# 5. HEADER & FILTROS OPERACIONAIS
# -----------------------------------------------------------------------------
st.title("🚚 Gestão Operacional de Entregas")

with st.container(border=True):
    st.markdown("### 🔍 Filtros de Consulta Operacional")
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)

    # 1. Filtro por Carga
    cargas = (
        ["Todas"] + sorted(list(df_raw["Carga"].dropna().unique()))
        if "Carga" in df_raw.columns
        else ["Todas"]
    )
    carga_sel = f_col1.selectbox("📦 Carga / Manifesto", cargas)

    # 2. Filtro por Cliente
    clientes = (
        ["Todos"] + sorted(list(df_raw["Cliente"].dropna().unique()))
        if "Cliente" in df_raw.columns
        else ["Todos"]
    )
    cliente_sel = f_col2.selectbox("🏢 Cliente", clientes)

    # 3. Filtro por Motorista
    motoristas_filtro = (
        ["Todos"] + sorted(list(df_raw["Motorista"].dropna().unique()))
        if "Motorista" in df_raw.columns
        else ["Todos"]
    )
    motorista_sel = f_col3.selectbox("🚛 Motorista", motoristas_filtro)

    # 4. Filtro por Status
    status_list = (
        ["Todos"] + sorted(list(df_raw["Status"].dropna().unique()))
        if "Status" in df_raw.columns
        else ["Todos"]
    )
    status_sel = f_col4.selectbox("📌 Status", status_list)

    # 5. Filtro por Ocorrência
    ocorrencias = (
        ["Todas"] + sorted(list(df_raw["Ocorrência"].dropna().unique()))
        if "Ocorrência" in df_raw.columns
        else ["Todas"]
    )
    ocorrencia_sel = f_col5.selectbox("⚠️ Ocorrência", ocorrencias)

# Aplicação dos Filtros
df_filtrado = df_raw.copy()

if carga_sel != "Todas" and "Carga" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Carga"] == carga_sel]
if cliente_sel != "Todos" and "Cliente" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Cliente"] == cliente_sel]
if motorista_sel != "Todos" and "Motorista" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Motorista"] == motorista_sel]
if status_sel != "Todos" and "Status" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Status"] == status_sel]
if ocorrencia_sel != "Todas" and "Ocorrência" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Ocorrência"] == ocorrencia_sel]

# -----------------------------------------------------------------------------
# 6. ESTRUTURA DE ABAS
# -----------------------------------------------------------------------------
tab_geral, tab_operacao, tab_kpi_log, tab_kpi_fin = st.tabs([
    "📋 Visão Geral",
    "✏️ Ações na Carga/Operação",
    "📊 Nível de Serviço (OTD/OTIF)",
    "💰 Indicadores Financeiros",
])

# -----------------------------------------------------------------------------
# ABA 1: VISÃO GERAL DE ENTREGAS
# -----------------------------------------------------------------------------
with tab_geral:
    st.markdown("#### 📈 Visão Consolidada")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    total_pedidos = len(df_filtrado)
    pendentes = (
        len(df_filtrado[df_filtrado["Status"] == "Pendente"])
        if "Status" in df_filtrado.columns
        else 0
    )
    em_transito = (
        len(df_filtrado[df_filtrado["Status"] == "Em Trânsito"])
        if "Status" in df_filtrado.columns
        else 0
    )
    entregues = (
        len(df_filtrado[df_filtrado["Status"] == "Entregue"])
        if "Status" in df_filtrado.columns
        else 0
    )
    com_ocorrencia = (
        len(
            df_filtrado[
                (df_filtrado["Ocorrência"].notna())
                & (df_filtrado["Ocorrência"] != "")
                & (df_filtrado["Ocorrência"] != "Nenhuma")
            ]
        )
        if "Ocorrência" in df_filtrado.columns
        else 0
    )

    kpi1.metric("Total de Pedidos", total_pedidos)
    kpi2.metric("Pendentes", pendentes)
    kpi3.metric("Em Trânsito", em_transito)
    kpi4.metric("Entregues", entregues)
    kpi5.metric("Com Ocorrência", com_ocorrencia)

    st.divider()
    st.dataframe(df_filtrado, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# ABA 2: AÇÕES NA CARGA / OPERAÇÃO
# -----------------------------------------------------------------------------
with tab_operacao:
    st.markdown("#### ⚡ Atualização de Motoristas, Status e Ocorrências")

    if perfil_user["perfil"] == "Leitor":
        st.warning(
            "🔒 Seu perfil de acesso permite apenas visualização dos dados."
        )
    else:
        if carga_sel != "Todas":
            st.info(
                f"🎯 **Editando exclusivamente os dados da Carga:** `{carga_sel}`"
            )

        status_op = ["Pendente", "Em Trânsito", "Entregue", "Cancelado"]
        ocorrencias_op = [
            "Nenhuma",
            "Avaria",
            "Atraso",
            "Cliente Ausente",
            "Devolução",
            "Endereço Não Localizado",
        ]

        col_config = {}
        if "Motorista" in df_filtrado.columns:
            col_config["Motorista"] = st.column_config.SelectboxColumn(
                "Motorista (Veículo)", options=lista_motoristas, required=True
            )
        if "Status" in df_filtrado.columns:
            col_config["Status"] = st.column_config.SelectboxColumn(
                "Status", options=status_op, required=True
            )
        if "Ocorrência" in df_filtrado.columns:
            col_config["Ocorrência"] = st.column_config.SelectboxColumn(
                "Ocorrência Operacional", options=ocorrencias_op
            )

        df_editado = st.data_editor(
            df_filtrado,
            column_config=col_config,
            disabled=[
                col
                for col in df_filtrado.columns
                if col not in ["Motorista", "Status", "Ocorrência", "Observações"]
            ],
            hide_index=True,
            width="stretch",
            key="editor_cargas",
        )

        if st.button("💾 Salvar Alterações na Nuvem", type="primary"):
            try:
                # 1. Atualiza o DataFrame geral com as alterações feitas na tela
                df_raw.update(df_editado)

                # 2. Converte o DataFrame atualizado em uma lista de listas (Matriz)
                matriz_dados = [df_raw.columns.tolist()] + df_raw.astype(
                    str
                ).values.tolist()

                # 3. Limpa a aba e atualiza usando o método seguro
                ws_ref.clear()
                ws_ref.update(matriz_dados)  # Passando apenas a matriz de dados

                st.success("✅ Alterações salvas com sucesso no Google Sheets!")
                st.cache_data.clear()

            except Exception as err:
                st.error(f"Erro ao salvar: {err}")

# -----------------------------------------------------------------------------
# ABA 3: NÍVEL DE SERVIÇO (OTD / OTIF / AVARIAS)
# -----------------------------------------------------------------------------
with tab_kpi_log:
    st.markdown("#### 🎯 Indicadores de Nível de Serviço (SGI & Qualidade)")

    if len(df_filtrado) > 0:
        # Cálculos de OTD e OTIF
        total = len(df_filtrado)

        # OTD: Entregas realizadas dentro do prazo
        no_prazo = (
            len(df_filtrado[df_filtrado["No_Prazo"].astype(str).str.upper() == "SIM"])
            if "No_Prazo" in df_filtrado.columns
            else entregues
        )
        otd = (no_prazo / total * 100) if total > 0 else 0

        # OTIF: No prazo E Sem Ocorrências/Avarias
        sem_avaria = (
            len(
                df_filtrado[
                    (df_filtrado["Ocorrência"] == "Nenhuma")
                    | (df_filtrado["Ocorrência"] == "")
                    | (df_filtrado["Ocorrência"].isna())
                ]
            )
            if "Ocorrência" in df_filtrado.columns
            else total
        )
        otif = (
            (len(df_filtrado[(df_filtrado["Status"] == "Entregue") & (df_filtrado["No_Prazo"].astype(str).str.upper() == "SIM") & ((df_filtrado["Ocorrência"] == "Nenhuma") | (df_filtrado["Ocorrência"] == ""))]) / total * 100)
            if "No_Prazo" in df_filtrado.columns and "Ocorrência" in df_filtrado.columns
            else otd
        )

        # Avarias
        avarias = (
            len(df_filtrado[df_filtrado["Ocorrência"] == "Avaria"])
            if "Ocorrência" in df_filtrado.columns
            else 0
        )
        taxa_avaria = (avarias / total * 100) if total > 0 else 0

        col_otd, col_otif, col_avaria = st.columns(3)
        col_otd.metric("OTD (On-Time Delivery)", f"{otd:.1f}%")
        col_otif.metric("OTIF (On-Time In-Full)", f"{otif:.1f}%")
        col_avaria.metric("Índice de Avarias", f"{taxa_avaria:.1f}%")

        st.divider()
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            st.markdown("##### Entregas por Status")
            st.bar_chart(df_filtrado["Status"].value_counts())
        with c_chart2:
            st.markdown("##### Ocorrências Operacionais")
            if "Ocorrência" in df_filtrado.columns:
                st.bar_chart(df_filtrado["Ocorrência"].value_counts())
    else:
        st.info("Nenhum dado selecionado.")

# -----------------------------------------------------------------------------
# ABA 4: FINANCEIRO & CONTROLADORIA (MOCK DE PREPARAÇÃO)
# -----------------------------------------------------------------------------
with tab_kpi_fin:
    st.markdown("#### 💰 Visão Financeira e Custos de Operação")

    # Tratamento de colunas financeiras (se existirem na planilha)
    frete_receber = (
        df_filtrado["Frete_Receber"].sum()
        if "Frete_Receber" in df_filtrado.columns
        else 0.0
    )
    frete_pagar = (
        df_filtrado["Frete_Pagar"].sum()
        if "Frete_Pagar" in df_filtrado.columns
        else 0.0
    )
    custo_diesel = (
        df_filtrado["Custo_Diesel"].sum()
        if "Custo_Diesel" in df_filtrado.columns
        else 0.0
    )
    margem = frete_receber - (frete_pagar + custo_diesel)

    f1, f2, f3, f4 = st.columns(4)
    f1.metric(
        "Fretes a Receber",
        f"R$ {frete_receber:,.2f}",
        help="Coluna 'Frete_Receber' na planilha",
    )
    f2.metric(
        "Fretes a Pagar (Terceiros)",
        f"R$ {frete_pagar:,.2f}",
        help="Coluna 'Frete_Pagar' na planilha",
    )
    f3.metric(
        "Custo Est. Diesel",
        f"R$ {custo_diesel:,.2f}",
        help="Coluna 'Custo_Diesel' na planilha",
    )
    f4.metric(
        "Margem Bruta Est.",
        f"R$ {margem:,.2f}",
        delta=f"{(margem/frete_receber*100) if frete_receber > 0 else 0:.1f}%",
    )

    st.divider()
    st.caption(
        "💡 *Dica:* Adicione as colunas `Frete_Receber`, `Frete_Pagar`, `Custo_Diesel` e `No_Prazo` na sua planilha para alimentar automaticamente estes indicadores em tempo real."
    )