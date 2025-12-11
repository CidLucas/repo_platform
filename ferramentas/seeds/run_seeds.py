"""
Script unificado para execução de seeds.

Uso:
    python -m seeds.run_seeds --all        # Executa DB + Qdrant
    python -m seeds.run_seeds --db         # Apenas banco de dados
    python -m seeds.run_seeds --qdrant     # Apenas Qdrant (RAG)
    python -m seeds.run_seeds --check      # Verifica estado atual
"""
import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path

# Adiciona paths para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs" / "vizu_db_connector" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs" / "vizu_models" / "src"))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Diretório base dos seeds
SEEDS_DIR = Path(__file__).parent
KNOWLEDGE_DIR = SEEDS_DIR / "knowledge"


def seed_database(db_url: str):
    """Popula o banco de dados com clientes de teste."""
    from sqlalchemy.exc import IntegrityError
    from sqlmodel import Session, create_engine, select

    from vizu_models import ClienteVizu
    from vizu_models.enums import TierCliente, TipoCliente

    from .clients import SEED_CLIENTS

    logger.info("=" * 60)
    logger.info("🌱 SEED DATABASE - Populando clientes de teste")
    logger.info("=" * 60)
    logger.info(f"   Database: {db_url.split('@')[-1]}")

    engine = create_engine(db_url)

    with Session(engine) as session:
        count_inserted = 0
        count_skipped = 0

        for client_data in SEED_CLIENTS:
            nome = client_data["nome_empresa"]

            # Verifica se já existe
            statement = select(ClienteVizu).where(ClienteVizu.nome_empresa == nome)
            existing = session.exec(statement).first()

            if existing:
                logger.info(f"   ⚠️  '{nome}' já existe (pulando)")
                count_skipped += 1
                continue

            try:
                # Converte strings para enums
                tipo_str = client_data["tipo_cliente"]
                tier_str = client_data["tier"]
                tipo_enum = TipoCliente(tipo_str) if isinstance(tipo_str, str) else tipo_str
                tier_enum = TierCliente(tier_str) if isinstance(tier_str, str) else tier_str

                # Cria o cliente
                novo_cliente = ClienteVizu(
                    id=uuid.uuid4(),
                    api_key=str(uuid.uuid4()),
                    nome_empresa=nome,
                    tipo_cliente=tipo_enum,
                    tier=tier_enum,
                )
                session.add(novo_cliente)
                session.flush()

                # Popula configurações
                config = client_data.get("config", {})
                novo_cliente.prompt_base = config.get("prompt_base", "")
                novo_cliente.horario_funcionamento = config.get("horario_funcionamento")
                novo_cliente.ferramenta_rag_habilitada = config.get("ferramenta_rag_habilitada", False)
                novo_cliente.ferramenta_sql_habilitada = config.get("ferramenta_sql_habilitada", False)
                novo_cliente.ferramenta_agendamento_habilitada = config.get("ferramenta_agendamento_habilitada", False)
                novo_cliente.collection_rag = config.get("collection_rag")

                session.add(novo_cliente)
                count_inserted += 1
                logger.info(f"   ✅ '{nome}' inserido")

            except Exception as e:
                logger.error(f"   ❌ Erro em '{nome}': {e}")
                session.rollback()
                continue

        try:
            session.commit()
            logger.info("=" * 60)
            logger.info(f"🎉 Seed DB concluído: {count_inserted} novos, {count_skipped} existentes")
            logger.info("=" * 60)
        except IntegrityError as e:
            session.rollback()
            logger.error(f"❌ Erro de integridade: {e}")


def seed_qdrant():
    """Popula o Qdrant com dados de conhecimento RAG."""
    import requests
    from qdrant_client import QdrantClient, models

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    embedding_url = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:11435")
    vector_size = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1024"))

    logger.info("=" * 60)
    logger.info("🌱 SEED QDRANT - Populando collections RAG")
    logger.info("=" * 60)
    logger.info(f"   Qdrant: {qdrant_url}")
    logger.info(f"   Embedding: {embedding_url}")
    logger.info(f"   Vector Size: {vector_size}")

    # Conecta ao Qdrant
    try:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        client.get_collections()
        logger.info("   ✅ Conectado ao Qdrant")
    except Exception as e:
        logger.error(f"   ❌ Erro ao conectar ao Qdrant: {e}")
        return

    # Carrega dados de conhecimento dos arquivos JSON
    if not KNOWLEDGE_DIR.exists():
        logger.error(f"   ❌ Diretório {KNOWLEDGE_DIR} não encontrado")
        return

    knowledge_files = list(KNOWLEDGE_DIR.glob("*.json"))
    if not knowledge_files:
        logger.warning("   ⚠️  Nenhum arquivo .json encontrado em ferramentas/seeds/knowledge/")
        return

    for json_file in knowledge_files:
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            collection_name = data.get("collection")
            documents = data.get("documents", [])

            if not collection_name or not documents:
                logger.warning(f"   ⚠️  Arquivo {json_file.name} inválido")
                continue

            logger.info(f"\n📚 Populando: {collection_name}")

            # Cria/recria collection
            try:
                existing = client.get_collection(collection_name)
                if existing.config.params.vectors.size != vector_size:
                    logger.info("   Recriando (dimensão diferente)...")
                    client.delete_collection(collection_name)
                    raise Exception("Recriar")
            except Exception:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )

            # Gera embeddings e insere
            points = []
            for idx, doc in enumerate(documents):
                title = doc.get("title", "")
                content = doc.get("content", "")
                text = f"{title}\n\n{content}"

                # Chama embedding service
                response = requests.post(
                    f"{embedding_url}/embed",
                    json={"texts": [text], "mode": "document"},
                    timeout=60
                )
                if response.status_code != 200:
                    logger.error(f"   ❌ Erro ao gerar embedding: {response.text}")
                    continue

                embedding = response.json()["embeddings"][0]

                points.append(models.PointStruct(
                    id=idx + 1,
                    vector=embedding,
                    payload={
                        "doc_id": doc.get("doc_id", f"doc_{idx}"),
                        "title": title,
                        "content": content,
                        "collection": collection_name
                    }
                ))
                logger.info(f"   ✅ {title}")

            # Upsert em batch
            if points:
                client.upsert(collection_name=collection_name, points=points, wait=True)
                logger.info(f"   📊 {len(points)} documentos inseridos")

        except Exception as e:
            logger.error(f"   ❌ Erro em {json_file.name}: {e}")
            import traceback
            traceback.print_exc()

    # Lista estado final
    logger.info("\n" + "=" * 60)
    logger.info("🎉 SEED QDRANT CONCLUÍDO")
    logger.info("=" * 60)
    for col in client.get_collections().collections:
        info = client.get_collection(col.name)
        logger.info(f"   {col.name}: {info.points_count} docs, {info.config.params.vectors.size} dims")


def check_status():
    """Verifica estado atual dos seeds."""
    logger.info("=" * 60)
    logger.info("📊 VERIFICANDO ESTADO DOS SEEDS")
    logger.info("=" * 60)

    # Verifica DB
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            from sqlmodel import Session, create_engine, select

            from vizu_models import ClienteVizu

            engine = create_engine(db_url)
            with Session(engine) as session:
                clients = session.exec(select(ClienteVizu)).all()
                logger.info(f"\n📦 Database: {len(clients)} clientes")
                for c in clients:
                    rag = "✅" if c.ferramenta_rag_habilitada else "❌"
                    sql = "✅" if c.ferramenta_sql_habilitada else "❌"
                    logger.info(f"   - {c.nome_empresa} | RAG:{rag} SQL:{sql} | {c.collection_rag or '-'}")
        except Exception as e:
            logger.error(f"   ❌ Erro ao verificar DB: {e}")
    else:
        logger.warning("   ⚠️  DATABASE_URL não definida")

    # Verifica Qdrant
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=qdrant_url)
        collections = client.get_collections().collections
        logger.info(f"\n🔍 Qdrant: {len(collections)} collections")
        for col in collections:
            info = client.get_collection(col.name)
            logger.info(f"   - {col.name}: {info.points_count} docs, {info.config.params.vectors.size} dims")
    except Exception as e:
        logger.error(f"   ❌ Erro ao verificar Qdrant: {e}")


def main():
    parser = argparse.ArgumentParser(description="Seed runner para Vizu")
    parser.add_argument("--all", action="store_true", help="Executa todos os seeds")
    parser.add_argument("--db", action="store_true", help="Seed apenas do banco")
    parser.add_argument("--qdrant", action="store_true", help="Seed apenas do Qdrant")
    parser.add_argument("--check", action="store_true", help="Verifica estado atual")

    args = parser.parse_args()

    if args.check:
        check_status()
        return

    if args.all or args.db:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("❌ DATABASE_URL não definida")
        else:
            seed_database(db_url)

    if args.all or args.qdrant:
        seed_qdrant()

    if not (args.all or args.db or args.qdrant or args.check):
        parser.print_help()


if __name__ == "__main__":
    main()
