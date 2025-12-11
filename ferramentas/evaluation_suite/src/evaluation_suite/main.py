import asyncio

import pandas as pd
import streamlit as st

from evaluation_suite.clients.api_client import APIClient

# Importa nossos componentes reais
from evaluation_suite.core.config import settings
from evaluation_suite.core.orchestrator import EvaluationOrchestrator
from vizu_db_connector.database import SessionLocal

# Configuração da página
st.set_page_config(layout="wide", page_title="Vizu Evaluation Suite")

# --- Funções de Backend Reais ---

def get_db_session():
    """Retorna uma sessão do banco de dados."""
    return SessionLocal()

def get_evaluation_history():
    """Mock para buscar o histórico de execuções."""
    # ... (manter mock por enquanto) ...
    data = { "Run ID": [], "Timestamp": [], "Dataset": [], "Versão": [], "Status": [] }
    return pd.DataFrame(data)

def run_evaluation_task(dataset_path: str, assistant_version: str):
    """
    Função síncrona que configura e executa a tarefa de avaliação assíncrona.
    """
    async def _run_async():
        # Instancia as dependências
        db = get_db_session()
        api_client = APIClient(base_url=settings.ASSISTANT_API_URL)
        orchestrator = EvaluationOrchestrator(db_session=db, assistant_client=api_client)

        try:
            run_id = await orchestrator.run_evaluation(dataset_path, assistant_version)
            return run_id
        finally:
            await api_client.close()
            db.close()

    return asyncio.run(_run_async())

# --- Interface do Usuário (UI) ---

st.title(" Vizu Evaluation Suite")
st.caption("Ferramenta para avaliação de performance do assistente virtual.")

col1, col2 = st.columns(2)

with col1:
    st.header("▶️ Iniciar Nova Execução")

    # Upload do arquivo de dataset
    uploaded_file = st.file_uploader(
        "Selecione o Dataset de Avaliação (.csv)",
        type=['csv'],
        help="O CSV deve conter as colunas 'clientevizu_id' e 'message'."
    )

    with st.form("evaluation_form"):
        assistant_version_tag = st.text_input(
            "Tag da Versão do Assistente",
            value="main-dev",
            help="Insira uma tag para identificar esta versão (ex: 'feature-nova-logica', 'v2.1.0')."
        )
        submitted = st.form_submit_button("Iniciar Avaliação")

        if submitted:
            if uploaded_file is None:
                st.error("Por favor, faça o upload de um dataset CSV.")
            elif not assistant_version_tag:
                st.error("Por favor, insira uma tag para a versão do assistente.")
            else:
                # O Streamlit salva o arquivo temporariamente, passamos o path para o orquestrador.
                dataset_path = f"/tmp/{uploaded_file.name}"
                with open(dataset_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.toast(f"Execução iniciada com o dataset '{uploaded_file.name}'!", icon="🚀")
                with st.spinner("Orquestrando a execução da avaliação... Aguarde."):
                    run_id = run_evaluation_task(dataset_path, assistant_version_tag)
                    st.success(f"Avaliação concluída com sucesso! Run ID: `{run_id}`")
                    st.info("Acompanhe os resultados detalhados no LangFuse e no banco de dados.")

with col2:
    st.header("📜 Histórico de Execuções")
    history_df = get_evaluation_history()
    st.dataframe(history_df, use_container_width=True)
    if st.button("Atualizar Histórico"):
        st.toast("Histórico atualizado!", icon="🔄")
