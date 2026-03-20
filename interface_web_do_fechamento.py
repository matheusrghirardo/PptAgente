"""
interface_web_do_fechamento.py - PowerDeck Financial Close Edition
======================================================
Interface B3-branded para fechamento mensal automático.
Upload de PPTX base + Excels → Geração automática do PPTX atualizado.
Layout executivo de duas colunas.
"""

import warnings
warnings.filterwarnings("ignore", message="Core Pydantic V1", category=UserWarning)

import time
import logging
import streamlit as st

logger = logging.getLogger(__name__)

from constantes_da_aplicacao import MODEL_PROVIDER, MODELOS_POR_PROVIDER, SHOW_PREVIEW
from configura_modelos_por_etapa import listar_configuracao_ativa, AMBIENTE_ATIVO
from monitora_execucao_dos_agentes import ObservabilityAgent, init_obs
from extrai_estrutura_do_pptx import extrair_estrutura_pptx
from cliente_modelos_de_linguagem import LLMClient
from orquestra_fechamento_mensal import executar_fechamento
from extrai_padroes_do_pptx import MESES_COMPLETOS
from componentes_visuais_da_interface import (
    GLOBAL_CSS,
    render_header,
    render_section_label,
    render_input_card_pptx,
    render_input_card_excel,
    render_file_ok,
    render_pipeline,
    render_resultado,
    render_avisos_manuais,
    render_log,
    render_separator,
    sanitizar_log,
)

# ---- Page Config ----
st.set_page_config(
    page_title="PowerDeck — Fechamento Mensal",
    page_icon="\U0001f4ca",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Sidebar: environment/model info
_config_ativa = listar_configuracao_ativa()
st.sidebar.caption(f"Ambiente: **{AMBIENTE_ATIVO}**")
st.sidebar.caption("Modelos por etapa:")
for _etapa, _mod in _config_ativa.items():
    st.sidebar.caption(f"  `{_etapa}`: {_mod}")
logger.info("Modelos ativos (%s): %s", AMBIENTE_ATIVO, _config_ativa)

# ---- Session State ----
for key, default in {
    "pptx_bytes": None,
    "pptx_original": None,
    "pptx_filename": None,
    "pptx_loaded": False,
    "messages": [],
    "chat_history": [],
    "historico_alteracoes": [],
    "edit_log": [],
    "fechamento_log": [],
    "fechamento_rodando": False,
    "pptx_resultado": None,
    "resultado_contexto": None,
    "avisos_manuais": [],
    "agent_states": {"excel": "waiting", "pattern": "waiting", "mapper": "waiting", "executor": "waiting"},
    "resultado_stats": None,
    "execution_log": [],
    "progress_items": [],
    "exec_stats": {"total": 0, "done": 0, "errors": 0, "warnings": 0, "skipped": 0, "elapsed": "0s"},
}.items():
    st.session_state.setdefault(key, default)

if "obs_agent" not in st.session_state:
    st.session_state.obs_agent = ObservabilityAgent()
obs = init_obs(st.session_state)


# ---- Main Interface ----
def main():
    # HEADER (full width)
    ambiente_tag = "DEV" if AMBIENTE_ATIVO == "dev" else "PROD"
    st.markdown(render_header(ambiente_tag), unsafe_allow_html=True)

    # CONFIG EXPANDER (full width)
    with st.expander("CONFIGURAÇÕES", expanded=False):
        col_provider, col_api, col_model = st.columns([0.8, 1.5, 1.0], gap="medium")

        with col_provider:
            provider = st.selectbox(
                "Provider",
                ["perplexity", "anthropic"],
                index=0 if MODEL_PROVIDER == "perplexity" else 1,
                key="cfg_provider",
            )

        with col_api:
            api_key = st.text_input(
                "API Key",
                type="password",
                value="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",
                key="cfg_api_key",
            )

        with col_model:
            modelos = MODELOS_POR_PROVIDER.get(provider, ["sonar"])
            default_idx = next((i for i, m in enumerate(modelos) if "pro" in m and "reasoning" not in m), 0)
            modelo = st.selectbox(
                "Modelo",
                modelos,
                index=default_idx,
                key="cfg_modelo",
            )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ======================================
    # TWO-COLUMN LAYOUT — Bots & Logs dominant
    # ======================================
    col_pipeline, col_inputs = st.columns([3, 2], gap="large")

    # ---- LEFT COLUMN (dominant): Pipeline + Bots ----

    # ---- RIGHT COLUMN: Inputs ----
    with col_inputs:
        st.markdown(render_section_label("ARQUIVOS DE ENTRADA"), unsafe_allow_html=True)

        # -- PPTX Upload --
        pptx_loaded = bool(st.session_state.pptx_bytes)
        pptx_meta = ""
        if pptx_loaded:
            try:
                e = extrair_estrutura_pptx(st.session_state.pptx_bytes)
                pptx_meta = f"{e['total_slides']} slides, {sum(len(s['shapes']) for s in e['slides'])} shapes"
            except Exception:
                pptx_meta = ""

        st.markdown(
            render_input_card_pptx(
                loaded=pptx_loaded,
                filename=st.session_state.pptx_filename or "",
                meta=pptx_meta,
            ),
            unsafe_allow_html=True,
        )

        uploaded_pptx = st.file_uploader(
            "Arquivo PPTX",
            type=["pptx"],
            label_visibility="collapsed",
            key="upload_pptx",
        )
        if uploaded_pptx:
            data = uploaded_pptx.read()
            st.session_state.pptx_bytes = data
            st.session_state.pptx_original = data
            st.session_state.pptx_filename = uploaded_pptx.name

        st.markdown("<hr class='df-input-sep'/>", unsafe_allow_html=True)

        # -- Excel Upload --
        uploaded_excels = st.file_uploader(
            "Arquivos Excel",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="upload_excels",
        )
        excel_loaded = bool(uploaded_excels)
        excel_info = ""
        if excel_loaded:
            names = [f.name for f in uploaded_excels]
            excel_info = f"\u2713  {len(names)} arquivo(s): {', '.join(names)}"

        st.markdown(
            render_input_card_excel(loaded=excel_loaded, files_info=excel_info),
            unsafe_allow_html=True,
        )

        # -- Period Override --
        with st.expander("PERIODO MANUAL (OPCIONAL)", expanded=False):
            st.caption(
                "Por padrão o LLM detecta o mês de referência automaticamente. "
                "Use esta seção apenas para sobrescrever a detecção."
            )
            usar_override = st.checkbox("Definir mês de referência manualmente", value=False, key="ck_override")
            if usar_override:
                col_mes, col_ano = st.columns(2)
                with col_mes:
                    override_mes = st.selectbox(
                        "Mês base",
                        options=list(range(1, 13)),
                        format_func=lambda m: MESES_COMPLETOS[m - 1],
                        index=0,
                        key="override_mes",
                    )
                with col_ano:
                    override_ano = st.number_input(
                        "Ano base",
                        min_value=2000,
                        max_value=2100,
                        value=2025,
                        step=1,
                        key="override_ano",
                    )
            else:
                override_mes = None
                override_ano = None

    # ---- LEFT COLUMN (dominant): Pipeline + Execute + Result + Log ----
    with col_pipeline:
        # Pipeline visualization
        pipeline_placeholder = st.empty()
        pipeline_placeholder.markdown(
            render_pipeline(st.session_state.agent_states),
            unsafe_allow_html=True,
        )

        # Execute button
        pronto = bool(api_key and st.session_state.pptx_bytes and uploaded_excels)

        if not pronto:
            faltam = []
            if not api_key:
                faltam.append("API Key")
            if not st.session_state.pptx_bytes:
                faltam.append("PPTX base")
            if not uploaded_excels:
                faltam.append("Excel(s)")
            st.caption(f"Aguardando: {', '.join(faltam)}")

        executar = st.button(
            "GERAR FECHAMENTO",
            disabled=not pronto,
            type="primary",
            use_container_width=True,
        )

        # Execution block
        if executar and pronto:
            st.session_state.fechamento_log = []
            st.session_state.pptx_resultado = None
            st.session_state.avisos_manuais = []
            st.session_state.resultado_stats = None
            st.session_state.agent_states = {
                "excel": "waiting", "pattern": "waiting",
                "mapper": "waiting", "executor": "waiting",
            }

            excel_files = []
            for f in uploaded_excels:
                f.seek(0)
                excel_files.append((f.name, f.read()))

            llm = LLMClient(api_key=api_key, model=modelo, provider=provider)

            log_placeholder = st.empty()
            panel_placeholder = st.empty()

            def _update_agents(states):
                st.session_state.agent_states = states
                pipeline_placeholder.markdown(
                    render_pipeline(states), unsafe_allow_html=True,
                )

            def _on_log(msg):
                st.session_state.fechamento_log.append(msg)
                log_placeholder.markdown(
                    render_log(st.session_state.fechamento_log),
                    unsafe_allow_html=True,
                )
                if "Etapa 0/3" in msg or "Extraindo padroes" in msg or "Extraindo padr" in msg:
                    _update_agents({"excel": "waiting", "pattern": "processing", "mapper": "waiting", "executor": "waiting"})
                elif "Etapa 1/3" in msg or "Extraindo dados" in msg:
                    _update_agents({"excel": "processing", "pattern": "done", "mapper": "waiting", "executor": "waiting"})
                elif "Etapa 2/3" in msg or "Mapeando dados" in msg:
                    _update_agents({"excel": "done", "pattern": "done", "mapper": "processing", "executor": "waiting"})
                elif "Etapa 3/3" in msg or "Executando edicoes" in msg or "Executando edi" in msg:
                    _update_agents({"excel": "done", "pattern": "done", "mapper": "done", "executor": "processing"})
                elif "Fechamento conclu" in msg or "\U0001f3c1" in msg:
                    _update_agents({"excel": "done", "pattern": "done", "mapper": "done", "executor": "done"})

            inicio = time.time()

            with st.spinner("Processando fechamento mensal..."):
                resultado = executar_fechamento(
                    llm=llm,
                    obs=obs,
                    pptx_bytes=st.session_state.pptx_bytes,
                    excel_files=excel_files,
                    on_log=_on_log,
                    panel_placeholder=panel_placeholder,
                    override_mes=override_mes,
                    override_ano=override_ano,
                )

            elapsed = f"{time.time() - inicio:.1f}s"
            total_ok = resultado.resultado_edicao.get("total_sucesso", 0)
            total_err = resultado.resultado_edicao.get("total_erro", 0)

            if resultado.sucesso:
                st.session_state.pptx_resultado = resultado.pptx_bytes
                st.session_state.pptx_bytes = resultado.pptx_bytes
                st.session_state.resultado_contexto = resultado.contexto_temporal
                st.balloons()

            st.session_state.avisos_manuais = resultado.avisos_manuais
            st.session_state.resultado_stats = {
                "sucesso": resultado.sucesso,
                "total_ok": total_ok,
                "total_err": total_err,
                "elapsed": elapsed,
            }

            log_placeholder.empty()
            panel_placeholder.empty()

        # Result card (persistent, stays in right column)
        if st.session_state.resultado_stats:
            stats = st.session_state.resultado_stats
            st.markdown(
                render_resultado(
                    stats["sucesso"], stats["total_ok"],
                    stats["total_err"], stats["elapsed"],
                ),
                unsafe_allow_html=True,
            )

        # Download button (inside result card area)
        if st.session_state.pptx_resultado:
            nome_saida = (
                st.session_state.resultado_contexto["nome_arquivo_saida"]
                if st.session_state.resultado_contexto
                else (st.session_state.pptx_filename or "deck.pptx").replace(".pptx", "_FECHAMENTO.pptx")
            )
            st.markdown('<div class="df-download">', unsafe_allow_html=True)
            st.download_button(
                "DOWNLOAD PPTX ATUALIZADO",
                data=st.session_state.pptx_resultado,
                file_name=nome_saida,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

    # ======================================
    # FULL-WIDTH SECTIONS BELOW COLUMNS
    # ======================================

    # Avisos manuais
    if st.session_state.avisos_manuais:
        st.markdown(
            render_avisos_manuais(st.session_state.avisos_manuais),
            unsafe_allow_html=True,
        )

    # Log area (prominent terminal view)
    if st.session_state.fechamento_log:
        st.markdown(render_section_label("TERMINAL DE EXECUÇÃO"), unsafe_allow_html=True)
        st.markdown(
            render_log(st.session_state.fechamento_log),
            unsafe_allow_html=True,
        )

    # Preview (conditional)
    if SHOW_PREVIEW and st.session_state.pptx_resultado:
        try:
            from gera_previsualizacao_html_do_pptx import gerar_preview_html_inline
            preview_html, preview_h = gerar_preview_html_inline(
                st.session_state.pptx_resultado
            )
            with st.expander("PREVIEW DO PPTX GERADO", expanded=False):
                import streamlit.components.v1 as components
                components.html(preview_html, height=preview_h, scrolling=True)
        except Exception:
            pass


# ---- Entry point ----
if __name__ == "__main__":
    main()
else:
    main()