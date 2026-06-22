"""
Unit tests for backup_shared_memory routine (Issue #37, T5.5).

Tests the backup lifecycle without hitting a real Supabase instance.
Covers: dump, compression, sha256, upload retry, checkpoint, prune.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_supabase_client() -> MagicMock:
    """Return a mock Supabase client with working table select and storage chains."""

    # Storage mock
    storage = MagicMock()
    storage.from_ = MagicMock(return_value=storage)
    storage.upload = MagicMock(return_value=MagicMock())
    storage.download = MagicMock(return_value=MagicMock())
    storage.list = MagicMock(return_value=[])
    storage.remove = MagicMock(return_value=MagicMock())

    # RPC mock
    rpc_execute = MagicMock()
    rpc_execute.execute.return_value = MagicMock(data=[])

    rpc_chain = MagicMock()
    rpc_chain.rpc.return_value = rpc_execute

    # Table mock — paginated select
    def _make_select_chain(rows: list[dict]) -> MagicMock:
        chain = MagicMock()
        chain.table.return_value = chain
        chain.select.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain

        # Execute returns the first page, then empty
        call_count = [0]

        def _execute():
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(data=rows)
            return MagicMock(data=[])

        chain.execute.side_effect = _execute
        return chain

    client = MagicMock()
    client.storage = storage
    client.rpc = rpc_chain
    # We'll configure table() per-test since it depends on expected rows

    return client, storage


def _sample_rows(n: int = 50) -> list[dict]:
    """Generate sample shared_business_memory records."""
    now = datetime.now(UTC).isoformat()
    return [
        {
            "id": i,
            "client_id": f"00000000-0000-0000-0000-{i:012d}",
            "entity_type": "snapshot" if i % 3 == 0 else "fact",
            "entity_name": "financeiro:semanal" if i % 2 == 0 else "clientes:diario",
            "key": f"2026-06-{(i % 28) + 1:02d}T10:00:00Z",
            "value": {"data": f"record_{i}", "size": i * 100},
            "source": "test",
            "confidence": 0.9,
            "created_at": now,
            "updated_at": now,
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Test: Dump all records
# ---------------------------------------------------------------------------


class TestDumpAllRecords:
    """Logical dump fetches all records from shared_business_memory."""

    @pytest.mark.asyncio
    async def test_dump_returns_all_records(self):
        """Single-page dump returns all records."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _dump_all_records,
        )

        rows = _sample_rows(10)
        client = MagicMock()

        # Setup table select chain
        chain = MagicMock()
        client.table.return_value = chain
        chain.select.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        chain.execute.return_value = MagicMock(data=rows)

        result = await _dump_all_records(client)
        assert len(result) == 10
        assert result == rows

    @pytest.mark.asyncio
    async def test_dump_paginated(self):
        """Multi-page dump concatenates all pages using full 1000-item pages."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _dump_all_records,
        )

        page1 = _sample_rows(1000)
        page2 = _sample_rows(500)
        client = MagicMock()

        chain = MagicMock()
        client.table.return_value = chain
        chain.select.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain

        calls = [MagicMock(data=page1), MagicMock(data=page2), MagicMock(data=[])]
        chain.execute.side_effect = calls

        result = await _dump_all_records(client)
        assert len(result) == 1500

    @pytest.mark.asyncio
    async def test_dump_empty_table(self):
        """Empty table returns empty list."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _dump_all_records,
        )

        client = MagicMock()
        chain = MagicMock()
        client.table.return_value = chain
        chain.select.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        chain.execute.return_value = MagicMock(data=[])

        result = await _dump_all_records(client)
        assert result == []


# ---------------------------------------------------------------------------
# Test: Compression and SHA256
# ---------------------------------------------------------------------------


class TestCompressionAndHash:
    """Gzip compression and SHA256 computation."""

    def test_gzip_compresses_json(self):
        """JSON data is compressed with gzip."""
        rows = _sample_rows(5)
        dump_json = json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
        compressed = gzip.compress(dump_json, compresslevel=6)

        assert len(compressed) > 0
        assert len(compressed) < len(dump_json)  # Should compress repetitive data

    def test_sha256_matches(self):
        """SHA256 of compressed data is deterministic."""
        rows = _sample_rows(5)
        dump_json = json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
        compressed = gzip.compress(dump_json, compresslevel=6)

        h1 = hashlib.sha256(compressed).hexdigest()
        h2 = hashlib.sha256(compressed).hexdigest()
        assert h1 == h2
        assert len(h1) == 64

    def test_decompress_roundtrip(self):
        """Compressed data decompresses back to original JSON."""
        rows = _sample_rows(5)
        dump_json = json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
        compressed = gzip.compress(dump_json, compresslevel=6)
        decompressed = gzip.decompress(compressed)

        assert decompressed == dump_json
        restored = json.loads(decompressed)
        assert len(restored) == 5


# ---------------------------------------------------------------------------
# Test: Checkpoint writing
# ---------------------------------------------------------------------------


class TestCheckpointWriting:
    """Checkpoint is saved to shared_business_memory after backup."""

    @pytest.mark.asyncio
    async def test_checkpoint_via_rpc(self):
        """RPC upsert_routine_checkpoint is called with correct parameters."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
            _save_checkpoint,
            ROUTINE_ID,
        )

        client, _ = _make_mock_supabase_client()

        result = BackupResult(
            exec_id="test-exec-123",
            status="success",
            row_count=100,
            size_bytes=5000,
            sha256="abc123def456",
            dump_path="2026-06-22/dump.json.gz",
        )
        start = datetime.now(UTC)

        await _save_checkpoint(client, result, start)

        # Verify RPC was called
        client.rpc.assert_called_once()
        rpc_call_args = client.rpc.call_args
        assert rpc_call_args[0][0] == "upsert_routine_checkpoint"

        rpc_params = rpc_call_args[0][1]  # second positional arg (the dict)
        assert rpc_params["p_routine_id"] == ROUTINE_ID
        assert rpc_params["p_exec_id"] == "test-exec-123"
        assert rpc_params["p_step_number"] == 1

        state = rpc_params["p_state_value"]
        assert state["status"] == "completed"
        assert state["row_count"] == 100
        assert state["size_bytes"] == 5000
        assert state["sha256"] == "abc123def456"
        assert state["dump_path"] == "2026-06-22/dump.json.gz"

    @pytest.mark.asyncio
    async def test_checkpoint_fallback_on_rpc_failure(self):
        """When RPC fails, checkpoint falls back to direct INSERT."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
            _save_checkpoint,
        )

        client, _ = _make_mock_supabase_client()

        # Make RPC call itself fail (client.rpc("upsert_routine_checkpoint", ...) raises)
        client.rpc = MagicMock(side_effect=RuntimeError("RPC unavailable"))
        client.table = MagicMock()

        # Setup table select → execute to return existing row
        select_chain = MagicMock()
        client.table.return_value = select_chain
        select_chain.select.return_value = select_chain
        select_chain.eq.return_value = select_chain
        select_chain.limit.return_value = select_chain
        select_chain.execute.return_value = MagicMock(
            data=[{"id": 99}]
        )

        # Setup update chain
        update_chain = MagicMock()
        client.table.return_value = select_chain  # for existing check
        # Let's just mock the direct path
        with patch(
            "services.routine_engine.src.routines.backup_shared_memory._save_checkpoint_direct",
        ) as mock_direct:
            result = BackupResult(exec_id="fallback-test")
            start = datetime.now(UTC)

            await _save_checkpoint(client, result, start)

            mock_direct.assert_called_once()


# ---------------------------------------------------------------------------
# Test: Upload with retry
# ---------------------------------------------------------------------------


class TestUploadWithRetry:
    """Upload to Supabase Storage retries on failure."""

    @pytest.mark.asyncio
    async def test_upload_succeeds_first_attempt(self):
        """Upload succeeds on first try."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _upload_with_retry,
        )

        client, storage = _make_mock_supabase_client()
        storage.upload.return_value = MagicMock()

        success = await _upload_with_retry(client, "2026-06-22/dump.json.gz", b"data")
        assert success is True
        assert storage.upload.call_count == 1

    @pytest.mark.asyncio
    async def test_upload_retries_then_fails(self):
        """Upload retries 3 times then returns False."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _upload_with_retry,
        )

        client, storage = _make_mock_supabase_client()
        storage.upload.side_effect = RuntimeError("Network error")

        # Patch asyncio.sleep to avoid real delay
        with patch("asyncio.sleep", new_callable=AsyncMock):
            success = await _upload_with_retry(
                client, "2026-06-22/dump.json.gz", b"data"
            )

        assert success is False
        assert storage.upload.call_count == 3

    @pytest.mark.asyncio
    async def test_upload_succeeds_on_retry(self):
        """Upload succeeds on second attempt."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _upload_with_retry,
        )

        client, storage = _make_mock_supabase_client()
        storage.upload.side_effect = [
            RuntimeError("Attempt 1 fail"),
            MagicMock(),  # Success on attempt 2
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            success = await _upload_with_retry(
                client, "2026-06-22/dump.json.gz", b"data"
            )

        assert success is True
        assert storage.upload.call_count == 2


# ---------------------------------------------------------------------------
# Test: Run backup (full lifecycle, dry-run)
# ---------------------------------------------------------------------------


class TestRunBackupDryRun:
    """Full backup lifecycle in dry-run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_dumps_and_computes_hash(self):
        """Dry-run dumps records, computes hash, skips upload and checkpoint."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            run_backup,
        )

        rows = _sample_rows(20)
        client, _ = _make_mock_supabase_client()

        # Setup table chain for dump
        select_chain = MagicMock()
        client.table.return_value = select_chain
        select_chain.select.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.range.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=rows)

        # RPC for checkpoint (should NOT be called in dry-run)
        rpc_chain = MagicMock()
        rpc_chain.rpc.return_value = MagicMock()
        client.rpc = rpc_chain

        result = await run_backup(db=client, dry_run=True)

        assert result.row_count == 20
        assert result.size_bytes > 0
        assert len(result.sha256) == 64
        assert result.status == "success"
        assert result.dump_path != ""
        assert result.success is True

        # Verify no upload happened
        client.storage.upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_empty_table(self):
        """Dry-run with empty table still succeeds."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            run_backup,
        )

        client, _ = _make_mock_supabase_client()

        # Empty table
        select_chain = MagicMock()
        client.table.return_value = select_chain
        select_chain.select.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.range.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[])

        # RPC mock
        rpc_chain = MagicMock()
        rpc_chain.rpc.return_value = MagicMock()
        client.rpc = rpc_chain

        result = await run_backup(db=client, dry_run=True)

        assert result.row_count == 0
        assert result.success is True


# ---------------------------------------------------------------------------
# Test: BackupResult dataclass
# ---------------------------------------------------------------------------


class TestBackupResult:
    """BackupResult dataclass behavior."""

    def test_defaults(self):
        """Default values are correct."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
        )

        result = BackupResult()
        assert result.status == "success"
        assert result.row_count == 0
        assert result.size_bytes == 0
        assert result.sha256 == ""
        assert result.error is None
        assert result.exec_id != ""  # Auto-generated UUID

    def test_success_property(self):
        """Success property reflects status and error."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
        )

        ok = BackupResult(status="success")
        assert ok.success is True

        failed = BackupResult(status="failed", error="Something broke")
        assert failed.success is False

        timeout = BackupResult(status="timeout")
        assert timeout.success is False


# ---------------------------------------------------------------------------
# Test: Prune daily backups
# ---------------------------------------------------------------------------


class TestPruneDailyBackups:
    """Pruning of old daily backups."""

    @pytest.mark.asyncio
    async def test_prune_removes_old_backups(self):
        """Backups older than 30 days are removed."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _prune_daily_backups,
        )

        client, storage = _make_mock_supabase_client()

        # List with old and recent backups
        old_date = (datetime.now(UTC) - timedelta(days=35)).strftime("%Y-%m-%d")
        recent_date = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        storage.list.return_value = [
            {"name": f"{old_date}/dump.json.gz", "created_at": old_date},
            {"name": f"{recent_date}/dump.json.gz", "created_at": recent_date},
            {"name": f"{today}/dump.json.gz", "created_at": today},
            {"name": "not-a-backup/file.txt", "created_at": today},
        ]

        pruned = await _prune_daily_backups(client, today)
        assert pruned == 1  # Only the 35-day-old backup should be pruned
        assert storage.remove.call_count == 1

    @pytest.mark.asyncio
    async def test_prune_no_old_backups(self):
        """Nothing pruned when all backups are recent."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _prune_daily_backups,
        )

        client, storage = _make_mock_supabase_client()

        recent = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%d")
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        storage.list.return_value = [
            {"name": f"{recent}/dump.json.gz", "created_at": recent},
            {"name": f"{today}/dump.json.gz", "created_at": today},
        ]

        pruned = await _prune_daily_backups(client, today)
        assert pruned == 0
        storage.remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_prune_handles_errors_gracefully(self):
        """Prune failures are logged but not raised."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _prune_daily_backups,
        )

        client, storage = _make_mock_supabase_client()
        storage.list.side_effect = RuntimeError("Storage unavailable")

        pruned = await _prune_daily_backups(client, "2026-06-22")
        assert pruned == 0  # Non-fatal


# ---------------------------------------------------------------------------
# Test: Error handling in run_backup
# ---------------------------------------------------------------------------


class TestRunBackupErrorHandling:
    """run_backup handles errors gracefully."""

    @pytest.mark.asyncio
    async def test_dump_failure_sets_error_status(self):
        """When dump fails, result has status=failed and error set."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            run_backup,
        )

        client, _ = _make_mock_supabase_client()

        # Make select chain fail
        select_chain = MagicMock()
        client.table.return_value = select_chain
        select_chain.select.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.range.return_value = select_chain
        select_chain.execute.side_effect = RuntimeError("DB connection lost")

        result = await run_backup(db=client, dry_run=True)

        assert result.status == "failed"
        assert result.error is not None
        assert "RuntimeError" in result.error
        assert result.success is False
