#!/usr/bin/env python3
"""
Seed platform knowledge documents into vector_db.

Uploads curated markdown files as platform-scoped documents (scope='platform',
client_id=NULL). Chunks, embeddings, and metadata enrichment happen
automatically via the existing pgmq pipeline (process-document EF → embed EF →
enrich-metadata EF).

Usage:
    # From repo root, with .env loaded:
    python scripts/seed_platform_knowledge.py

    # Dry-run (list files without uploading):
    python scripts/seed_platform_knowledge.py --dry-run

    # Reseed a specific category:
    python scripts/seed_platform_knowledge.py --category statistical_knowledge
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

# Ensure libs are importable when running from repo root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "libs" / "vizu_supabase_client" / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

from vizu_supabase_client import get_supabase_client  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Manifest ────────────────────────────────────────────────────

PLATFORM_KNOWLEDGE_DIR = ROOT_DIR / "seeds" / "platform_knowledge"
STORAGE_BUCKET = "knowledge-base"
STORAGE_PREFIX = "platform"


@dataclass
class PlatformDocument:
    """Describes a platform knowledge document to be seeded."""

    filename: str
    category: str
    description: str
    title: str


DOCUMENTS: list[PlatformDocument] = [
    PlatformDocument(
        filename="statistical_methods.md",
        category="statistical_knowledge",
        description=(
            "Guia completo de métodos estatísticos para análise de dados de "
            "negócios: medidas de tendência central, dispersão, distribuições, "
            "testes de hipóteses, correlação, regressão, séries temporais e "
            "detecção de outliers."
        ),
        title="Métodos Estatísticos para Análise de Dados de Negócios",
    ),
    PlatformDocument(
        filename="br_tax_guide.md",
        category="tax_knowledge",
        description=(
            "Guia de tributação brasileira para análise de dados: ICMS, "
            "PIS/COFINS, IPI, ISS, IRPJ, CSLL, Simples Nacional, NF-e, "
            "CFOPs, calendário fiscal e reforma tributária."
        ),
        title="Guia de Tributação Brasileira",
    ),
    PlatformDocument(
        filename="business_fundamentals.md",
        category="business_knowledge",
        description=(
            "Fundamentos de negócio e análise financeira: KPIs essenciais, "
            "unit economics (CAC, LTV, churn), DRE, balanço, DFC, "
            "forecasting, análise de rentabilidade, cohort, RFM e pricing."
        ),
        title="Fundamentos de Negócio e Análise Financeira",
    ),
    PlatformDocument(
        filename="data_analysis_playbook.md",
        category="task_specific",
        description=(
            "Playbook de análise de dados: metodologia passo a passo da "
            "definição do objetivo à comunicação de insights. EDA, modelagem, "
            "interpretação e visualização."
        ),
        title="Data Analysis Playbook",
    ),
]


# ── Helpers ─────────────────────────────────────────────────────


def file_content_hash(content: bytes) -> str:
    """SHA-256 hash of file content (for idempotent upserts)."""
    return hashlib.sha256(content).hexdigest()


def invoke_edge_function(client, function_name: str, body: dict) -> dict | None:
    """Invoke a Supabase Edge Function via the SDK."""
    try:
        response = client.functions.invoke(function_name, invoke_options={"body": body})
        logger.info("Edge Function '%s' invoked successfully", function_name)
        return response
    except Exception as e:
        logger.warning("Edge Function '%s' invocation error: %s", function_name, e)
        return None


# ── Core Logic ──────────────────────────────────────────────────


def seed_document(doc: PlatformDocument, *, dry_run: bool = False) -> str | None:
    """
    Upload a single platform knowledge document.

    1. Read file from disk
    2. Upload to Supabase Storage (knowledge-base/platform/{uuid}-{filename})
    3. INSERT into vector_db.documents with scope='platform'
    4. Invoke process-document Edge Function (chunking + embedding pipeline)

    Returns the document_id on success or None on failure/skip.
    """
    file_path = PLATFORM_KNOWLEDGE_DIR / doc.filename
    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        return None

    content = file_path.read_bytes()
    content_hash = file_content_hash(content)
    ext = file_path.suffix.lstrip(".")

    if dry_run:
        logger.info(
            "[DRY RUN] Would seed: %s (%s, %d bytes, %s)",
            doc.filename,
            doc.category,
            len(content),
            content_hash[:12],
        )
        return "dry-run"

    client = get_supabase_client()

    # ── Check if already seeded (idempotent by file_name + scope) ────
    existing = (
        client.schema("vector_db")
        .from_("documents")
        .select("id, file_name")
        .eq("file_name", doc.filename)
        .eq("scope", "platform")
        .limit(1)
        .execute()
    )
    if existing.data:
        logger.info(
            "Document '%s' already exists (id=%s). Skipping.",
            doc.filename,
            existing.data[0]["id"],
        )
        return "skipped"

    # ── 1. Upload to Storage ─────────────────────────────────────
    doc_uuid = str(uuid.uuid4())
    storage_path = f"{STORAGE_PREFIX}/{doc_uuid}-{doc.filename}"

    try:
        client.storage.from_(STORAGE_BUCKET).upload(storage_path, content)
        logger.info("Uploaded %s → %s/%s", doc.filename, STORAGE_BUCKET, storage_path)
    except Exception as e:
        logger.error("Storage upload failed for %s: %s", doc.filename, e)
        return None

    # ── 2. Insert document row ───────────────────────────────────
    try:
        result = (
            client.schema("vector_db")
            .from_("documents")
            .insert(
                {
                    "file_name": doc.filename,
                    "title": doc.title,
                    "file_type": ext,
                    "storage_path": storage_path,
                    "source": "upload",
                    "processing_mode": "simple",
                    "status": "processing",
                    "scope": "platform",
                    "category": doc.category,
                    "description": doc.description,
                    "client_id": None,
                }
            )
            .select("id")
            .single()
            .execute()
        )
        document_id = result.data["id"]
        logger.info("Created document row: %s (id=%s)", doc.filename, document_id)
    except Exception as e:
        logger.error("Document insert failed for %s: %s", doc.filename, e)
        # Clean up storage
        try:
            client.storage.from_(STORAGE_BUCKET).remove([storage_path])
        except Exception:
            pass
        return None

    # ── 3. Invoke process-document Edge Function ─────────────────
    invoke_edge_function(
        client,
        "process-document",
        {
            "document_id": document_id,
            "storage_path": storage_path,
            "client_id": None,  # Platform doc — no client
            "file_name": doc.filename,
            "file_type": ext,
        },
    )

    return document_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed platform knowledge documents into vector_db."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be uploaded without actually uploading.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Only seed documents of this category.",
    )
    args = parser.parse_args()

    docs = DOCUMENTS
    if args.category:
        docs = [d for d in docs if d.category == args.category]
        if not docs:
            logger.warning("No documents match category '%s'.", args.category)
            return

    logger.info(
        "Seeding %d platform knowledge document(s)%s...",
        len(docs),
        " (DRY RUN)" if args.dry_run else "",
    )

    results = {"seeded": 0, "skipped": 0, "failed": 0}

    for doc in docs:
        result = seed_document(doc, dry_run=args.dry_run)
        if result is None:
            results["failed"] += 1
        elif result == "dry-run":
            pass  # dry-run doesn't count
        elif result == "skipped":
            results["skipped"] += 1
        else:
            results["seeded"] += 1

    logger.info(
        "Done. Seeded: %d | Skipped (existing): %d | Failed: %d",
        results["seeded"],
        results["skipped"],
        results["failed"],
    )

    if not args.dry_run:
        logger.info(
            "Chunks will be created by the process-document Edge Function. "
            "Embeddings + metadata enrichment will follow via pgmq pipeline."
        )


if __name__ == "__main__":
    main()
