import logging
from typing import Optional
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable
from sqlalchemy import create_engine

# Dependências de outras libs Vizu
from vizu_shared_models.cliente_vizu import VizuClientContext
from vizu_shared_models.credencial_servico_externo import CredencialServicoExternoCreate
from vizu_llm_service.client import ModelTier, ModelTask # Importamos os enums

logger = logging.getLogger(__name__)

def _construir_db_url(credencial: dict) -> str:
    """
    Constrói a string de conexão SQLAlchemy a partir do modelo de credencial.

    Esta função é crítica para garantir o isolamento, pois usa as
    credenciais específicas do cliente.
    """
    db_creds = credencial
    if not all([db_creds.get('db_user'), db_creds.get('db_password'), db_creds.get('db_host'), db_creds.get('db_name')]):
        raise ValueError("Credencial SQL incompleta. Todos os campos são obrigatórios.")

    # TODO: Validar o dialeto (ex: 'postgresql', 'mysql') se necessário
    dialeto = db_creds.get('db_dialeto') or "postgresql"

    return (
        f"{dialeto}+psycopg2://{db_creds['db_user']}:{db_creds['db_password']}"
        f"@{db_creds['db_host']}:{db_creds.get('db_port') or 5432}/{db_creds['db_name']}"
    )

def create_sql_agent_runnable(
    contexto: VizuClientContext,
    llm: BaseChatModel,
    llm_fast: Optional[BaseChatModel] = None, # Opcional: para classificação/roteamento
    tabelas_incluidas: Optional[list[str]] = None
) -> Optional[Runnable]:
    """
    Factory agnóstica para criar um Agente SQL executável (Runnable).

    Recebe o contexto do cliente e o(s) LLM(s) já instrumentados (com Langfuse).

    Args:
        contexto: O VizuClientContext completo.
        llm: O LLM principal (ex: POWERFUL) para execução do agente.
        llm_fast: (Opcional) Um LLM mais rápido (ex: FAST) para tarefas
                  internas do agente, como classificação de tabelas.
        tabelas_incluidas: (Opcional) Lista explícita de tabelas a incluir.
                           Se None, usará o schema_sql do contexto.

    Returns:
        Uma instância de 'Runnable' (Agente SQL) ou None se a ferramenta
        estiver desabilitada ou as credenciais estiverem ausentes.
    """

    # --- 1. Validação de Permissão e Configuração ---
    if not contexto.ferramenta_sql_habilitada:
        logger.warning(f"Tentativa de criar agente SQL para contexto.id.")
        return None

    sql_credencial = next((c for c in contexto.credenciais if c.nome_servico == 'sql_service_mock'), None)
    if not sql_credencial:
        logger.error(f"Cliente {contexto.id} tem SQL habilitado, mas não possui credenciais para o serviço 'sql_service_mock'.")
        return None

    try:
        db_url = _construir_db_url(sql_credencial.credenciais)
    except ValueError as e:
        logger.error(f"Erro ao construir db_url para {contexto.id}: {e}")
        return None

    # --- 2. Construção dos Componentes ---
    logger.info(contexto.id)

    # CRÍTICO: Esta é a 'despesa' que o tool_pool_api irá 'aquecer'.
    # Estamos criando uma Engine exclusiva para este cliente.
    engine = create_engine(db_url, pool_size=5, max_overflow=2, pool_recycle=300)

    # Define as tabelas que o agente poderá ver
    include_tables = tabelas_incluidas
    if not include_tables and contexto.prompt_base:
        # TODO: Parsear o schema_sql para extrair nomes de tabelas, se necessário
        # Por enquanto, se 'tabelas_incluidas' for None, Langchain faz a introspecção
        pass

    db = SQLDatabase(engine=engine, include_tables=include_tables)

    # Usa o LLM rápido para introspecção, se fornecido
    llm_para_introspeccao = llm_fast or llm

    # --- 3. Criação do Agente ---
    logger.info(f"Instanciando Agente SQL para {contexto.id}...")

    # create_sql_agent retorna um AgentExecutor, que é um Runnable
    agente_runnable = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="openai-tools", # O tipo de agente padrão recomendado
        verbose=True, # Vamos deixar o Langfuse/Observabilidade cuidar disso
        handle_parsing_errors=True,
        llm_for_table_verification=llm_para_introspeccao
    )

    logger.info(f"Agente SQL criado com sucesso para {contexto.id}.")

    return agente_runnable