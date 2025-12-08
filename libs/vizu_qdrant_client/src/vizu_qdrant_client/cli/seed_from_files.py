"""
Seed script para popular o Qdrant com dados de teste para RAG.
Lê arquivos JSON de conhecimento e usa chunking para dividir documentos longos.

Uso:
    python -m vizu_qdrant_client.cli.seed_from_files [--dir PATH] [--chunk-size 512] [--no-chunk]

Requer:
    - QDRANT_URL (default: http://localhost:6333)
    - EMBEDDING_SERVICE_URL (default: http://localhost:11435)
    - EMBEDDING_VECTOR_SIZE (default: 1024 para multilingual-e5-large)

IMPORTANTE: Este script usa EXCLUSIVAMENTE o .env da RAIZ do monorepo.
"""
import os
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models

# Configuracao de log
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACAO (lida do .env da raiz via variáveis de ambiente)
# =============================================================================

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:11435")

# Dimensao do vetor - DEVE corresponder ao modelo configurado no embedding_service
# intfloat/multilingual-e5-large = 1024
VECTOR_SIZE = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1024"))

# Default path for knowledge files
DEFAULT_KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "ferramentas" / "seeds" / "knowledge"


def get_embedding(text: str) -> List[float]:
    """
    Gera embedding usando o serviço de embedding local (HuggingFace).
    Usa o endpoint /embed do embedding_service que aplica os prefixos E5 automaticamente.
    """
    import requests

    try:
        response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/embed",
            json={"texts": [text]},
            timeout=120  # Timeout maior para textos longos
        )
        if response.status_code == 200:
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
        else:
            logger.error(f"   Erro do embedding service: {response.status_code} - {response.text}")
            raise Exception(f"Embedding service retornou {response.status_code}")
    except Exception as e:
        logger.error(f"   Erro ao gerar embedding: {e}")
        raise


def get_chunked_embeddings(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Usa o endpoint /process do embedding_service para chunkar e embedar em uma única chamada.
    Retorna lista de dicts com chunk info + embedding.
    """
    import requests

    try:
        response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/process",
            json={
                "text": text,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "strategy": "semantic",
                "embed": True,
                "mode": "document"
            },
            timeout=180  # Timeout maior para processamento completo
        )
        if response.status_code == 200:
            data = response.json()
            chunks = data.get("chunks", [])
            embeddings = data.get("embeddings", [])
            
            # Combina chunks com embeddings
            result = []
            for i, chunk in enumerate(chunks):
                chunk["embedding"] = embeddings[i] if i < len(embeddings) else None
                result.append(chunk)
            return result
        else:
            logger.error(f"   Erro do embedding service: {response.status_code} - {response.text}")
            raise Exception(f"Embedding service retornou {response.status_code}")
    except Exception as e:
        logger.error(f"   Erro ao processar texto: {e}")
        raise


def create_collection_if_not_exists(client: QdrantClient, collection_name: str, force_recreate: bool = True):
    """
    Cria collection se nao existir.
    Se force_recreate=True e a collection existir, deleta e recria para garantir dimensões corretas.
    """
    try:
        existing = client.get_collection(collection_name)
        existing_size = existing.config.params.vectors.size

        if force_recreate or existing_size != VECTOR_SIZE:
            logger.info(f"   Collection '{collection_name}' existe com {existing_size} dims, recriando com {VECTOR_SIZE}...")
            client.delete_collection(collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"   Collection '{collection_name}' recriada com {VECTOR_SIZE} dims")
            return False
        else:
            logger.info(f"   Collection '{collection_name}' ja existe com dimensões corretas ({VECTOR_SIZE})")
            return True
    except Exception:
        logger.info(f"   Criando collection '{collection_name}' com {VECTOR_SIZE} dims...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE
            )
        )
        return False


def load_knowledge_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Carrega um arquivo JSON de conhecimento."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"   Erro ao carregar {file_path}: {e}")
        return None


def seed_collection_with_chunks(
    client: QdrantClient,
    collection_name: str,
    documents: List[Dict[str, Any]],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    use_chunking: bool = True,
):
    """
    Popula uma collection com documentos, opcionalmente usando chunking.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"📚 Populando collection: {collection_name}")
    logger.info(f"{'='*60}")

    # Cria collection se necessario
    create_collection_if_not_exists(client, collection_name)

    # Prepara pontos para upsert
    points = []
    point_id = 1

    for doc in documents:
        doc_id = doc.get("doc_id", f"doc_{point_id}")
        title = doc.get("title", "")
        content = doc.get("content", "")

        # Texto combinado para embedding
        full_text = f"{title}\n\n{content}"
        
        if use_chunking and len(full_text) > chunk_size:
            # Usa chunking para documentos grandes
            logger.info(f"   Chunking: {title} ({len(full_text)} chars)...")
            try:
                chunk_results = get_chunked_embeddings(full_text, chunk_size, chunk_overlap)
                
                for i, chunk_data in enumerate(chunk_results):
                    if chunk_data.get("embedding"):
                        point = models.PointStruct(
                            id=point_id,
                            vector=chunk_data["embedding"],
                            payload={
                                "doc_id": f"{doc_id}_chunk_{i}",
                                "parent_doc_id": doc_id,
                                "title": title,
                                "content": chunk_data["text"],
                                "chunk_index": chunk_data.get("index", i),
                                "collection": collection_name,
                                "is_chunk": True,
                            }
                        )
                        points.append(point)
                        point_id += 1
                
                logger.info(f"   -> {len(chunk_results)} chunks criados")
                
            except Exception as e:
                logger.error(f"   Erro ao chunkar {title}: {e}")
                # Fallback: usa documento inteiro
                logger.info(f"   Fallback: usando documento inteiro")
                embedding = get_embedding(full_text)
                point = models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "doc_id": doc_id,
                        "title": title,
                        "content": content,
                        "collection": collection_name,
                        "is_chunk": False,
                    }
                )
                points.append(point)
                point_id += 1
        else:
            # Documento pequeno - usa inteiro
            logger.info(f"   Embedding: {title} ({len(full_text)} chars)...")
            embedding = get_embedding(full_text)
            
            point = models.PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "doc_id": doc_id,
                    "title": title,
                    "content": content,
                    "collection": collection_name,
                    "is_chunk": False,
                }
            )
            points.append(point)
            point_id += 1

    # Upsert em batch
    if points:
        logger.info(f"   Inserindo {len(points)} pontos...")
        client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )
        logger.info(f"   ✅ Collection '{collection_name}' populada com {len(points)} pontos")
    else:
        logger.warning(f"   ⚠️ Nenhum ponto para inserir em '{collection_name}'")


def run_seed(
    knowledge_dir: Optional[Path] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    use_chunking: bool = True,
):
    """Funcao principal de seed do Qdrant."""
    knowledge_dir = knowledge_dir or DEFAULT_KNOWLEDGE_DIR
    
    logger.info("\n" + "="*60)
    logger.info("🌱 SEED QDRANT FROM FILES")
    logger.info("="*60)
    logger.info(f"   Knowledge dir: {knowledge_dir}")
    logger.info(f"   Qdrant URL: {QDRANT_URL}")
    logger.info(f"   Vector Size: {VECTOR_SIZE}")
    logger.info(f"   Embedding Service: {EMBEDDING_SERVICE_URL}")
    logger.info(f"   Chunking: {'ON' if use_chunking else 'OFF'} (size={chunk_size}, overlap={chunk_overlap})")

    # Verifica se o diretorio existe
    if not knowledge_dir.exists():
        logger.error(f"   ❌ Diretório não encontrado: {knowledge_dir}")
        return

    # Lista arquivos JSON
    json_files = list(knowledge_dir.glob("*.json"))
    if not json_files:
        logger.error(f"   ❌ Nenhum arquivo .json encontrado em {knowledge_dir}")
        return
    
    logger.info(f"   Encontrados {len(json_files)} arquivos JSON")

    # Conecta ao Qdrant
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        client.get_collections()
        logger.info("   ✅ Conectado ao Qdrant")
    except Exception as e:
        logger.error(f"   ❌ Erro ao conectar ao Qdrant: {e}")
        logger.error("   Verifique se o Qdrant esta rodando em " + QDRANT_URL)
        return

    # Processa cada arquivo
    for json_file in json_files:
        logger.info(f"\n📄 Processando: {json_file.name}")
        
        data = load_knowledge_file(json_file)
        if not data:
            continue
        
        collection_name = data.get("collection")
        documents = data.get("documents", [])
        
        if not collection_name:
            logger.warning(f"   ⚠️ Arquivo sem 'collection': {json_file.name}")
            continue
        
        if not documents:
            logger.warning(f"   ⚠️ Arquivo sem 'documents': {json_file.name}")
            continue
        
        try:
            seed_collection_with_chunks(
                client=client,
                collection_name=collection_name,
                documents=documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_chunking=use_chunking,
            )
        except Exception as e:
            logger.error(f"   ❌ Erro ao popular '{collection_name}': {e}")
            import traceback
            traceback.print_exc()

    logger.info("\n" + "="*60)
    logger.info("🎉 SEED FINALIZADO")
    logger.info("="*60)

    # Lista collections criadas
    collections = client.get_collections()
    logger.info(f"\n   Collections disponiveis:")
    for col in collections.collections:
        try:
            info = client.get_collection(col.name)
            logger.info(f"   - {col.name}: {info.points_count} pontos, {info.config.params.vectors.size} dims")
        except Exception:
            logger.info(f"   - {col.name}: (erro ao obter info)")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Seed Qdrant with knowledge files using chunking"
    )
    parser.add_argument(
        "--dir", "-d",
        type=Path,
        default=DEFAULT_KNOWLEDGE_DIR,
        help=f"Directory containing JSON knowledge files (default: {DEFAULT_KNOWLEDGE_DIR})"
    )
    parser.add_argument(
        "--chunk-size", "-s",
        type=int,
        default=512,
        help="Target chunk size in characters (default: 512)"
    )
    parser.add_argument(
        "--chunk-overlap", "-o",
        type=int,
        default=50,
        help="Chunk overlap in characters (default: 50)"
    )
    parser.add_argument(
        "--no-chunk",
        action="store_true",
        help="Disable chunking (embed full documents)"
    )
    
    args = parser.parse_args()
    
    run_seed(
        knowledge_dir=args.dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        use_chunking=not args.no_chunk,
    )


if __name__ == "__main__":
    main()
