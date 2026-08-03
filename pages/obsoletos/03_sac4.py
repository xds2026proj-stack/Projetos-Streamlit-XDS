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
# 3. CONEXÃO E CARREGAMENTO
# -----------------------------------------------------------------------------
@st.cache_resource
def conectar_gsheets():
    credentials = dict(st.secrets["connections"]["gsheets"])
    return gspread.service_account_from_dict(credentials)


@st.cache_data(ttl=60)
def carregar_dados():
    gc = conectar_gsheets()
    sh = gc.open_by_url(URL_PLANILHA)

    # 1. Entregas (Aba Principal)
    ws_entregas = sh.get_worksheet(0)
    dados_entregas = ws_entregas.get_all_records()
    df_entregas = pd.DataFrame(dados_entregas)

    # 2. Motoristas (Aba 'Motoristas')
    motoristas_ativos = ["Manter Atual / Não Alterar", "Não Atribuído"]
    try:
        ws_motoristas = sh.worksheet("Motoristas")
        df_mot = pd.DataFrame(ws_motoristas.get_all_records())

        if "Status" in df_mot.columns:
            df_mot = df_mot[
                df_mot["Status"].astype(str).str.upper() == "ATIVO"
            ]

        if "Nome" in df_mot.columns and "Placa" in df_mot.columns:
            motoristas_ativos += (
                df_mot["Nome"] + " (" + df_mot["Placa"] + ")"
            ).tolist()
        elif "Nome" in df_mot.columns:
            motoristas_ativos += df_mot["Nome"].tolist()
    except Exception:
        motoristas_ativos += ["João", "Carlos", "Ana", "Roberto"]

    return df_entregas, ws_entregas, motoristas_ativos, sh


try:
    df_raw, ws_ref, lista_motoristas, spreadsheet_ref = carregar_dados()
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    st.stop()


# -----------------------------------------------------------------------------
# FUNÇÃO ROBUSTA DE SALVAMENTO (EVITA BUG '_auth_request')
# -----------------------------------------------------------------------------
def salvar_dados_na_planilha(df_para_salvar, worksheet):
    """Garante a gravação na planilha contornando bugs do gspread/google-auth."""
    df_limpo = df_para_salvar.fillna("").astype(str)
    matriz = [df_limpo.columns.tolist()] + df_limpo.values.tolist()

    # Método 1: Limpa a aba e atualiza usando batch_update na planilha principal
    try:
        worksheet.clear()
        # Constrói o payload direto da API v4 do Google Sheets
        body = {"values": matriz}
        worksheet.spreadsheet.values_update(
            f"{worksheet.title}!A1",
            params={"valueInputOption": "USER_ENTERED"},
            body=body,
        )
    except Exception:
        # Método 2 (Fallback caso o gspread esteja em versão mais antiga)
        cell_list = []
        for row_idx, row in enumerate(matriz):
            for col_idx, val in enumerate(row):
                cell_list.append(
                    gspread.Cell(row_idx + 1, col_idx + 1, str(val))
                )
        worksheet.clear()
        worksheet.update_cells(cell_list)


# -----------------------------------------------------------------------------
# 4. SIDEBAR
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
# 5. FILTROS DE CONSULTA
# -----------------------------------------------------------------------------
st.title("🚚 Gestão Operacional de Entregas")

with st.container(border=True):
    st.markdown("### 🔍 Filtros de Consulta Operacional")
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)

    cargas = (
        ["Todas"] + sorted(list(df_raw["Carga"].astype(str).unique()))
        if "Carga" in df_raw.columns
        else ["Todas"]
    )
    carga_sel = f_col1.selectbox("📦 Carga / Manifesto", cargas)

    clientes = (
        ["Todos"] + sorted(list(df_raw["Cliente"].astype(str).unique()))
        if "Cliente" in df_raw.columns
        else ["Todos"]
    )
    cliente_sel = f_col2.selectbox("🏢 Cliente", clientes)

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
    status_sel = f_col4.selectbox("📌 Status", status_list)

    ocorrencias = (
        ["Todas"] + sorted(list(df_raw["Ocorrência"].astype(str).unique()))
        if "Ocorrência" in df_raw.columns
        else ["Todas"]
    )
    ocorrencia_sel = f_col5.selectbox("⚠️ Ocorrência", ocorrencias)

# Aplicação dos Filtros
df_filtrado = df_raw.copy()

if carga_sel != "Todas" and "Carga" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Carga"].astype(str) == str(carga_sel)
    ]
if cliente_sel != "Todos" and "Cliente" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Cliente"].astype(str) == str(cliente_sel)
    ]
if motorista_sel != "Todos" and "Motorista" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Motorista"].astype(str) == str(motorista_sel)
    ]
if status_sel != "Todos" and "Status" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Status"].astype(str) == str(status_sel)
    ]
if ocorrencia_sel != "Todas" and "Ocorrência" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Ocorrência"].astype(str) == str(ocorrencia_sel)
    ]

# -----------------------------------------------------------------------------
# 6. ABAS
# -----------------------------------------------------------------------------
tab_geral, tab_operacao, tab_kpi_log, tab_kpi_fin = st.tabs([
    "📋 Visão Geral",
    "⚡ Operação & Atualização em Lote",
    "📊 Nível de Serviço (OTD/OTIF)",
    "💰 Indicadores Financeiros",
])

# ABA 1: VISÃO GERAL
with tab_geral:
    st.markdown("#### 📈 Visão Consolidada")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    kpi1.metric("Total de Pedidos", len(df_filtrado))
    kpi2.metric(
        "Pendentes",
        len(df_filtrado[df_filtrado["Status"] == "Pendente"])
        if "Status" in df_filtrado.columns
        else 0,
    )
    kpi3.metric(
        "Em Trânsito",
        len(df_filtrado[df_filtrado["Status"] == "Em Trânsito"])
        if "Status" in df_filtrado.columns
        else 0,
    )
    kpi4.metric(
        "Entregues",
        len(df_filtrado[df_filtrado["Status"] == "Entregue"])
        if "Status" in df_filtrado.columns
        else 0,
    )
    kpi5.metric(
        "Com Ocorrência",
        len(
            df_filtrado[
                (df_filtrado["Ocorrência"].notna())
                & (df_filtrado["Ocorrência"] != "")
                & (df_filtrado["Ocorrência"] != "Nenhuma")
            ]
        )
        if "Ocorrência" in df_filtrado.columns
        else 0,
    )

    st.divider()
    st.dataframe(df_filtrado, width="stretch", hide_index=True)

# ABA 2: ATUALIZAÇÃO EM LOTE E EDIÇÃO INDIVIDUAL
with tab_operacao:
    if perfil_user["perfil"] == "Leitor":
        st.warning(
            "🔒 Seu perfil de acesso permite apenas a visualização dos dados."
        )
    else:
        # AÇÃO EM LOTE (POR CARGA)
        with st.container(border=True):
            st.markdown("### ⚡ Ação em Lote (Atualizar Carga Completa)")
            st.caption(
                "Defina os dados abaixo para aplicar de uma só vez a todas as NFes filtradas no painel."
            )

            b_col1, b_col2, b_col3, b_col4 = st.columns([2, 2, 2, 2])

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

            novo_mot = b_col1.selectbox("🚛 Atribuir Motorista", lista_motoristas)
            novo_status = b_col2.selectbox("📌 Atribuir Status", status_op)
            nova_ocorrencia = b_col3.selectbox(
                "⚠️ Atribuir Ocorrência", ocorrencias_op
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if b_col4.button(
                "🚀 Aplicar em Lote na Carga", type="primary", width="stretch"
            ):
                if len(df_filtrado) == 0:
                    st.error("Nenhum pedido encontrado nos filtros atuais.")
                else:
                    indices_para_alterar = df_filtrado.index

                    if novo_mot != "Manter Atual / Não Alterar":
                        df_raw.loc[indices_para_alterar, "Motorista"] = novo_mot
                    if novo_status != "Manter Atual / Não Alterar":
                        df_raw.loc[indices_para_alterar, "Status"] = (
                            novo_status
                        )
                    if nova_ocorrencia != "Manter Atual / Não Alterar":
                        df_raw.loc[indices_para_alterar, "Ocorrência"] = (
                            nova_ocorrencia
                        )

                    try:
                        with st.spinner(
                            "Salvando alterações no Google Sheets..."
                        ):
                            salvar_dados_na_planilha(df_raw, ws_ref)

                        st.success(
                            f"✅ {len(indices_para_alterar)} pedido(s) atualizado(s) com sucesso!"
                        )
                        st.cache_data.clear()
                        st.rerun()

                    except Exception as err:
                        st.error(f"Erro ao salvar no Google Sheets: {err}")

        st.divider()

        # EDIÇÃO TABULAR INDIVIDUAL
        st.markdown("### ✏️ Edição Fina Line-by-Line (Ajuste Individual)")
        st.caption(
            "Edite células específicas da tabela se precisar pontuar exceções em algum pedido da carga."
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
            key="editor_fino",
        )

        if st.button("💾 Salvar Edição Fina na Nuvem", type="secondary"):
            try:
                with st.spinner("Atualizando registros..."):
                    # Aplica as edições feitas na tabela de volta ao DataFrame principal preservando os índices originais
                    df_raw.loc[df_editado.index, df_editado.columns] = (
                        df_editado.values
                    )

                    # Chama a mesma função de salvamento robusta que funcionou no lote
                    salvar_dados_na_planilha(df_raw, ws_ref)

                st.success(
                    "✅ Tabela individual atualizada com sucesso na nuvem!"
                )
                st.cache_data.clear()
                st.rerun()

            except Exception as err:
                st.error(f"Erro ao salvar edição fina: {err}")

# ABA 3: INDICADORES LOGÍSTICOS
with tab_kpi_log:
    st.markdown("#### 🎯 Indicadores de Nível de Serviço (SGI & Qualidade)")

    if len(df_filtrado) > 0:
        total = len(df_filtrado)
        entregues = len(df_filtrado[df_filtrado["Status"] == "Entregue"])

        no_prazo = (
            len(
                df_filtrado[
                    df_filtrado["No_Prazo"].astype(str).str.upper() == "SIM"
                ]
            )
            if "No_Prazo" in df_filtrado.columns
            else entregues
        )
        otd = (no_prazo / total * 100) if total > 0 else 0

        avarias = (
            len(df_filtrado[df_filtrado["Ocorrência"] == "Avaria"])
            if "Ocorrência" in df_filtrado.columns
            else 0
        )
        taxa_avaria = (avarias / total * 100) if total > 0 else 0

        c_otd, c_otif, c_avaria = st.columns(3)
        c_otd.metric("OTD (On-Time Delivery)", f"{otd:.1f}%")
        c_otif.metric("OTIF Estimated", f"{otd - taxa_avaria:.1f}%")
        c_avaria.metric("Índice de Avarias", f"{taxa_avaria:.1f}%")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Status das Entregas")
            st.bar_chart(df_filtrado["Status"].value_counts())
        with c2:
            st.markdown("##### Ocorrências Operacionais")
            if "Ocorrência" in df_filtrado.columns:
                st.bar_chart(df_filtrado["Ocorrência"].value_counts())
    else:
        st.info("Nenhum dado selecionado.")

# ABA 4: FINANCEIRO & CONTROLADORIA
with tab_kpi_fin:
    st.markdown("#### 💰 Visão Financeira e Custos de Operação")

    frete_receber = (
        pd.to_numeric(df_filtrado["Frete_Receber"], errors="coerce").sum()
        if "Frete_Receber" in df_filtrado.columns
        else 0.0
    )
    frete_pagar = (
        pd.to_numeric(df_filtrado["Frete_Pagar"], errors="coerce").sum()
        if "Frete_Pagar" in df_filtrado.columns
        else 0.0
    )
    custo_diesel = (
        pd.to_numeric(df_filtrado["Custo_Diesel"], errors="coerce").sum()
        if "Custo_Diesel" in df_filtrado.columns
        else 0.0
    )
    margem = frete_receber - (frete_pagar + custo_diesel)

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Fretes a Receber", f"R$ {frete_receber:,.2f}")
    f2.metric("Fretes a Pagar", f"R$ {frete_pagar:,.2f}")
    f3.metric("Custo Diesel", f"R$ {custo_diesel:,.2f}")
    f4.metric(
        "Margem Bruta",
        f"R$ {margem:,.2f}",
        delta=f"{(margem/frete_receber*100) if frete_receber > 0 else 0:.1f}%",
    )