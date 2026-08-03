import datetime
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

RESPONSABILIDADE_PADRAO = {
    "Nenhuma": "N/A",
    "Avaria": "Transportadora",
    "Atraso": "Transportadora",
    "Extravio": "Transportadora",
    "Cliente Ausente": "Cliente",
    "Devolução": "Cliente",
    "Endereço Não Localizado": "Cliente",
    "Recusa Comercial": "Cliente",
}

COLUNAS_OPERACIONAIS = [
    "Carga",
    "NF",
    "Cliente_XDS",
    "Motorista",
    "Status",
    "Ocorrência",
    "Responsavel_Ocorrencia",
    "Observações",
    "Local",
    "Periodo de entrega",
    "Nome do Recebedor",
    "CEP", "Bairro",
    "Custo Diesel",
]

COLUNAS_FINANCEIRAS = [
    "Frete_Receber",
    "Adicional_Receber",
    "Frete_Pagar",
    "Adicional_Pagar",
    "Custo_Diesel",
    "Status_Adicional_Receber",
    "Status_Adicional_Pagar",
    "Fatura_Receber_ID",
    "Status_Faturamento_Receber",
    "Fatura_Pagar_ID",
    "Status_Faturamento_Pagar",
]

# -----------------------------------------------------------------------------
# 2. CONTROLE DE TEMAS DE CORES
# -----------------------------------------------------------------------------
TEMAS = {
    "🔴 Vermelho Corporativo": {
        "primary": "#E63946",
        "secondary": "#2B1E22",
        "hover": "#D62828",
        "bg_card": "#1E1F2B",
    },
    "🔵 Azul Corporativo": {
        "primary": "#1E88E5",
        "secondary": "#1E2B37",
        "hover": "#1565C0",
        "bg_card": "#1E222B",
    },
    "🟢 Verde Logística": {
        "primary": "#2E7D32",
        "secondary": "#1E2B20",
        "hover": "#1B5E20",
        "bg_card": "#1E2820",
    },
    "🟠 Laranja Operacional": {
        "primary": "#E65100",
        "secondary": "#2B241E",
        "hover": "#BF360C",
        "bg_card": "#2B221E",
    },
    "🟣 Roxo Moderno": {
        "primary": "#7B1FA2",
        "secondary": "#281E2B",
        "hover": "#4A148C",
        "bg_card": "#251E2B",
    },
}

if "tema_selecionado" not in st.session_state:
    st.session_state.tema_selecionado = "🔴 Vermelho Corporativo"

# -----------------------------------------------------------------------------
# 3. CONTROLE DE ACESSO
# -----------------------------------------------------------------------------
USUARIOS = {
    "admin": {
        "senha": "123",
        "nome": "Gestor XDS",
        "perfil": "Admin",
        "acesso_financeiro": True,
    },
    "operador": {
        "senha": "123",
        "nome": "Operador Logístico",
        "perfil": "Operador",
        "acesso_financeiro": False,
    },
    "financeiro": {
        "senha": "123",
        "nome": "Analista Financeiro",
        "perfil": "Financeiro",
        "acesso_financeiro": True,
    },
    "user": {
        "senha": "123",
        "nome": "Consulta / Cliente",
        "perfil": "Leitor",
        "acesso_financeiro": False,
    },
}


def realizar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("## 🔐 XDS | Torre de Controle Logística")
            with st.form("login_form"):
                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button(
                    "Entrar", use_container_width=True, type="primary"
                ):
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
# 4. ESTILO CUSTOMIZADO
# -----------------------------------------------------------------------------
cor_tema = TEMAS[st.session_state.tema_selecionado]

st.markdown(
    f"""
    <style>
        div.stButton > button[kind="primary"] {{
            background-color: {cor_tema['primary']} !important;
            border-color: {cor_tema['primary']} !important;
            color: white !important;
            font-weight: bold;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background-color: {cor_tema['hover']} !important;
            border-color: {cor_tema['hover']} !important;
            transform: translateY(-2px);
        }}
        button[data-baseweb="tab"] [data-testid="stMarkdownContainer"] p {{
            font-size: 1.05rem;
            font-weight: 600;
        }}
        button[aria-selected="true"] {{
            border-bottom-color: {cor_tema['primary']} !important;
        }}
        button[aria-selected="true"] [data-testid="stMarkdownContainer"] p {{
            color: {cor_tema['primary']} !important;
        }}
        .kpi-card {{
            background-color: {cor_tema['secondary']};
            border-left: 5px solid {cor_tema['primary']};
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            margin-bottom: 10px;
        }}
        .kpi-title {{
            font-size: 0.85rem;
            color: #AAA;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .kpi-value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #FFF;
        }}
    </style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 5. CARREGAMENTO E SALVAMENTO DE DADOS
# -----------------------------------------------------------------------------
def obter_cliente_gspread():
    credentials = dict(st.secrets["connections"]["gsheets"])
    return gspread.service_account_from_dict(credentials)


@st.cache_data(ttl=60)
def carregar_dados():
    gc = obter_cliente_gspread()
    sh = gc.open_by_url(URL_PLANILHA)

    ws_entregas = sh.get_worksheet(0)
    dados_entregas = ws_entregas.get_all_records()
    df_entregas = pd.DataFrame(dados_entregas)

    colunas_necessarias = (
        COLUNAS_OPERACIONAIS + COLUNAS_FINANCEIRAS + ["Data_Envio"]
    )
    for col in colunas_necessarias:
        if col not in df_entregas.columns:
            if col in [
                "Frete_Receber",
                "Adicional_Receber",
                "Frete_Pagar",
                "Adicional_Pagar",
                "Custo_Diesel",
            ]:
                df_entregas[col] = 0.0
            elif col in [
                "Status_Adicional_Receber",
                "Status_Adicional_Pagar",
            ]:
                df_entregas[col] = "Pendente"
            elif col in [
                "Status_Faturamento_Receber",
                "Status_Faturamento_Pagar",
            ]:
                df_entregas[col] = "A Faturar"
            elif col in ["Fatura_Receber_ID", "Fatura_Pagar_ID"]:
                df_entregas[col] = ""
            elif col == "Data_Envio":
                df_entregas[col] = datetime.date.today().strftime("%Y-%m-%d")
            else:
                df_entregas[col] = ""

    cols_numericas = [
        "Frete_Receber",
        "Adicional_Receber",
        "Frete_Pagar",
        "Adicional_Pagar",
        "Custo_Diesel",
    ]
    for col in cols_numericas:
        df_entregas[col] = (
            pd.to_numeric(
                df_entregas[col].astype(str).str.replace(",", "."),
                errors="coerce",
            )
            .fillna(0.0)
            .astype(float)
        )

    df_entregas["Data_Envio_dt"] = pd.to_datetime(
        df_entregas["Data_Envio"], errors="coerce"
    )

    motoristas_ativos = ["Manter Atual / Não Alterar", "Não Atribuído"]
    try:
        ws_motoristas = sh.worksheet("Motoristas")
        df_mot = pd.DataFrame(ws_motoristas.get_all_records())
        if "Status" in df_mot.columns:
            df_mot = df_mot[
                df_mot["Status"].astype(str).str.upper() == "ATIVO"
            ]
        if "Nome" in df_mot.columns:
            motoristas_ativos += df_mot["Nome"].tolist()
    except Exception:
        motoristas_ativos += ["João", "Carlos", "Ana", "Roberto"]

    return df_entregas, motoristas_ativos


try:
    df_raw, lista_motoristas = carregar_dados()
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    st.stop()


def salvar_dados_na_planilha(df_para_salvar):
    gc = obter_cliente_gspread()
    sh = gc.open_by_url(URL_PLANILHA)
    worksheet = sh.get_worksheet(0)

    df_gravar = df_para_salvar.copy()
    if "Data_Envio_dt" in df_gravar.columns:
        df_gravar = df_gravar.drop(columns=["Data_Envio_dt"])

    df_limpo = df_gravar.fillna("").astype(str)
    matriz = [df_limpo.columns.tolist()] + df_limpo.values.tolist()

    worksheet.clear()
    worksheet.update(matriz)


# PERMISSÕES DE PERFIL
usuario_atual = st.session_state.usuario_logado
tem_acesso_financeiro = usuario_atual.get("acesso_financeiro", False)

if tem_acesso_financeiro:
    colunas_permitidas = [
        c
        for c in df_raw.columns
        if c in COLUNAS_OPERACIONAIS + COLUNAS_FINANCEIRAS or c == "Data_Envio"
    ]
else:
    colunas_permitidas = [
        c
        for c in df_raw.columns
        if c
        in COLUNAS_OPERACIONAIS
        + ["Adicional_Receber", "Adicional_Pagar", "Data_Envio"]
    ]

# -----------------------------------------------------------------------------
# 6. SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.markdown(f"### 👤 {usuario_atual['nome']}")
st.sidebar.caption(f"Perfil: **{usuario_atual['perfil']}**")

st.sidebar.divider()
st.sidebar.markdown("🎨 **Aparência do Sistema**")
novo_tema = st.sidebar.selectbox(
    "Cor do Tema:",
    list(TEMAS.keys()),
    index=list(TEMAS.keys()).index(st.session_state.tema_selecionado),
)

if novo_tema != st.session_state.tema_selecionado:
    st.session_state.tema_selecionado = novo_tema
    st.rerun()

st.sidebar.divider()
if tem_acesso_financeiro:
    st.sidebar.success("🔒 Acesso Financeiro Habilitado")
else:
    st.sidebar.info("👁️ Visão Operacional")

if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🚪 Sair", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

# -----------------------------------------------------------------------------
# 7. FILTROS DE CONSULTA
# -----------------------------------------------------------------------------
st.title("🚚 Torre de Controle Logística")

with st.container(border=True):
    st.markdown("### 🔍 Filtros de Pesquisa e Intervalo")

    d_col1, d_col2 = st.columns(2)
    data_min = (
        df_raw["Data_Envio_dt"].min().date()
        if pd.notna(df_raw["Data_Envio_dt"].min())
        else datetime.date.today()
    )
    data_max = (
        df_raw["Data_Envio_dt"].max().date()
        if pd.notna(df_raw["Data_Envio_dt"].max())
        else datetime.date.today()
    )

    data_inicio = d_col1.date_input("🗓️ Data Inicial", value=data_min)
    data_fim = d_col2.date_input("🗓️ Data Final", value=data_max)

    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)

    cargas = (
        ["Todas"] + sorted(list(df_raw["Carga"].astype(str).unique()))
        if "Carga" in df_raw.columns
        else ["Todas"]
    )
    carga_sel = f_col1.selectbox("📦 Carga / Manifesto", cargas)

    clientes = (
        ["Todos"] + sorted(list(df_raw["Cliente_XDS"].astype(str).unique()))
        if "Cliente_XDS" in df_raw.columns
        else ["Todos"]
    )
    cliente_sel = f_col2.selectbox("🏢 Cliente_XDS", clientes)

    motoristas_filtro = (
        ["Todos"] + sorted(list(df_raw["Motorista"].astype(str).unique()))
        if "Motorista" in df_raw.columns
        else ["Todos"]
    )
    motorista_sel = f_col3.selectbox("🚛 Motorista", motoristas_filtro)

    status_list = (
        ["Todos"] + sorted(list(df_raw["Status"].astype(str).unique()))
        if "Status" in df_raw.columns
        else ["Todos"]
    )
    status_sel = f_col4.selectbox("📌 Status Operacional", status_list)

    ocorrencias = (
        ["Todas"] + sorted(list(df_raw["Ocorrência"].astype(str).unique()))
        if "Ocorrência" in df_raw.columns
        else ["Todas"]
    )
    ocorrencia_sel = f_col5.selectbox("⚠️ Ocorrência", ocorrencias)

# Aplicação dos Filtros
df_filtrado = df_raw.copy()

if "Data_Envio_dt" in df_filtrado.columns:
    mask_data = (df_filtrado["Data_Envio_dt"].dt.date >= data_inicio) & (
        df_filtrado["Data_Envio_dt"].dt.date <= data_fim
    )
    df_filtrado = df_filtrado[mask_data]

if carga_sel != "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["Carga"].astype(str) == str(carga_sel)
    ]
if cliente_sel != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["Cliente_XDS"].astype(str) == str(cliente_sel)
    ]
if motorista_sel != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["Motorista"].astype(str) == str(motorista_sel)
    ]
if status_sel != "Todos":
    df_filtrado = df_filtrado[
        df_filtrado["Status"].astype(str) == str(status_sel)
    ]
if ocorrencia_sel != "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["Ocorrência"].astype(str) == str(ocorrencia_sel)
    ]


def criar_card_kpi(coluna, titulo, valor):
    coluna.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{titulo}</div>
            <div class="kpi-value">{valor}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 8. ESTRUTURA DE ABAS
# -----------------------------------------------------------------------------
abas_lista = [
    "📋 Visão Geral",
    "⚡ Operação & Edição",
    "📊 SGI: OTD / Ocorrências",
]
if tem_acesso_financeiro:
    abas_lista.append("💳 Homologação de Adicionais")
    abas_lista.append("📄 Faturamento (Contas a Pagar / Receber)")
    abas_lista.append("💰 Controladoria & DRE")

aba_objs = st.tabs(abas_lista)

# -----------------------------------------------------------------------------
# ABA 1: VISÃO GERAL
# -----------------------------------------------------------------------------
with aba_objs[0]:
    st.markdown("#### 📈 Visão Consolidada de Pedidos")

    k1, k2, k3, k4, k5 = st.columns(5)
    criar_card_kpi(k1, "Total no Filtro", len(df_filtrado))
    criar_card_kpi(
        k2, "Pendentes", len(df_filtrado[df_filtrado["Status"] == "Pendente"])
    )
    criar_card_kpi(
        k3,
        "Em Trânsito",
        len(df_filtrado[df_filtrado["Status"] == "Em Trânsito"]),
    )
    criar_card_kpi(
        k4, "Entregues", len(df_filtrado[df_filtrado["Status"] == "Entregue"])
    )

    total_oc = len(
        df_filtrado[
            (df_filtrado["Ocorrência"].notna())
            & (df_filtrado["Ocorrência"] != "")
            & (df_filtrado["Ocorrência"] != "Nenhuma")
        ]
    )
    criar_card_kpi(k5, "Com Ocorrência", total_oc)

    st.divider()
    st.dataframe(
        df_filtrado[colunas_permitidas],
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------------------------------------------------------
# ABA 2: OPERAÇÃO EM LOTE + EDIÇÃO TABULAR
# -----------------------------------------------------------------------------
with aba_objs[1]:
    if usuario_atual["perfil"] == "Leitor":
        st.warning("🔒 Seu perfil permite apenas visualização dos dados.")
    else:
        with st.container(border=True):
            st.markdown("### ⚡ Ação Operacional em Lote")

            c_lote1, c_lote2, c_lote3 = st.columns([2, 2, 2])

            status_op = [
                "Manter Atual / Não Alterar",
                "Pendente",
                "Em Trânsito",
                "Entregue",
                "Cancelado",
            ]
            ocorrencias_op = [
                "Manter Atual / Não Alterar",
                "Nenhuma",
                "Avaria",
                "Atraso",
                "Cliente Ausente",
                "Devolução",
                "Endereço Não Localizado",
            ]
            resp_op = [
                "Automático pelo Tipo",
                "Transportadora",
                "Cliente",
                "N/A",
            ]

            novo_mot = c_lote1.selectbox(
                "🚛 Atribuir Motorista", lista_motoristas
            )
            novo_status = c_lote2.selectbox("📌 Atribuir Status", status_op)
            nova_ocorrencia = c_lote3.selectbox(
                "⚠️ Atribuir Ocorrência", ocorrencias_op
            )

            c_lote4, c_lote5, c_lote6 = st.columns([2, 2, 2])
            nova_resp = c_lote4.selectbox("👤 Responsabilidade", resp_op)

            escopo_aplicacao = c_lote5.radio(
                "🎯 Escopo da Alteração:",
                ["Apenas Linhas Filtradas", "Toda a Carga Selecionada"],
                horizontal=True,
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if c_lote6.button(
                "🚀 Aplicar Alteração em Lote",
                type="primary",
                use_container_width=True,
            ):
                if len(df_filtrado) == 0:
                    st.error("Nenhum pedido selecionado nos filtros atuais.")
                else:
                    if (
                        escopo_aplicacao == "Toda a Carga Selecionada"
                        and carga_sel != "Todas"
                    ):
                        indices_alvo = df_raw[
                            df_raw["Carga"].astype(str) == str(carga_sel)
                        ].index
                    else:
                        indices_alvo = df_filtrado.index

                    if novo_mot != "Manter Atual / Não Alterar":
                        df_raw.loc[indices_alvo, "Motorista"] = novo_mot
                    if novo_status != "Manter Atual / Não Alterar":
                        df_raw.loc[indices_alvo, "Status"] = novo_status
                    if nova_ocorrencia != "Manter Atual / Não Alterar":
                        df_raw.loc[indices_alvo, "Ocorrência"] = nova_ocorrencia
                        df_raw.loc[indices_alvo, "Responsavel_Ocorrencia"] = (
                            RESPONSABILIDADE_PADRAO.get(nova_ocorrencia, "N/A")
                            if nova_resp == "Automático pelo Tipo"
                            else nova_resp
                        )

                    try:
                        with st.spinner("Gravando alterações na nuvem..."):
                            salvar_dados_na_planilha(df_raw)

                        st.success(
                            f"✅ {len(indices_alvo)} pedido(s) atualizado(s) com sucesso!"
                        )
                        st.cache_data.clear()
                    except Exception as err:
                        st.error(f"Erro ao salvar alteração em lote: {err}")

        st.divider()

        st.markdown(
            "### ✏️ Edição Fina Line-by-Line (Tabela de Dados Filtrada)"
        )
        st.info(
            "💡 **Aviso:** Alterações em Adicionais entram automaticamente como **'Pendente'** para homologação do Financeiro."
        )

        col_config = {}
        if "Motorista" in df_filtrado.columns:
            col_config["Motorista"] = st.column_config.SelectboxColumn(
                "Motorista",
                options=[
                    m
                    for m in lista_motoristas
                    if m != "Manter Atual / Não Alterar"
                ],
            )
        if "Status" in df_filtrado.columns:
            col_config["Status"] = st.column_config.SelectboxColumn(
                "Status",
                options=[
                    s for s in status_op if s != "Manter Atual / Não Alterar"
                ],
            )
        if "Ocorrência" in df_filtrado.columns:
            col_config["Ocorrência"] = st.column_config.SelectboxColumn(
                "Ocorrência",
                options=[
                    o
                    for o in ocorrencias_op
                    if o != "Manter Atual / Não Alterar"
                ],
            )

        if "Responsavel_Ocorrencia" in df_filtrado.columns:
            col_config["Responsavel_Ocorrencia"] = (
                st.column_config.SelectboxColumn(
                    "Resp. Ocorrência",
                    options=["Transportadora", "Cliente", "N/A"],
                )
            )

        df_para_editar = df_filtrado[colunas_permitidas].copy()

        # Ajuste: Libera Responsavel_Ocorrencia para ser editado manualmente!
        colunas_editaveis = [
            "Carga",
            "Motorista",
            "Status",
            "Ocorrência",
            "Responsavel_Ocorrencia",
            "Observações",
            "Adicional_Receber",
            "Adicional_Pagar",
        ]

        df_editado = st.data_editor(
            df_para_editar,
            column_config=col_config,
            disabled=[
                col
                for col in df_para_editar.columns
                if col not in colunas_editaveis
            ],
            hide_index=True,
            use_container_width=True,
            key="editor_fino_operacional",
        )

        if st.button("💾 Salvar Edição na Nuvem", type="primary"):
            try:
                with st.spinner("Atualizando planilha na nuvem..."):
                    for idx in df_editado.index:
                        # Preenchimento automático da responsabilidade se deixado em branco
                        oc_val = df_editado.loc[idx, "Ocorrência"]
                        resp_val = df_editado.loc[idx, "Responsavel_Ocorrencia"]

                        if not resp_val or resp_val == "":
                            df_editado.loc[idx, "Responsavel_Ocorrencia"] = (
                                RESPONSABILIDADE_PADRAO.get(oc_val, "N/A")
                            )

                        # Controle de status de aprovação de adicionais
                        if "Adicional_Receber" in df_editado.columns:
                            if (
                                str(df_raw.loc[idx, "Adicional_Receber"])
                                != str(df_editado.loc[idx, "Adicional_Receber"])
                            ):
                                df_raw.loc[idx, "Status_Adicional_Receber"] = (
                                    "Pendente"
                                )
                        if "Adicional_Pagar" in df_editado.columns:
                            if (
                                str(df_raw.loc[idx, "Adicional_Pagar"])
                                != str(df_editado.loc[idx, "Adicional_Pagar"])
                            ):
                                df_raw.loc[idx, "Status_Adicional_Pagar"] = (
                                    "Pendente"
                                )

                    df_raw.loc[df_editado.index, df_editado.columns] = (
                        df_editado.values
                    )
                    salvar_dados_na_planilha(df_raw)

                st.success(
                    "✅ Tabela gravada na nuvem com sucesso! As alterações foram registradas."
                )
                st.cache_data.clear()

            except Exception as err:
                st.error(f"Erro ao salvar edição fina: {err}")

# -----------------------------------------------------------------------------
# ABA 3: SGI / INDICADORES
# -----------------------------------------------------------------------------
with aba_objs[2]:
    st.markdown("#### 📊 Análise Operacional e Responsabilidade")
    if len(df_filtrado) > 0:
        df_oc = df_filtrado[
            (df_filtrado["Ocorrência"].notna())
            & (df_filtrado["Ocorrência"] != "")
            & (df_filtrado["Ocorrência"] != "Nenhuma")
        ]

        c1, c2, c3 = st.columns(3)
        criar_card_kpi(c1, "Ocorrências no Período", len(df_oc))
        criar_card_kpi(
            c2,
            "Culpa Transportadora",
            len(df_oc[df_oc["Responsavel_Ocorrencia"] == "Transportadora"]),
        )
        criar_card_kpi(
            c3,
            "Culpa Cliente",
            len(df_oc[df_oc["Responsavel_Ocorrencia"] == "Cliente"]),
        )

        st.divider()
        st.bar_chart(df_filtrado["Ocorrência"].value_counts())

# -----------------------------------------------------------------------------
# ABA 4, 5 & 6: MÓDULOS FINANCEIROS E FATURAMENTO
# -----------------------------------------------------------------------------
if tem_acesso_financeiro:

    # --- ABA 4: HOMOLOGAÇÃO DE ADICIONAIS ---
    with aba_objs[3]:
        st.markdown("### 💳 Homologação de Adicionais por Carga")
        st.caption(
            "Aprove ou rejeite os adicionais informados pela equipe operacional antes de liberá-los para faturamento."
        )

        # Agregação CORRETA: Soma dos adicionais de TODAS as linhas da Carga
        df_cargas_fin = (
            df_raw.groupby("Carga")
            .agg({
                "Cliente_XDS": "first",
                "Motorista": "first",
                "Status": "first",
                "Frete_Receber": "first",
                "Adicional_Receber": "sum",  # Soma todas as entregas!
                "Status_Adicional_Receber": "first",
                "Frete_Pagar": "first",
                "Adicional_Pagar": "sum",  # Soma todas as entregas!
                "Status_Adicional_Pagar": "first",
                "Custo_Diesel": "first",
            })
            .reset_index()
        )

        df_fin_editado = st.data_editor(
            df_cargas_fin,
            column_config={
                "Carga": st.column_config.TextColumn(
                    "Carga / Manifesto", disabled=True
                ),
                "Cliente_XDS": st.column_config.TextColumn(
                    "Cliente_XDS", disabled=True
                ),
                "Motorista": st.column_config.TextColumn(
                    "Motorista", disabled=True
                ),
                "Status": st.column_config.TextColumn("Status", disabled=True),
                "Frete_Receber": st.column_config.NumberColumn(
                    "Frete a Receber (R$)", format="R$ %.2f"
                ),
                "Adicional_Receber": st.column_config.NumberColumn(
                    "Total Adic. Receber (R$)", format="R$ %.2f"
                ),
                "Status_Adicional_Receber": st.column_config.SelectboxColumn(
                    "Validação Rec.",
                    options=["Pendente", "Aprovado", "Rejeitado"],
                ),
                "Frete_Pagar": st.column_config.NumberColumn(
                    "Frete Terceiro (R$)", format="R$ %.2f"
                ),
                "Adicional_Pagar": st.column_config.NumberColumn(
                    "Total Adic. Pagar (R$)", format="R$ %.2f"
                ),
                "Status_Adicional_Pagar": st.column_config.SelectboxColumn(
                    "Validação Pag.",
                    options=["Pendente", "Aprovado", "Rejeitado"],
                ),
                "Custo_Diesel": st.column_config.NumberColumn(
                    "Custo Diesel (R$)", format="R$ %.2f"
                ),
            },
            hide_index=True,
            use_container_width=True,
            key="editor_financeiro_carga",
        )

        if st.button(
            "💾 Homologar e Salvar Lançamentos Financeiros", type="primary"
        ):
            try:
                with st.spinner("Atualizando validações na nuvem..."):
                    for _, row in df_fin_editado.iterrows():
                        carga_id = row["Carga"]
                        mask = df_raw["Carga"].astype(str) == str(carga_id)
                        df_raw.loc[mask, "Frete_Receber"] = row["Frete_Receber"]
                        df_raw.loc[mask, "Status_Adicional_Receber"] = row[
                            "Status_Adicional_Receber"
                        ]
                        df_raw.loc[mask, "Frete_Pagar"] = row["Frete_Pagar"]
                        df_raw.loc[mask, "Status_Adicional_Pagar"] = row[
                            "Status_Adicional_Pagar"
                        ]
                        df_raw.loc[mask, "Custo_Diesel"] = row["Custo_Diesel"]

                    salvar_dados_na_planilha(df_raw)

                st.success("✅ Validações atualizadas com sucesso!")
                st.cache_data.clear()

            except Exception as e:
                st.error(f"Erro ao salvar validações financeiras: {e}")

    # --- ABA 5: FATURAMENTO (PAGAR E RECEBER) ---
    with aba_objs[4]:
        st.markdown(
            "### 📄 Gestão de Faturas e Cobranças (A Pagar / A Receber)"
        )
        st.caption(
            "Cargas homologadas são agrupadas para acompanhamento de emissão e liquidação."
        )

        tab_fat_rec, tab_fat_pag = st.tabs(
            ["📥 Contas a Receber (Cliente_XDS)", "📤 Contas a Pagar (Terceiros)"]
        )

        status_faturamento_op = [
            "A Faturar",
            "Fatura Gerada",
            "Enviado ao Cliente",
            "Pago / Recebido",
            "Cancelado",
        ]

        with tab_fat_rec:
            # Agregação com SOMA nos adicionais
            df_fat_rec = (
                df_filtrado.groupby("Carga")
                .agg({
                    "Cliente_XDS": "first",
                    "Frete_Receber": "first",
                    "Adicional_Receber": "sum",
                    "Status_Adicional_Receber": "first",
                    "Fatura_Receber_ID": "first",
                    "Status_Faturamento_Receber": "first",
                })
                .reset_index()
            )

            df_fat_rec["Total_Receber"] = df_fat_rec["Frete_Receber"] + (
                df_fat_rec["Adicional_Receber"]
                * (df_fat_rec["Status_Adicional_Receber"] == "Aprovado")
            )

            # CARDS DE VISÃO GERAL DE FATURAMENTO (RECEBER)
            tot_rec_geral = df_fat_rec["Total_Receber"].sum()
            tot_rec_pago = df_fat_rec[
                df_fat_rec["Status_Faturamento_Receber"] == "Pago / Recebido"
            ]["Total_Receber"].sum()
            tot_rec_pendente = tot_rec_geral - tot_rec_pago

            f_k1, f_k2, f_k3 = st.columns(3)
            criar_card_kpi(
                f_k1, "Total do Período", f"R$ {tot_rec_geral:,.2f}"
            )
            criar_card_kpi(
                f_k2, "Já Recebido / Liquidado", f"R$ {tot_rec_pago:,.2f}"
            )
            criar_card_kpi(
                f_k3, "Pendente de Recebimento", f"R$ {tot_rec_pendente:,.2f}"
            )

            st.divider()

            df_edit_fat_rec = st.data_editor(
                df_fat_rec,
                column_config={
                    "Carga": st.column_config.TextColumn(
                        "Carga / Manifesto", disabled=True
                    ),
                    "Cliente_XDS": st.column_config.TextColumn(
                        "Cliente_XDS", disabled=True
                    ),
                    "Total_Receber": st.column_config.NumberColumn(
                        "Valor Total Aprovado (R$)",
                        format="R$ %.2f",
                        disabled=True,
                    ),
                    "Fatura_Receber_ID": st.column_config.TextColumn(
                        "Nº da Fatura / ND"
                    ),
                    "Status_Faturamento_Receber": st.column_config.SelectboxColumn(
                        "Status do Faturamento", options=status_faturamento_op
                    ),
                },
                hide_index=True,
                use_container_width=True,
                key="editor_faturamento_receber",
            )

            if st.button(
                "💾 Salvar Status de Faturamento (Receber)", type="primary"
            ):
                try:
                    with st.spinner("Atualizando faturas a receber..."):
                        for _, row in df_edit_fat_rec.iterrows():
                            carga_id = row["Carga"]
                            mask = df_raw["Carga"].astype(str) == str(carga_id)
                            df_raw.loc[mask, "Fatura_Receber_ID"] = row[
                                "Fatura_Receber_ID"
                            ]
                            df_raw.loc[
                                mask, "Status_Faturamento_Receber"
                            ] = row["Status_Faturamento_Receber"]

                        salvar_dados_na_planilha(df_raw)

                    st.success("✅ Faturas a Receber salvas com sucesso!")
                    st.cache_data.clear()

                except Exception as e:
                    st.error(f"Erro ao salvar Faturas a Receber: {e}")

        with tab_fat_pag:
            # Agregação com SOMA nos adicionais
            df_fat_pag = (
                df_filtrado.groupby("Carga")
                .agg({
                    "Motorista": "first",
                    "Frete_Pagar": "first",
                    "Adicional_Pagar": "sum",
                    "Status_Adicional_Pagar": "first",
                    "Fatura_Pagar_ID": "first",
                    "Status_Faturamento_Pagar": "first",
                })
                .reset_index()
            )

            df_fat_pag["Total_Pagar"] = df_fat_pag["Frete_Pagar"] + (
                df_fat_pag["Adicional_Pagar"]
                * (df_fat_pag["Status_Adicional_Pagar"] == "Aprovado")
            )

            # CARDS DE VISÃO GERAL DE FATURAMENTO (PAGAR)
            tot_pag_geral = df_fat_pag["Total_Pagar"].sum()
            tot_pag_pago = df_fat_pag[
                df_fat_pag["Status_Faturamento_Pagar"] == "Pago / Recebido"
            ]["Total_Pagar"].sum()
            tot_pag_pendente = tot_pag_geral - tot_pag_pago

            fp_k1, fp_k2, fp_k3 = st.columns(3)
            criar_card_kpi(
                fp_k1, "Total a Pagar (Período)", f"R$ {tot_pag_geral:,.2f}"
            )
            criar_card_kpi(
                fp_k2, "Já Pago / Quitado", f"R$ {tot_pag_pago:,.2f}"
            )
            criar_card_kpi(
                fp_k3, "Pendente de Pagamento", f"R$ {tot_pag_pendente:,.2f}"
            )

            st.divider()

            df_edit_fat_pag = st.data_editor(
                df_fat_pag,
                column_config={
                    "Carga": st.column_config.TextColumn(
                        "Carga / Manifesto", disabled=True
                    ),
                    "Motorista": st.column_config.TextColumn(
                        "Motorista", disabled=True
                    ),
                    "Total_Pagar": st.column_config.NumberColumn(
                        "Valor Total Aprovado (R$)",
                        format="R$ %.2f",
                        disabled=True,
                    ),
                    "Fatura_Pagar_ID": st.column_config.TextColumn(
                        "Nº Recibo / Fatura"
                    ),
                    "Status_Faturamento_Pagar": st.column_config.SelectboxColumn(
                        "Status do Pagamento", options=status_faturamento_op
                    ),
                },
                hide_index=True,
                use_container_width=True,
                key="editor_faturamento_pagar",
            )

            if st.button(
                "💾 Salvar Status de Pagamentos (Pagar)", type="primary"
            ):
                try:
                    with st.spinner("Atualizando pagamentos..."):
                        for _, row in df_edit_fat_pag.iterrows():
                            carga_id = row["Carga"]
                            mask = df_raw["Carga"].astype(str) == str(carga_id)
                            df_raw.loc[mask, "Fatura_Pagar_ID"] = row[
                                "Fatura_Pagar_ID"
                            ]
                            df_raw.loc[mask, "Status_Faturamento_Pagar"] = row[
                                "Status_Faturamento_Pagar"
                            ]

                        salvar_dados_na_planilha(df_raw)

                    st.success("✅ Pagamentos atualizados com sucesso!")
                    st.cache_data.clear()

                except Exception as e:
                    st.error(f"Erro ao salvar Faturas a Pagar: {e}")

    # --- ABA 6: CONTROLADORIA & DRE ---
    with aba_objs[5]:
        st.markdown(
            "#### 💰 Resultado Financeiro Consolidado & Status de Adicionais"
        )

        df_calc = (
            df_filtrado.groupby("Carga")
            .agg({
                "Frete_Receber": "first",
                "Frete_Pagar": "first",
                "Custo_Diesel": "first",
                "Adicional_Receber": "sum",
                "Status_Adicional_Receber": "first",
                "Adicional_Pagar": "sum",
                "Status_Adicional_Pagar": "first",
            })
            .reset_index()
        )

        rec_frete = df_calc["Frete_Receber"].sum()
        pag_frete = df_calc["Frete_Pagar"].sum()
        c_diesel = df_calc["Custo_Diesel"].sum()

        # Adicionais Receber (Aprovados vs Pendentes)
        rec_adic_aprovado = df_calc[
            df_calc["Status_Adicional_Receber"] == "Aprovado"
        ]["Adicional_Receber"].sum()
        rec_adic_pendente = df_calc[
            df_calc["Status_Adicional_Receber"] == "Pendente"
        ]["Adicional_Receber"].sum()

        # Adicionais Pagar (Aprovados vs Pendentes)
        pag_adic_aprovado = df_calc[
            df_calc["Status_Adicional_Pagar"] == "Aprovado"
        ]["Adicional_Pagar"].sum()
        pag_adic_pendente = df_calc[
            df_calc["Status_Adicional_Pagar"] == "Pendente"
        ]["Adicional_Pagar"].sum()

        f_total_receber = rec_frete + rec_adic_aprovado
        f_total_custos = pag_frete + pag_adic_aprovado + c_diesel
        margem_liquida = f_total_receber - f_total_custos

        st.markdown("##### 🟢 Resumo Geral DRE (Valores Homologados)")
        m1, m2, m3, m4 = st.columns(4)
        criar_card_kpi(m1, "Faturado Efetivo", f"R$ {f_total_receber:,.2f}")
        criar_card_kpi(m2, "Custos Efetivos", f"R$ {f_total_custos:,.2f}")
        criar_card_kpi(m3, "Margem Bruta (R$)", f"R$ {margem_liquida:,.2f}")
        criar_card_kpi(m4, "Consumo Diesel", f"R$ {c_diesel:,.2f}")

        st.divider()

        st.markdown("##### 🟡 Acompanhamento de Adicionais (Pipeline)")
        a1, a2, a3, a4 = st.columns(4)
        criar_card_kpi(
            a1, "Adic. Receber (Aprovado)", f"R$ {rec_adic_aprovado:,.2f}"
        )
        criar_card_kpi(
            a2, "Adic. Receber (Pendente)", f"R$ {rec_adic_pendente:,.2f}"
        )
        criar_card_kpi(
            a3, "Adic. Pagar (Aprovado)", f"R$ {pag_adic_aprovado:,.2f}"
        )
        criar_card_kpi(
            a4, "Adic. Pagar (Pendente)", f"R$ {pag_adic_pendente:,.2f}"
        )