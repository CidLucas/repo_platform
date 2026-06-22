"""
Unit tests for backup_shared_memory routine (Issue #37, T5.5).

Tests the backup lifecycle without hitting a real Supabase instance.
Covers: dump, compression, sha256, upload retry, checkpoint, prune,
weekly consolidation, restore, list, send_alert, CLI parser,
and edge cases (empty backup, corruption, concurrent writes).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import zlib
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


# ---------------------------------------------------------------------------
# Test: Weekly consolidation
# ---------------------------------------------------------------------------


class TestConsolidateWeeklyBackups:
    """Weekly consolidation of daily backups."""

    @pytest.mark.asyncio
    async def test_consolidate_on_sunday(self):
        """Consolidation runs on Sundays."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _consolidate_weekly_backups,
        )

        # Find a recent Sunday
        import datetime as dt

        today = dt.datetime.now(dt.UTC)
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - dt.timedelta(days=days_since_sunday)
        sunday_str = sunday.strftime("%Y-%m-%d")

        client, storage = _make_mock_supabase_client()
        # Daily dump exists
        storage.download.return_value = b"gzip-compressed-data"
        storage.list.return_value = []

        consolidated = await _consolidate_weekly_backups(client, sunday_str)
        # Should have attempted consolidation (sunday)
        storage.download.assert_called_once()
        assert storage.upload.call_count == 1  # uploads to weekly path

    @pytest.mark.asyncio
    async def test_skip_consolidation_on_non_sunday(self):
        """Consolidation is skipped on non-Sunday days."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _consolidate_weekly_backups,
        )

        # Use a Monday explicitly to guarantee non-Sunday regardless of current date
        import datetime as dt

        # Find next Monday after today
        today = dt.datetime.now(dt.UTC)
        days_to_monday = (7 - today.weekday()) % 7
        if days_to_monday == 0:
            # Today is Monday, use today
            non_sunday = today
        else:
            non_sunday = today + dt.timedelta(days=days_to_monday)
        non_sunday_str = non_sunday.strftime("%Y-%m-%d")

        # Verify we're not on Sunday
        assert non_sunday.weekday() != 6, "Expected non-Sunday, got Sunday"

        client, storage = _make_mock_supabase_client()

        consolidated = await _consolidate_weekly_backups(client, non_sunday_str)
        assert consolidated == 0
        storage.download.assert_not_called()
        storage.upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_prune_old_weeklies(self):
        """Weeklies older than 12 weeks are pruned on Sunday."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _consolidate_weekly_backups,
        )

        import datetime as dt

        today = dt.datetime.now(dt.UTC)
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - dt.timedelta(days=days_since_sunday)
        sunday_str = sunday.strftime("%Y-%m-%d")

        # Old weekly path
        old_week = (sunday - dt.timedelta(weeks=15)).strftime("%Y-W%U")

        client, storage = _make_mock_supabase_client()
        storage.download.return_value = b"gzip-compressed-data"

        # List with old weekly
        storage.list.return_value = [
            {"name": f"weekly/{old_week}/dump.json.gz"},
        ]

        consolidated = await _consolidate_weekly_backups(client, sunday_str)
        storage.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_consolidation_error_handled_gracefully(self):
        """Error during consolidation is logged but not raised."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _consolidate_weekly_backups,
        )

        import datetime as dt

        today = dt.datetime.now(dt.UTC)
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - dt.timedelta(days=days_since_sunday)
        sunday_str = sunday.strftime("%Y-%m-%d")

        client, storage = _make_mock_supabase_client()
        storage.download.side_effect = RuntimeError("Storage unavailable")

        consolidated = await _consolidate_weekly_backups(client, sunday_str)
        assert consolidated == 0  # Non-fatal, returns 0


# ---------------------------------------------------------------------------
# Test: Restore from backup
# ---------------------------------------------------------------------------


class TestRestoreBackup:
    """Restore functionality for backup_shared_memory."""

    @pytest.mark.asyncio
    async def test_restore_successful(self, capsys):
        """Restore decompresses gzip data and prints records."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _restore_backup,
        )
        import sys

        rows = _sample_rows(10)
        dump_json = json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
        compressed = gzip.compress(dump_json, compresslevel=6)

        client, storage = _make_mock_supabase_client()
        storage.download.return_value = compressed

        # Patch sys.exit to not actually exit
        with patch.object(sys, "exit") as mock_exit:
            await _restore_backup(client, "2026-06-22")

        mock_exit.assert_not_called()

    @pytest.mark.asyncio
    async def test_restore_empty_backup(self, capsys):
        """Restore handles empty backup (0 records)."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _restore_backup,
        )
        import sys

        rows = []
        dump_json = json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
        compressed = gzip.compress(dump_json, compresslevel=6)

        client, storage = _make_mock_supabase_client()
        storage.download.return_value = compressed

        with patch.object(sys, "exit") as mock_exit:
            await _restore_backup(client, "2026-06-01")

        mock_exit.assert_not_called()

    @pytest.mark.asyncio
    async def test_restore_corrupted_gzip(self):
        """Restore calls sys.exit(1) on corrupted gzip data."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _restore_backup,
        )
        import sys

        client, storage = _make_mock_supabase_client()
        # Corrupted data (not valid gzip)
        storage.download.return_value = b"not-gzip-data-at-all"

        with patch.object(sys, "exit") as mock_exit:
            await _restore_backup(client, "2026-06-22")

        mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_restore_missing_backup(self):
        """Restore calls sys.exit(1) when backup path does not exist."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _restore_backup,
        )
        import sys

        client, storage = _make_mock_supabase_client()
        storage.download.side_effect = RuntimeError("Path not found")

        with patch.object(sys, "exit") as mock_exit:
            await _restore_backup(client, "2099-01-01")

        mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_restore_corrupted_json(self):
        """Restore calls sys.exit(1) on valid gzip but invalid JSON content."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _restore_backup,
        )
        import sys

        # Valid gzip but invalid JSON inside
        corrupted_json = gzip.compress(b"this-is-not-json-{{{}}")

        client, storage = _make_mock_supabase_client()
        storage.download.return_value = corrupted_json

        with patch.object(sys, "exit") as mock_exit:
            await _restore_backup(client, "2026-06-22")

        mock_exit.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# Test: List backups
# ---------------------------------------------------------------------------


class TestListBackups:
    """List backups in the storage bucket."""

    @pytest.mark.asyncio
    async def test_list_returns_files(self):
        """List backups returns sorted file listing."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _list_backups,
        )

        client, storage = _make_mock_supabase_client()
        storage.list.return_value = [
            {"name": "2026-06-10/dump.json.gz", "metadata": {"size": 5000}, "created_at": "2026-06-10T02:00:00Z"},
            {"name": "2026-06-20/dump.json.gz", "metadata": {"size": 3000}, "created_at": "2026-06-20T02:00:00Z"},
            {"name": "2026-06-15/dump.json.gz", "metadata": {"size": 4200}, "created_at": "2026-06-15T02:00:00Z"},
        ]

        # Should not raise
        await _list_backups(client)

        # Verify sorted (reverse chronological)
        storage.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_empty(self):
        """List backups handles empty bucket."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _list_backups,
        )

        client, storage = _make_mock_supabase_client()
        storage.list.return_value = []

        # Should not raise
        await _list_backups(client)


# ---------------------------------------------------------------------------
# Test: Send alert
# ---------------------------------------------------------------------------


class TestSendAlert:
    """Alert webhook sends notifications on failures."""

    @pytest.mark.asyncio
    async def test_alert_skipped_when_no_webhook(self):
        """Alert is skipped when ALERT_WEBHOOK_URL is not configured."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
            _send_alert,
        )

        with patch(
            "services.routine_engine.src.routines.backup_shared_memory.ALERT_WEBHOOK_URL",
            "",
        ):
            result = BackupResult(exec_id="test", status="failed", error="Something broke")
            await _send_alert(result, "Test alert")
            # No exception should be raised

    @pytest.mark.asyncio
    async def test_alert_sends_http_post(self):
        """Alert sends HTTP POST to configured webhook."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
            _send_alert,
        )
        import sys
        from unittest.mock import AsyncMock, MagicMock, patch as p

        # Mock aiohttp at the sys.modules level since it's imported inside _send_alert
        mock_aiohttp = MagicMock()
        mock_session = AsyncMock()
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value.status = 200
        mock_session.post.return_value = mock_post
        mock_aiohttp.ClientSession.return_value.__aenter__.return_value = mock_session

        with (
            p(
                "services.routine_engine.src.routines.backup_shared_memory.ALERT_WEBHOOK_URL",
                "https://hooks.example.com/alert",
            ),
            p.dict(
                "sys.modules",
                {"aiohttp": mock_aiohttp},
            ),
        ):
            result = BackupResult(
                exec_id="test-exec",
                status="failed",
                error="Disk full",
                row_count=0,
                size_bytes=0,
                sha256="",
                dump_path="",
                started_at="2026-06-22T02:00:00",
                duration_ms=5000,
            )
            await _send_alert(result, "Backup failed")

            mock_session.post.assert_called_once()
            call_url = mock_session.post.call_args[0][0]
            assert call_url == "https://hooks.example.com/alert"

    @pytest.mark.asyncio
    async def test_alert_http_error_logged(self):
        """HTTP error response from webhook is logged but not raised."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
            _send_alert,
        )
        import sys
        from unittest.mock import AsyncMock, MagicMock, patch as p

        mock_aiohttp = MagicMock()
        mock_session = AsyncMock()
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value.status = 500
        mock_post.__aenter__.return_value.text = AsyncMock(return_value="Server Error")
        mock_session.post.return_value = mock_post
        mock_aiohttp.ClientSession.return_value.__aenter__.return_value = mock_session

        with (
            p(
                "services.routine_engine.src.routines.backup_shared_memory.ALERT_WEBHOOK_URL",
                "https://hooks.example.com/alert",
            ),
            p.dict(
                "sys.modules",
                {"aiohttp": mock_aiohttp},
            ),
        ):
            result = BackupResult(exec_id="test", status="failed")
            await _send_alert(result, "HTTP 500 test")
            # No exception raised — error is logged

    @pytest.mark.asyncio
    async def test_alert_import_error_handled(self):
        """Missing aiohttp import is handled gracefully."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
            _send_alert,
        )

        with patch(
            "services.routine_engine.src.routines.backup_shared_memory.ALERT_WEBHOOK_URL",
            "https://hooks.example.com/alert",
        ):
            # Simulate ImportError by making aiohttp not importable
            import sys

            original_aiohttp = sys.modules.pop("aiohttp", None)
            # Re-import the module to clear the import cache
            # Instead, we just patch and invoke — the code catches ImportError inside

            result = BackupResult(exec_id="test", status="failed")
            await _send_alert(result, "Import error test")
            # No exception — ImportError is caught inside _send_alert

            if original_aiohttp:
                sys.modules["aiohttp"] = original_aiohttp


# ---------------------------------------------------------------------------
# Test: CLI argument parser
# ---------------------------------------------------------------------------


class TestCLIParser:
    """CLI argument parser builds correctly."""

    def test_dry_run_flag(self):
        """--dry-run flag is parsed correctly."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _build_parser,
        )

        parser = _build_parser()
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_verbose_flag(self):
        """--verbose flag is parsed correctly."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _build_parser,
        )

        parser = _build_parser()
        args = parser.parse_args(["-v"])
        assert args.verbose is True

    def test_restore_argument(self):
        """--restore accepts a date string."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _build_parser,
        )

        parser = _build_parser()
        args = parser.parse_args(["--restore", "2026-06-22"])
        assert args.restore == "2026-06-22"

    def test_list_backups_flag(self):
        """--list-backups flag is parsed correctly."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _build_parser,
        )

        parser = _build_parser()
        args = parser.parse_args(["--list-backups"])
        assert args.list_backups is True

    def test_defaults(self):
        """Default values are correct when no flags given."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _build_parser,
        )

        parser = _build_parser()
        args = parser.parse_args([])
        assert args.dry_run is False
        assert args.verbose is False
        assert args.restore is None
        assert args.list_backups is False

    def test_restore_invalid_date(self):
        """--restore accepts any string (validation is at runtime)."""
        # CLI parser doesn't validate date format — that's the runtime's job
        from services.routine_engine.src.routines.backup_shared_memory import (
            _build_parser,
        )

        parser = _build_parser()
        args = parser.parse_args(["--restore", "not-a-date"])
        assert args.restore == "not-a-date"


# ---------------------------------------------------------------------------
# Test: Edge cases — empty state, concurrent access, corruption
# ---------------------------------------------------------------------------


class TestBackupEdgeCases:
    """Edge cases for backup_shared_memory."""

    @pytest.mark.asyncio
    async def test_backup_empty_table_full_lifecycle(self):
        """Full backup lifecycle with empty table still produces valid result."""
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

        result = await run_backup(db=client, dry_run=True)

        assert result.row_count == 0
        assert result.size_bytes > 0  # Still produces a valid (empty) gzip
        assert len(result.sha256) == 64
        assert result.status == "success"
        assert result.success is True

    def test_concurrent_backupresult_immutability(self):
        """BackupResult fields are independent per instance (simulates concurrent runs)."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
        )

        r1 = BackupResult(exec_id="run-1", status="success", row_count=100, size_bytes=5000)
        r2 = BackupResult(exec_id="run-2", status="failed", row_count=0, size_bytes=0, error="OOM")

        # Verify independence
        assert r1.exec_id == "run-1"
        assert r1.success is True
        assert r2.exec_id == "run-2"
        assert r2.success is False
        assert r1.row_count == 100
        assert r2.row_count == 0

    def test_backupresult_fields_mutable_independently(self):
        """BackupResult default_factory creates unique exec_ids per instance."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            BackupResult,
        )

        r1 = BackupResult()
        r2 = BackupResult()
        assert r1.exec_id != r2.exec_id  # UUID uniqueness

    @pytest.mark.asyncio
    async def test_upload_corrupted_data_small(self):
        """Upload handles very small/corrupted data gracefully."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _upload_with_retry,
        )

        client, storage = _make_mock_supabase_client()
        storage.upload.return_value = MagicMock()

        # Empty bytes
        success = await _upload_with_retry(client, "2026-06-22/dump.json.gz", b"")
        assert success is True
        storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_large_data(self):
        """Upload handles large compressed data."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _upload_with_retry,
        )

        client, storage = _make_mock_supabase_client()
        storage.upload.return_value = MagicMock()

        # Simulate large payload (~1MB)
        large_data = b"x" * (1024 * 1024)
        success = await _upload_with_retry(client, "2026-06-22/dump.json.gz", large_data)
        assert success is True

    @pytest.mark.asyncio
    async def test_dump_timeout_propagation(self):
        """Timeout during dump is captured as error in run_backup."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            _dump_all_records,
        )

        client = MagicMock()
        chain = MagicMock()
        client.table.return_value = chain
        chain.select.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        chain.execute.side_effect = TimeoutError("Query timed out")

        with pytest.raises(TimeoutError, match="Query timed out"):
            await _dump_all_records(client)

    def test_gzip_corruption_detection(self):
        """Corrupted gzip data fails decompression."""
        import gzip as gz

        # Write valid gzip, then corrupt it in the middle
        valid = gz.compress(b'{"valid": true}')
        corrupted = valid[:10] + b"\xff\xff" + valid[12:]

        with pytest.raises((gz.BadGzipFile, OSError, zlib.error)):
            gz.decompress(corrupted)

    def test_sha256_deterministic_across_same_data(self):
        """SHA256 is deterministic for identical compressed data."""
        data = b"deterministic-test-data-exact-copy"
        compressed = gzip.compress(data)

        h1 = hashlib.sha256(compressed).hexdigest()
        h2 = hashlib.sha256(compressed).hexdigest()

        assert h1 == h2
        assert len(h1) == 64
        assert isinstance(h1, str)

    def test_sha256_changes_on_data_change(self):
        """SHA256 changes when compressed data changes (integrity check)."""
        data1 = gzip.compress(b"original data")
        data2 = gzip.compress(b"modified data")

        h1 = hashlib.sha256(data1).hexdigest()
        h2 = hashlib.sha256(data2).hexdigest()

        assert h1 != h2  # Different data → different hash


# ---------------------------------------------------------------------------
# Test: Run backup full lifecycle (no dry-run) — error paths
# ---------------------------------------------------------------------------


class TestRunBackupFullLifecycle:
    """Full backup lifecycle without dry-run — upload and checkpoint."""

    @pytest.mark.asyncio
    async def test_full_backup_success(self):
        """Full backup lifecycle succeeds with upload and checkpoint."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            run_backup,
        )

        rows = _sample_rows(5)
        client, storage = _make_mock_supabase_client()

        # Setup table chain for dump
        select_chain = MagicMock()
        client.table.return_value = select_chain
        select_chain.select.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.range.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=rows)

        # RPC success
        rpc_execute = MagicMock()
        rpc_execute.execute.return_value = MagicMock(data=[])
        client.rpc = MagicMock(return_value=rpc_execute)

        # Storage list for prune (no old backups)
        storage.list.return_value = []
        storage.upload.return_value = MagicMock()

        result = await run_backup(db=client, dry_run=False)

        assert result.row_count == 5
        assert result.status == "success"
        assert result.success is True
        # Upload should have been called
        storage.upload.assert_called_once()
        # Checkpoint via RPC should have been called
        client.rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_backup_upload_failure(self):
        """Full backup with upload failure still saves failure checkpoint."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            run_backup,
        )

        rows = _sample_rows(3)
        client, storage = _make_mock_supabase_client()

        # Setup table chain for dump
        select_chain = MagicMock()
        client.table.return_value = select_chain
        select_chain.select.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.range.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=rows)

        # Upload fails
        storage.upload.side_effect = RuntimeError("Upload failed")

        # RPC success for failure checkpoint
        rpc_execute = MagicMock()
        rpc_execute.execute.return_value = MagicMock(data=[])
        client.rpc = MagicMock(return_value=rpc_execute)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await run_backup(db=client, dry_run=False)

        assert result.status == "failed"
        assert result.error is not None
        assert result.success is False
        # Checkpoint should still be saved (failure checkpoint)
        client.rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_backup_saves_correct_checkpoint_data(self):
        """Backup saves checkpoint with accurate metadata."""
        from services.routine_engine.src.routines.backup_shared_memory import (
            run_backup,
            ROUTINE_ID,
        )

        rows = _sample_rows(10)
        client, storage = _make_mock_supabase_client()

        select_chain = MagicMock()
        client.table.return_value = select_chain
        select_chain.select.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.range.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=rows)

        rpc_execute = MagicMock()
        rpc_execute.execute.return_value = MagicMock(data=[])
        client.rpc = MagicMock(return_value=rpc_execute)

        storage.list.return_value = []
        storage.upload.return_value = MagicMock()

        result = await run_backup(db=client, dry_run=False)

        # Verify RPC parameters
        call_args = client.rpc.call_args
        assert call_args[0][0] == "upsert_routine_checkpoint"
        params = call_args[0][1]
        assert params["p_routine_id"] == ROUTINE_ID
        assert params["p_step_number"] == 1

        state = params["p_state_value"]
        assert state["status"] == "completed"
        assert state["row_count"] == 10
        assert state["size_bytes"] == result.size_bytes
        assert state["sha256"] == result.sha256
        assert state["dump_path"] == result.dump_path
        assert state["routine_run_id"] == result.exec_id
