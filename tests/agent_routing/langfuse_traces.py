"""
langfuse_traces.py
------------------
Fetch and display Langfuse traces for routing-test sessions.

Usage:
    python3 langfuse_traces.py                    # last 10 routing-test traces
    python3 langfuse_traces.py --session test-L1-007
    python3 langfuse_traces.py --limit 20
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DOTENV = Path(__file__).parents[2] / ".env"


def _load_env() -> None:
    if not DOTENV.exists():
        return
    for line in DOTENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


_load_env()

BASE_URL = os.environ.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")

if not PUBLIC_KEY or not SECRET_KEY:
    sys.exit("ERROR: LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set.")

AUTH = (PUBLIC_KEY, SECRET_KEY)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def fetch_traces(tag: str = "routing-test", limit: int = 10) -> list[dict]:
    r = httpx.get(
        f"{BASE_URL}/api/public/traces",
        params={"tags": tag, "limit": limit, "orderBy": "timestamp.desc"},
        auth=AUTH,
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def fetch_trace(trace_id: str) -> dict:
    r = httpx.get(
        f"{BASE_URL}/api/public/traces/{trace_id}",
        auth=AUTH,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fetch_observations(trace_id: str) -> list[dict]:
    r = httpx.get(
        f"{BASE_URL}/api/public/observations",
        params={"traceId": trace_id, "limit": 50},
        auth=AUTH,
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def fetch_by_session(session_id: str) -> list[dict]:
    r = httpx.get(
        f"{BASE_URL}/api/public/traces",
        params={"sessionId": session_id, "limit": 5},
        auth=AUTH,
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("data", [])


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _short(v: object, n: int = 80) -> str:
    s = str(v or "")
    return s[:n] + "…" if len(s) > n else s


def print_trace_summary(traces: list[dict]) -> None:
    if not traces:
        print("No traces found.")
        return
    print(f"\n{'ID':36s}  {'Session':20s}  {'Status':8s}  {'Latency':8s}  Input preview")
    print("-" * 110)
    for t in traces:
        tid = t.get("id", "")[:36]
        sid = (t.get("sessionId") or "")[:20]
        status = t.get("status", "")[:8]
        latency_ms = int((t.get("latency") or 0) * 1000)
        inp = _short(t.get("input") or "", 50)
        print(f"{tid:36s}  {sid:20s}  {status:8s}  {latency_ms:6d}ms  {inp}")


def print_trace_detail(trace: dict, observations: list[dict]) -> None:
    print(f"\n{'='*60}")
    print(f"Trace : {trace.get('id')}")
    print(f"Session : {trace.get('sessionId')}")
    print(f"Status  : {trace.get('status')}")
    print(f"Tags    : {trace.get('tags')}")
    latency_ms = int((trace.get("latency") or 0) * 1000)
    print(f"Latency : {latency_ms}ms")
    print(f"Input   : {_short(trace.get('input'), 120)}")
    print(f"Output  : {_short(trace.get('output'), 120)}")

    if observations:
        print(f"\nObservations ({len(observations)}):")
        for obs in sorted(observations, key=lambda o: o.get("startTime", "")):
            kind = obs.get("type", "")
            name = obs.get("name", "")[:40]
            model = obs.get("model") or ""
            tokens = obs.get("usage", {}) or {}
            inp_tok = tokens.get("input", 0)
            out_tok = tokens.get("output", 0)
            lat = int((obs.get("latency") or 0) * 1000)
            print(f"  [{kind:8s}] {name:40s}  model={model:20s}  in={inp_tok:5d} out={out_tok:5d}  {lat}ms")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Langfuse routing-test traces")
    parser.add_argument("--session", help="Filter by session_id (e.g. test-L1-007)")
    parser.add_argument("--trace", help="Show full detail for a specific trace_id")
    parser.add_argument("--limit", type=int, default=10, help="Number of traces to fetch")
    parser.add_argument("--tag", default="routing-test", help="Tag to filter by")
    args = parser.parse_args()

    if args.trace:
        trace = fetch_trace(args.trace)
        obs = fetch_observations(args.trace)
        print_trace_detail(trace, obs)
        return

    if args.session:
        traces = fetch_by_session(args.session)
    else:
        traces = fetch_traces(tag=args.tag, limit=args.limit)

    print_trace_summary(traces)

    # If only one trace found, show detail automatically
    if len(traces) == 1:
        obs = fetch_observations(traces[0]["id"])
        print_trace_detail(traces[0], obs)


if __name__ == "__main__":
    main()
