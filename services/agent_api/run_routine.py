"""
Manual routine runner — executes a single routine step-by-step and
prints a detailed trace of inputs and outputs at each step.

Usage (inside container or with venv active):
    python run_routine.py <routine_id> [client_id]

Examples:
    python run_routine.py weekly_reengagement
    python run_routine.py monthly_strategy_brief
    python run_routine.py weekly_financial_snapshot da1abcb6-3e7a-476d-b13b-ff55a3cc0db2
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PURE_PLACEHOLDER_RE = re.compile(r"^\{\{\s*(\w+)\s*\}\}$")
_INLINE_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# ── logging: show INFO so we can follow execution ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
# Suppress noisy libs
for noisy in ("httpx", "httpcore", "openai", "anthropic", "langfuse", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("routine_runner")

# ── env: load .env so the script works without the full compose stack ─────────

_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file, override=False)


_DIVIDER = "─" * 72
_CLIENT_ID = "da1abcb6-3e7a-476d-b13b-ff55a3cc0db2"


def _pp(obj: Any, indent: int = 2) -> str:
    """Pretty-print any value, truncating long strings."""
    if isinstance(obj, str) and len(obj) > 500:
        obj = obj[:500] + f"… [+{len(obj)-500} chars]"
    if isinstance(obj, list) and len(obj) > 5:
        preview = obj[:5]
        remaining = len(obj) - 5
        return json.dumps(preview, ensure_ascii=False, indent=indent) + f"\n  … +{remaining} more items"
    try:
        return json.dumps(obj, ensure_ascii=False, indent=indent, default=str)
    except Exception:
        return repr(obj)


def _resolve_templates(obj: Any, state: dict[str, Any]) -> Any:
    """Resolve {{key}} placeholders (mirrors routine engine logic)."""
    if isinstance(obj, str):
        # Pure placeholder — preserve the value's original type
        m = _PURE_PLACEHOLDER_RE.match(obj)
        if m:
            key = m.group(1)
            val = state.get(key)
            return obj if val is None else val
        # Mixed string — stringify everything
        def _replace(m: re.Match) -> str:
            key = m.group(1).strip()
            val = state.get(key)
            if val is None:
                return m.group(0)
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)
        return _INLINE_PLACEHOLDER_RE.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _resolve_templates(v, state) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_templates(v, state) for v in obj]
    return obj


async def run_routine(routine_id: str, client_id: str) -> None:
    from blu_supabase_client import get_supabase_client

    db = get_supabase_client(use_service_role=True)

    # ── 1. Fetch catalog routine ───────────────────────────────────────────────
    row = db.table("cross_agent_routines").select("*").eq("id", routine_id).maybe_single().execute()
    if not row.data:
        print(f"ERROR: Routine '{routine_id}' not found in cross_agent_routines")
        sys.exit(1)
    routine = row.data
    steps: list[dict] = routine.get("steps") or []
    print(f"\n{_DIVIDER}")
    print(f"  ROUTINE  : {routine['name']}  (id={routine_id})")
    print(f"  ROOM     : {routine['room']}")
    print(f"  TRIGGER  : {routine['trigger_type']}")
    print(f"  STEPS    : {len(steps)}")
    print(f"  CLIENT   : {client_id}")
    print(_DIVIDER)

    # ── 2. Fetch per-client config overrides ─────────────────────────────────
    cfg_row = (
        db.table("client_routines")
        .select("config, trigger_type, trigger_config")
        .eq("client_id", client_id)
        .eq("routine_id", routine_id)
        .maybe_single()
        .execute()
    )
    client_config: dict[str, Any] = {}
    if cfg_row and cfg_row.data and cfg_row.data.get("config"):
        for k, v in cfg_row.data["config"].items():
            try:
                client_config[k] = int(v)
            except (ValueError, TypeError):
                try:
                    client_config[k] = float(v)
                except (ValueError, TypeError):
                    client_config[k] = v
    print(f"\nClient config overrides: {_pp(client_config)}")

    # ── 3. Create a test execution row ────────────────────────────────────────
    exec_id = str(uuid.uuid4())
    db.table("client_routine_executions").insert({
        "id": exec_id,
        "client_id": client_id,
        "routine_id": routine_id,
        "status": "executing",
        "triggered_by": "manual_test",
        "trigger_data": {},
    }).execute()
    print(f"\nExecution ID: {exec_id}")

    # ── 4. Get company name ────────────────────────────────────────────────────
    from agent_api.core.factory import get_context_service
    ctx_svc = get_context_service()
    client_ctx = await ctx_svc.get_client_context_by_id(client_id)
    nome_empresa = client_ctx.nome_empresa if client_ctx else "Empresa Teste"
    print(f"Company    : {nome_empresa}\n")

    # ── 5. Build initial state ────────────────────────────────────────────────
    state: dict[str, Any] = {
        "client_id": client_id,
        "routine_name": routine["name"],
        "exec_id": exec_id,
        "nome_empresa": nome_empresa,
        **client_config,
    }

    # ── 6. Execute steps ──────────────────────────────────────────────────────
    from agent_api.core.routine_artifacts import call as call_artifact
    from agent_api.core.routine_functions import call as call_function

    step_results: list[dict] = []

    for step in steps:
        step_n = step.get("step", 0)
        step_id = step.get("id") or f"step_{step_n}"
        step_type: str | None = step.get("type")
        on_failure: str = step.get("on_failure", "halt")

        print(f"\n{'━'*72}")
        print(f"  STEP {step_n}: {step_id}  [type={step_type or 'legacy'}]  on_failure={on_failure}")
        print(f"{'━'*72}")

        # Resolve inputs against current state
        raw_inputs = step.get("inputs", {})
        resolved_inputs = _resolve_templates(raw_inputs, state)

        # Apply per-client config override for function steps
        if step_type == "function":
            config_override = {k: client_config[k] for k in resolved_inputs if k in client_config}
            if config_override:
                print(f"  Config overrides applied: {_pp(config_override)}")
                resolved_inputs = {**resolved_inputs, **config_override}

        if resolved_inputs:
            print(f"\n  INPUTS:\n{_pp(resolved_inputs)}")

        if step_type in {"function", "artifact"}:
            try:
                from agent_api.core.factory import get_mcp_manager
                get_mcp_manager().set_client_id(client_id)
            except Exception:
                pass

        if step_type == "skill":
            task_template = step.get("task_template", "")
            task = _resolve_templates(task_template, state)
            print(f"\n  TASK PROMPT (first 400 chars):\n  {task[:400]}")
            if step.get("outputs"):
                print(f"\n  EXPECTED OUTPUTS SCHEMA:\n{_pp(step['outputs'])}")

        t_start = datetime.now(timezone.utc)
        try:
            if step_type == "function":
                fn_name: str = step.get("function", "")
                print(f"\n  → calling function: {fn_name}")
                step_outputs = await call_function(fn_name, resolved_inputs, client_id)

            elif step_type == "skill":
                print(f"\n  → invoking skill worker: {step.get('skill_slug')}")
                print("  (this may take 10-30s — LLM is running)")
                from agent_api.core.factory import get_context_service, get_mcp_manager
                from agent_api.core.routines import _execute_skill_step
                get_mcp_manager().set_client_id(client_id)
                step_outputs, slug = await _execute_skill_step(
                    step, resolved_inputs, state, nome_empresa, get_context_service()
                )

            elif step_type == "artifact":
                fn_name = step.get("function", "")
                if not fn_name:
                    _ARTIFACT_MAP = {
                        "email": "channels.send_email_batch",
                        "alert": "channels.create_alert",
                        "document": "storage.save_context_document",
                        "whatsapp": "channels.send_whatsapp",
                    }
                    fn_name = _ARTIFACT_MAP.get(step.get("artifact_type", ""), "")
                print(f"\n  → calling artifact: {fn_name}")
                step_outputs = await call_artifact(fn_name, resolved_inputs, client_id)

            else:
                print(f"  SKIP: unknown step type '{step_type}'")
                continue

            elapsed = (datetime.now(timezone.utc) - t_start).total_seconds()
            print(f"\n  OUTPUTS (elapsed {elapsed:.1f}s):")
            for k, v in step_outputs.items():
                print(f"    {k}: {_pp(v)}")

            state.update(step_outputs)
            step_results.append({"step": step_id, "status": "ok", "outputs": step_outputs})

        except Exception as exc:
            elapsed = (datetime.now(timezone.utc) - t_start).total_seconds()
            print(f"\n  ERROR (elapsed {elapsed:.1f}s): {exc}")
            step_results.append({"step": step_id, "status": "error", "error": str(exc)})
            if on_failure == "halt":
                print("  on_failure=halt → stopping execution")
                db.table("client_routine_executions").update({
                    "status": "failed",
                    "result_text": f"Step '{step_id}' failed: {exc}",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", exec_id).execute()
                break
            else:
                print("  on_failure=continue → proceeding to next step")

    # ── 7. Mark execution complete ────────────────────────────────────────────
    all_ok = all(r["status"] == "ok" for r in step_results)
    db.table("client_routine_executions").update({
        "status": "completed" if all_ok else "failed",
        "result_text": f"Manual test: {len(step_results)} steps",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "result_metadata": {str(i): r for i, r in enumerate(step_results)},
    }).eq("id", exec_id).execute()

    print(f"\n{_DIVIDER}")
    print(f"  DONE — {len(step_results)} steps, status={'OK' if all_ok else 'PARTIAL FAILURE'}")
    print(f"  Execution saved: {exec_id}")
    print(_DIVIDER + "\n")

if __name__ == "__main__":
    routine_id = sys.argv[1] if len(sys.argv) > 1 else "weekly_reengagement"
    client_id = sys.argv[2] if len(sys.argv) > 2 else _CLIENT_ID
    asyncio.run(run_routine(routine_id, client_id))
