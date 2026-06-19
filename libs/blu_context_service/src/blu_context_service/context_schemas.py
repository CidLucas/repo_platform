"""context_schemas.py — Shared Memory & Snapshot Context Schemas

Defines typed schemas (TypedDict / dataclass) for representing
snapshot dimensions and shared-memory facts consumed by the
BLU Context Service.

Status: SKELETON — implementar durante Issue #22 (Snapshot Templates).
"""

from __future__ import annotations

from typing import TypedDict


class MemoryEntry(TypedDict, total=False):
    """A single row from shared_business_memory."""

    id: str
    client_id: str
    entity_type: str
    entity_name: str
    key: str
    value: dict
    version: int
    source: str
    confidence: float
    metadata: dict
    created_at: str
    updated_at: str


class SnapshotDimension(TypedDict, total=False):
    """Dimensional snapshot — template structure (Fase 1)."""

    dimension: str
    label: str
    keys: list[str]
    template: dict
    version: int


class SnapshotTemplate(TypedDict, total=False):
    """Aggregate snapshot template (Fase 1)."""

    snapshot_id: str
    client_id: str
    dimensions: list[SnapshotDimension]
    created_at: str
    updated_at: str
