#!/usr/bin/env python3
"""
Executor F3 — Pipeline 3.0.
Varre cards 'ready' do board factory-v3 com assignee=pipeline-bot e executa:

  1. Lê card body (já tem Goal + ACs + test_red + routing)
  2. Chama opencode run com o body
  3. Valida resultado (multi-camada, anti-falso-GREEN)
  4. Atualiza card: complete (routing PM) ou blocked (diagnóstico)

Zero LLM Hermes aqui — só OpenCode + scripts.

Uso: python3 scripts/executor_f3.py
Rodar como cron a cada 10 minutos.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path.home() / "repo_platform"
BOARD = "factory-v3"


def run_cmd(cmd: list[str], timeout: int = 120, cwd: str | None = None) -> dict:
    """Executa comando e retorna {'output': str, 'exit_code': int, 'error': str}."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=cwd or str(REPO_ROOT),
        )
        return {"output": (result.stdout + result.stderr).strip(), "exit_code": result.returncode, "error": None}
    except subprocess.TimeoutExpired:
        return {"output": "", "exit_code": -1, "error": "TIMEOUT"}
    except FileNotFoundError as e:
        return {"output": "", "exit_code": -1, "error": str(e)}


def get_ready_cards() -> list[dict]:
    """Lista cards 'ready' no board factory-v3 com assignee pipeline-bot."""
    result = run_cmd(["hermes", "kanban", "list", "--board", BOARD, "--json"], timeout=30)
    if result["exit_code"] != 0 or not result["output"]:
        return []

    try:
        cards = json.loads(result["output"])
    except (json.JSONDecodeError, TypeError):
        return []

    ready = []
    for card in cards:
        status = card.get("status", "")
        assignee = card.get("assignee", "")
        if status in ("ready", "▶") and assignee == "pipeline-bot":
            ready.append(card)

    return ready


def get_card_body(card_id: str) -> tuple[str, str]:
    """Extrai title + body de um card via kanban show."""
    result = run_cmd(["hermes", "kanban", "show", card_id], timeout=15)
    if result["exit_code"] != 0:
        return ("", "")

    output = result["output"]
    lines = output.split("\n")

    title = ""
    body = ""
    in_body = False
    body_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Task") and ":" in stripped:
            colon_pos = stripped.find(": ")
            if colon_pos > 0:
                title = stripped[colon_pos + 2:].strip()
        if stripped == "Body:":
            in_body = True
            continue
        if in_body:
            if stripped.startswith("Events") or stripped.startswith("Metadata"):
                break
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, body


def run_opencode(prompt: str, card_id: str) -> dict:
    """Executa opencode run com o body do card. Retorna resultado."""
    # Limpa vars AWS
    env = os.environ.copy()
    for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]:
        env.pop(key, None)

    # Verifica opencode
    which = subprocess.run(["which", "opencode"], capture_output=True, text=True, timeout=10)
    if which.returncode != 0:
        return {"output": "", "exit_code": -1, "error": "opencode_not_found", "pr_number": None}

    # Escreve prompt no diretório do repo (OpenCode não gosta de /tmp/)
    prompt_dir = REPO_ROOT / "scripts" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"f3_{card_id}.md"
    prompt_path.write_text(prompt)

    print(f"[Executor] Prompt salvo em {prompt_path} ({len(prompt)} chars)", flush=True)
    print(f"[Executor] Executando: opencode run @{prompt_path}", flush=True)

    try:
        result = subprocess.run(
            ["opencode", "run", f"@{prompt_path}"],
            capture_output=True, text=True, timeout=600, cwd=str(REPO_ROOT), env=env,
        )
        output = (result.stdout + result.stderr).strip()

        # Tenta extrair PR number
        pr_number = None
        for line in output.split("\n"):
            pr_match = re.search(r'(?:PR|pull request)\s*#?(\d+)', line, re.IGNORECASE)
            if pr_match:
                pr_number = int(pr_match.group(1))
                break

        return {"output": output, "exit_code": result.returncode, "error": None, "pr_number": pr_number}

    except subprocess.TimeoutExpired:
        return {"output": "", "exit_code": -1, "error": "timeout", "pr_number": None}


def validate_result(result: dict, card_body: str) -> dict:
    """Validação multi-camada — anti-falso-GREEN.

    Camadas:
    1. git diff --name-only → ≥1 arquivo (excluindo scripts/, node_modules/)
    2. pytest do teste RED → exit_code == 0
    3. PR detectado (confirmado via gh)
    """
    checks = []

    # ---- Camada 1: git diff ----
    diff = run_cmd(["git", "diff", "--name-only", "--diff-filter=ACMR"], timeout=15)
    diff_files = [f.strip() for f in diff["output"].split("\n") if f.strip()]
    # Filtra diretórios irrelevantes
    real_files = [f for f in diff_files if not any(
        f.startswith(d) for d in ["scripts/", "node_modules/", ".hermes/"]
    )]

    if real_files:
        checks.append({"check": "git_diff", "status": "pass", "detail": f"{len(real_files)} arquivo(s) alterado(s)", "files": real_files})
    else:
        checks.append({"check": "git_diff", "status": "fail", "detail": "Nenhum arquivo alterado (excluindo scripts/, node_modules/)"})

    # ---- Camada 2: pytest ----
    # Extrai test_red do card body
    test_path = None
    for line in card_body.split("\n"):
        line_lower = line.lower().strip()
        if "teste red" in line_lower or "test_red" in line_lower or "test file" in line_lower:
            # Extrai o path após ":"
            if ":" in line:
                test_path = line.split(":", 1)[1].strip().strip("`'\"")
                break

    if test_path and not test_path.endswith(".py"):
        test_path = None

    if test_path:
        test_full = REPO_ROOT / test_path
        if test_full.exists():
            pytest_result = run_cmd(["python3", "-m", "pytest", str(test_full), "-v", "--tb=short"], timeout=120)

            # Parse resultado
            passed = pytest_result["exit_code"] == 0
            failed_count = 0
            for line in pytest_result["output"].split("\n"):
                if "FAILED" in line:
                    failed_count += 1

            if passed:
                checks.append({"check": "pytest", "status": "pass", "detail": f"✅ {test_path} — passou"})
            else:
                checks.append({"check": "pytest", "status": "fail", "detail": f"❌ {test_path} — {failed_count} falha(s)", "output": pytest_result["output"][:500]})
        else:
            checks.append({"check": "pytest", "status": "fail", "detail": f"Arquivo de teste não encontrado: {test_path}"})
    else:
        checks.append({"check": "pytest", "status": "warn", "detail": "Nenhum test_red especificado no body do card"})

    # ---- Camada 3: PR confirmado ----
    pr_number = result.get("pr_number")
    if pr_number:
        # Confirma via gh CLI
        pr_check = run_cmd(["gh", "pr", "view", str(pr_number), "--json", "state,title,url"], timeout=15)
        if pr_check["exit_code"] == 0:
            try:
                pr_data = json.loads(pr_check["output"])
                if pr_data.get("state") == "OPEN":
                    checks.append({"check": "pr_exists", "status": "pass", "detail": f"PR #{pr_number} aberto — {pr_data.get('title', '')}"})
                else:
                    checks.append({"check": "pr_exists", "status": "warn", "detail": f"PR #{pr_number} — estado: {pr_data.get('state')}"})
            except json.JSONDecodeError:
                checks.append({"check": "pr_exists", "status": "warn", "detail": f"PR #{pr_number} mencionado mas não confirmado via API"})
        else:
            checks.append({"check": "pr_exists", "status": "warn", "detail": f"PR #{pr_number} mencionado mas gh falhou ao confirmar"})
    else:
        checks.append({"check": "pr_exists", "status": "fail", "detail": "Nenhum PR detectado no output do OpenCode"})

    # ---- Resultado final ----
    fails = [c for c in checks if c["status"] == "fail"]
    warnings = [c for c in checks if c["status"] == "warn"]

    validation = {
        "status": "pass" if not fails else "fail",
        "checks": checks,
        "summary": {
            "total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "warn": len(warnings),
            "fail": len(fails),
        }
    }

    return validation


def main():
    print(f"\n{'='*60}", flush=True)
    print(f"Executor F3 — Pipeline 3.0 — Board: {BOARD}", flush=True)
    print(f"{'='*60}\n", flush=True)

    # 1. Busca cards ready
    cards = get_ready_cards()
    print(f"[Executor] Cards ready (assignee=pipeline-bot): {len(cards)}", flush=True)

    if not cards:
        print("[Executor] Nenhum card para executar.", flush=True)
        return

    # 2. Processa 1 card por tick
    card = cards[0]
    card_id = card.get("id", card.get("task_id", ""))
    title = card.get("title", "?")

    print(f"\n[Executor] Processando: {title} ({card_id})", flush=True)

    # Move para running
    run_cmd(["hermes", "kanban", "promote", "--force", card_id], timeout=15)

    # 3. Lê body do card
    card_title, card_body = get_card_body(card_id)
    if not card_body:
        print(f"[Executor] ERRO: Card sem body", flush=True)
        run_cmd(["hermes", "kanban", "block", card_id, "Card sem body — triage-agent precisa preencher"], timeout=15)
        return

    prompt = f"{card_title}\n\n{card_body}"
    print(f"[Executor] Card body: {len(prompt)} chars", flush=True)

    # 4. Executa OpenCode
    print(f"[Executor] Chamando OpenCode...", flush=True)
    oc_result = run_opencode(prompt, card_id)

    if oc_result["exit_code"] != 0 and oc_result["error"]:
        error_msg = f"OpenCode falhou: {oc_result['error']}"
        print(f"[Executor] ❌ {error_msg}", flush=True)
        run_cmd(["hermes", "kanban", "block", card_id, error_msg], timeout=15)
        return

    print(f"[Executor] ✅ OpenCode exit=0", flush=True)
    if oc_result.get("pr_number"):
        print(f"[Executor] PR #{oc_result['pr_number']} detectado", flush=True)

    # 5. Valida resultado
    print(f"[Executor] Validando resultado...", flush=True)
    validation = validate_result(oc_result, card_body)

    print(f"[Executor] Validação: {validation['status']}", flush=True)
    for check in validation["checks"]:
        status_icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}.get(check["status"], "?")
        print(f"  {status_icon} {check['check']}: {check['detail'][:100]}", flush=True)

    # 6. Atualiza card
    if validation["status"] == "pass":
        # Tudo OK → routing para PM
        metadata = {
            "tag": "executed",
            "next_step": "project-manager: consolidar resultados",
            "phase": "post-execution",
            "routing": {"on_complete": "project-manager", "on_fail": "triage-agent"},
            "pr_number": oc_result.get("pr_number"),
            "validation_summary": validation["summary"],
        }
        summary = (f"✅ Executado + Validado. PR #{oc_result['pr_number']}. "
                   f"{validation['summary']['pass']}/{validation['summary']['total']} checks passaram.")
        run_cmd(["hermes", "kanban", "complete", card_id,
                 "--summary", summary,
                 "--metadata", json.dumps(metadata)], timeout=15)
        print(f"[Executor] ✅ Card {card_id} concluído — routing para PM", flush=True)
    else:
        # Falhou → blocked com diagnóstico
        fail_checks = [c for c in validation["checks"] if c["status"] == "fail"]
        reason = "; ".join(f"{c['check']}: {c['detail'][:80]}" for c in fail_checks)
        print(f"[Executor] ❌ Validação falhou: {reason}", flush=True)
        run_cmd(["hermes", "kanban", "block", card_id, f"Validação falhou: {reason}"], timeout=15)

    # 7. Salva log
    log_dir = REPO_ROOT / "scripts" / "executions"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = {
        "card_id": card_id,
        "title": card_title,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "validation": validation,
        "pr_number": oc_result.get("pr_number"),
    }
    log_file = log_dir / f"{card_id}.json"
    log_file.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"[Executor] Log salvo: {log_file}", flush=True)


if __name__ == "__main__":
    main()
