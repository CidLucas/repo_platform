#!/usr/bin/env python3
"""
Backfill embeddings for shared_business_memory rows.

Iterates rows where embedding IS NULL, generates embedding text via
_build_embedding_text(), calls Cohere API in batches of 96, updates rows.

Usage:
    python scripts/backfill_shared_memory_embeddings.py [--client-id UUID] [--batch-size 96] [--dry-run]

Prerequisites:
    - T3.1a migration applied (embedding column exists)
    - CO_API_KEY set (Cohere API key)
    - SUPABASE_URL, SUPABASE_SERVICE_KEY set
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_supabase_client" / "src"))
sys.path.insert(0, str(ROOT_DIR / "libs" / "blu_llm_service" / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# _build_embedding_text (replicado de T3.1b — memory_module.py)
# ---------------------------------------------------------------------------


def _build_embedding_text(
    entity_type: str,
    entity_name: str,
    key: str,
    value: dict | None,
    category: str | None = None,
) -> str:
    """Constrói representação textual do fato para embedding.

    Segue a mesma filosofia do process-document edge function:
    gerar texto representativo com campos semanticamente relevantes,
    embeddar, armazenar.
    """
    parts = [
        f"Entity type: {entity_type}",
        f"Entity name: {entity_name}",
        f"Key: {key}",
    ]
    if category:
        parts.append(f"Category: {category}")
    # Incluir campos significativos do value (não o JSON inteiro)
    if isinstance(value, dict):
        for k, v in value.items():
            if k in (
                "snapshot_id", "gerado_em", "vigencia_inicio",
                "vigencia_fim", "versao", "template_version",
            ):
                continue
            if isinstance(v, str) and len(v) > 3:
                parts.append(f"{k}: {v[:500]}")
            elif isinstance(v, (int, float)) and k not in ("confianca", "confidence"):
                parts.append(f"{k}: {v}")
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Cohere batch embedder
# ---------------------------------------------------------------------------

MAX_BATCH_SIZE = 96  # Cohere limit per request


def _get_cohere_client():
    """Retorna CohereEmbeddingClient configurado."""
    from blu_llm_service import get_cohere_embedding_model

    try:
        return get_cohere_embedding_model()
    except ValueError as exc:
        logger.error("CO_API_KEY não configurada. Obtenha em: https://dashboard.cohere.com/api-keys")
        raise SystemExit(1) from exc


def _embed_batch(
    embedder, texts: list[str], max_retries: int = 3
) -> list[list[float]]:
    """Gera embeddings para um batch de textos com retry e backoff exponencial.

    Args:
        embedder: CohereEmbeddingClient instance.
        texts: Lista de textos (máx 96).
        max_retries: Número máximo de tentativas.

    Returns:
        Lista de embeddings (cada um lista de 384 floats).

    Raises:
        RuntimeError: Se todas as tentativas falharem.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            embeddings = embedder.embed_documents(texts)
            return embeddings
        except Exception as exc:
            last_error = exc
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(
                "Batch embedding falhou (tentativa %d/%d): %s. Retrying em %ds...",
                attempt + 1, max_retries, exc, wait,
            )
            time.sleep(wait)

    raise RuntimeError(
        f"Falha ao gerar embeddings após {max_retries} tentativas: {last_error}"
    )


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def count_rows_without_embedding(db, client_id: str | None = None) -> int:
    """Conta quantas linhas estão sem embedding."""
    query = db.table("shared_business_memory").select("id", count="exact").is_("embedding", "null")
    if client_id:
        query = query.eq("client_id", client_id)
    result = query.execute()
    return result.count if hasattr(result, "count") else len(result.data)


def backfill(
    db,
    embedder,
    client_id: str | None = None,
    batch_size: int = 96,
    dry_run: bool = False,
) -> dict:
    """Executa o backfill de embeddings.

    Args:
        db: Supabase client.
        embedder: CohereEmbeddingClient.
        client_id: Filtrar por cliente (opcional).
        batch_size: Tamanho do batch Cohere (max 96).
        dry_run: Se True, apenas conta, não modifica.

    Returns:
        Dict com estatísticas: {"total": N, "updated": N, "failed": N, "batches": N}.
    """
    if batch_size > MAX_BATCH_SIZE:
        logger.warning(
            "batch_size=%d excede o limite Cohere (%d). Reduzindo para %d.",
            batch_size, MAX_BATCH_SIZE, MAX_BATCH_SIZE,
        )
        batch_size = MAX_BATCH_SIZE

    total = count_rows_without_embedding(db, client_id)
    logger.info("Total rows without embedding: %d", total)

    if total == 0:
        logger.info("Nothing to backfill.")
        return {"total": 0, "updated": 0, "failed": 0, "batches": 0}

    if dry_run:
        num_batches = (total + batch_size - 1) // batch_size
        logger.info(
            "DRY-RUN: Would backfill %d rows in %d batches (batch_size=%d).",
            total, num_batches, batch_size,
        )
        return {"total": total, "updated": 0, "failed": 0, "batches": num_batches}

    # Paginar pelos registros sem embedding
    updated = 0
    failed = 0
    num_batches = 0
    page_size = batch_size  # cada página vira um batch Cohere
    offset = 0

    while True:
        query = (
            db.table("shared_business_memory")
            .select("id, entity_type, entity_name, key, value, category")
            .is_("embedding", "null")
            .order("id")
            .range(offset, offset + page_size - 1)
        )
        if client_id:
            query = query.eq("client_id", client_id)

        result = query.execute()
        rows = result.data
        if not rows:
            break

        # Gerar textos de embedding
        texts: list[str] = []
        row_ids: list[str] = []
        for row in rows:
            text = _build_embedding_text(
                entity_type=row.get("entity_type", ""),
                entity_name=row.get("entity_name", ""),
                key=row.get("key", ""),
                value=row.get("value"),
                category=row.get("category"),
            )
            texts.append(text)
            row_ids.append(row["id"])

        num_batches += 1
        t0 = time.monotonic()

        try:
            embeddings = _embed_batch(embedder, texts)
        except RuntimeError as exc:
            logger.error("Batch %d: FAILED — %s", num_batches, exc)
            failed += len(rows)
            offset += page_size
            continue

        elapsed = (time.monotonic() - t0) * 1000

        # Atualizar cada linha individualmente
        batch_updated = 0
        for row_id, embedding in zip(row_ids, embeddings):
            try:
                db.table("shared_business_memory").update(
                    {"embedding": embedding}
                ).eq("id", row_id).execute()
                batch_updated += 1
            except Exception as exc:
                logger.error("Falha ao atualizar row %s: %s", row_id, exc)
                failed += 1

        updated += batch_updated
        logger.info(
            "Batch %d: embedding %d rows... OK (%dms, %d updated, %d failed so far)",
            num_batches, len(rows), int(elapsed), updated, failed,
        )

        offset += page_size

        # Rate limiting: pausa entre batches
        if len(rows) == page_size:
            time.sleep(1.0)

    logger.info(
        "Backfill complete: %d rows updated, %d failed (total=%d, batches=%d).",
        updated, failed, total, num_batches,
    )

    return {
        "total": total,
        "updated": updated,
        "failed": failed,
        "batches": num_batches,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Backfill embeddings for shared_business_memory rows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run to count
  python scripts/backfill_shared_memory_embeddings.py --dry-run

  # Backfill all clients
  python scripts/backfill_shared_memory_embeddings.py

  # Backfill for a specific client
  python scripts/backfill_shared_memory_embeddings.py --client-id <UUID>

  # Custom batch size (max 96)
  python scripts/backfill_shared_memory_embeddings.py --batch-size 50
        """,
    )
    parser.add_argument(
        "--client-id",
        help="Client UUID to filter rows (optional, backfills all if omitted).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=96,
        help="Cohere batch size (default: 96, max: 96).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count and report, do not modify any rows.",
    )

    args = parser.parse_args()

    # Sanity check CO_API_KEY
    if not args.dry_run and not os.getenv("CO_API_KEY"):
        logger.error(
            "CO_API_KEY not set. Export it or use --dry-run to test.\n"
            "Obtain: https://dashboard.cohere.com/api-keys"
        )
        sys.exit(1)

    # Conectar Supabase
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client()

    # Embedder (skip if dry-run)
    embedder = None
    if not args.dry_run:
        embedder = _get_cohere_client()
        logger.info(
            "Cohere client: model=%s, dims=%d, batch_size=%d",
            embedder.MODEL, embedder.DIMENSIONS, args.batch_size,
        )

    if args.client_id:
        logger.info("Backfill for client_id=%s", args.client_id)
    else:
        logger.info("Backfill for ALL clients")

    logger.info("=" * 60)

    stats = backfill(
        db=db,
        embedder=embedder,
        client_id=args.client_id,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    logger.info("=" * 60)
    if args.dry_run:
        logger.info(
            "DRY-RUN: Would backfill %d rows in %d batches.",
            stats["total"], stats["batches"],
        )
    else:
        logger.info(
            "DONE: %d updated, %d failed out of %d total rows (%d batches).",
            stats["updated"], stats["failed"], stats["total"], stats["batches"],
        )

    if stats["failed"] > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
