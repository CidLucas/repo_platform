#!/usr/bin/env python3
"""
Database Connection Monitor & Auto-Kill Script

Prevents connection pool exhaustion by automatically terminating:
1. Transactions idle > 15 minutes
2. Queries running > 5 minutes (except whitelisted)

Run as a cron job every 5 minutes:
    */5 * * * * /path/to/monitor_kill_idle_connections.py

Or as a background service:
    docker-compose up -d connection_monitor
"""

import os
import sys
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration
IDLE_TRANSACTION_TIMEOUT_MINUTES = 15
LONG_QUERY_TIMEOUT_MINUTES = 5
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Whitelist for queries that can run longer (migrations, recomputes)
QUERY_WHITELIST_PATTERNS = [
    "CREATE INDEX",
    "REINDEX",
    "VACUUM",
    "pg_dump",
    "-- LONG_RUNNING_OK",  # Add this comment to long-running queries
]


def get_db_connection():
    """Get database connection from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    return psycopg2.connect(database_url)


def find_stuck_connections(conn):
    """Find connections that should be terminated."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Find idle-in-transaction connections > threshold
        cur.execute(
            """
            SELECT
                pid,
                usename,
                application_name,
                state,
                wait_event_type,
                wait_event,
                query_start,
                state_change,
                NOW() - state_change AS idle_duration,
                LEFT(query, 200) AS query_preview
            FROM pg_stat_activity
            WHERE state = 'idle in transaction'
              AND pid != pg_backend_pid()
              AND NOW() - state_change > INTERVAL '%s minutes'
            ORDER BY state_change;
            """,
            (IDLE_TRANSACTION_TIMEOUT_MINUTES,),
        )
        idle_transactions = cur.fetchall()

        # Find long-running active queries > threshold
        cur.execute(
            """
            SELECT
                pid,
                usename,
                application_name,
                state,
                query_start,
                NOW() - query_start AS query_duration,
                query AS query_preview
            FROM pg_stat_activity
            WHERE state = 'active'
              AND pid != pg_backend_pid()
              AND NOW() - query_start > INTERVAL '%s minutes'
            ORDER BY query_start;
            """,
            (LONG_QUERY_TIMEOUT_MINUTES,),
        )
        long_queries = cur.fetchall()

        # Filter out whitelisted queries
        long_queries = [
            q
            for q in long_queries
            if not any(pattern in q["query_preview"] for pattern in QUERY_WHITELIST_PATTERNS)
        ]

        return idle_transactions, long_queries


def kill_connection(conn, pid, reason):
    """Terminate a backend connection."""
    with conn.cursor() as cur:
        cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
        result = cur.fetchone()[0]
        return result


def format_duration(duration):
    """Format timedelta as human-readable string."""
    if duration is None:
        return "unknown"
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {seconds}s"


def main():
    """Main monitoring loop."""
    print(f"🔍 Connection Monitor Starting - {datetime.now().isoformat()}")
    print(f"   Idle transaction timeout: {IDLE_TRANSACTION_TIMEOUT_MINUTES} minutes")
    print(f"   Long query timeout: {LONG_QUERY_TIMEOUT_MINUTES} minutes")
    print(f"   Dry run mode: {DRY_RUN}")
    print()

    try:
        conn = get_db_connection()
        conn.autocommit = True

        idle_transactions, long_queries = find_stuck_connections(conn)

        # Process idle transactions
        if idle_transactions:
            print(f"⚠️  Found {len(idle_transactions)} idle-in-transaction connections:")
            for i, conn_info in enumerate(idle_transactions, 1):
                duration = format_duration(conn_info["idle_duration"])
                print(f"\n  {i}. PID {conn_info['pid']} (idle for {duration})")
                print(f"     User: {conn_info['usename']}")
                print(f"     App: {conn_info['application_name']}")
                print(f"     Started: {conn_info['query_start']}")
                print(f"     Query: {conn_info['query_preview'][:100]}...")

                if not DRY_RUN:
                    killed = kill_connection(conn, conn_info["pid"], "idle_transaction")
                    if killed:
                        print(f"     ✅ Terminated PID {conn_info['pid']}")
                    else:
                        print(f"     ❌ Failed to terminate PID {conn_info['pid']}")
                else:
                    print(f"     🔍 [DRY RUN] Would terminate PID {conn_info['pid']}")
        else:
            print("✅ No stuck idle-in-transaction connections found")

        # Process long-running queries
        if long_queries:
            print(f"\n⚠️  Found {len(long_queries)} long-running queries:")
            for i, conn_info in enumerate(long_queries, 1):
                duration = format_duration(conn_info["query_duration"])
                print(f"\n  {i}. PID {conn_info['pid']} (running for {duration})")
                print(f"     User: {conn_info['usename']}")
                print(f"     App: {conn_info['application_name']}")
                print(f"     Started: {conn_info['query_start']}")
                print(f"     Query: {conn_info['query_preview'][:150]}...")

                if not DRY_RUN:
                    killed = kill_connection(conn, conn_info["pid"], "long_query")
                    if killed:
                        print(f"     ✅ Terminated PID {conn_info['pid']}")
                    else:
                        print(f"     ❌ Failed to terminate PID {conn_info['pid']}")
                else:
                    print(f"     🔍 [DRY RUN] Would terminate PID {conn_info['pid']}")
        else:
            print("\n✅ No long-running queries found")

        # Summary
        total_killed = len(idle_transactions) + len(long_queries)
        if total_killed > 0:
            action = "Would terminate" if DRY_RUN else "Terminated"
            print(f"\n📊 Summary: {action} {total_killed} connections")
        else:
            print("\n📊 Summary: Database connection pool is healthy")

        conn.close()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
