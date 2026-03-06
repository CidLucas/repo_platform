"""
Script para atualizar clientes existentes com novas configuracoes.
Usa os dados de SEED_CLIENTS do seed.py para atualizar registros existentes.

Uso:
    python -m vizu_db_connector.cli.update_clients
"""

import logging
import os
from typing import Any

from sqlmodel import Session, create_engine, select

from vizu_models import ClienteVizu

from .seed import SEED_CLIENTS

# Configuracao de log
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def update_client(session: Session, client_data: dict[str, Any]) -> bool:
    """Atualiza um cliente existente com novos dados."""
    nome = client_data["nome_empresa"]

    # Busca cliente pelo nome
    statement = select(ClienteVizu).where(ClienteVizu.nome_empresa == nome)
    cliente = session.exec(statement).first()

    if not cliente:
        logger.warning(f"   ⚠️  Cliente '{nome}' nao encontrado. Pulando.")
        return False

    # Atualiza campos de configuracao
    config = client_data.get("config", {})

    cliente.prompt_base = config.get("prompt_base", cliente.prompt_base)
    cliente.horario_funcionamento = config.get(
        "horario_funcionamento", cliente.horario_funcionamento
    )

    # Update enabled_tools from config
    if "enabled_tools" in config:
        cliente.enabled_tools = config.get("enabled_tools") or []

    cliente.collection_rag = config.get("collection_rag", cliente.collection_rag)

    # Atualiza tier se especificado
    if "tier" in client_data:
        cliente.tier = client_data["tier"]

    session.add(cliente)
    logger.info(f"   ✅ Cliente '{nome}' atualizado")
    return True


def run_update(db_url: str = None):
    """Funcao principal de update."""
    if db_url is None:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("❌ DATABASE_URL nao definida")
            return

    logger.info("\n" + "=" * 60)
    logger.info("🔄 ATUALIZANDO CLIENTES EXISTENTES")
    logger.info("=" * 60)
    logger.info(f"   Banco: {db_url.split('@')[-1]}")

    engine = create_engine(db_url)

    with Session(engine) as session:
        updated = 0
        skipped = 0

        for client_data in SEED_CLIENTS:
            if update_client(session, client_data):
                updated += 1
            else:
                skipped += 1

        try:
            session.commit()
            logger.info("\n" + "=" * 60)
            logger.info("🎉 Atualizacao concluida!")
            logger.info(f"   Atualizados: {updated}")
            logger.info(f"   Nao encontrados: {skipped}")
            logger.info("=" * 60)
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erro ao salvar: {e}")


if __name__ == "__main__":
    run_update()
