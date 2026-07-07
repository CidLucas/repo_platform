"""Compartilhado entre as fases da Pipeline 2.0 — zero LLM."""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path.home() / "repo_platform"
SCRIPTS_DIR = Path(__file__).parent
CONTEXTS_DIR = SCRIPTS_DIR / "contexts"


def ensure_contexts_dir():
    CONTEXTS_DIR.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str], timeout: int = 120, cwd: str | None = None) -> dict:
    """Executa comando e retorna {'output': str, 'exit_code': int}."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or str(REPO_ROOT),
        )
        return {"output": (result.stdout + result.stderr).strip(), "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"output": "TIMEOUT", "exit_code": -1}
    except FileNotFoundError as e:
        return {"output": f"Command not found: {e}", "exit_code": -1}


def get_card(card_id: str) -> dict | None:
    """Lê card do kanban via texto (parsing manual, mais robusto que JSON)."""
    result = run_cmd(["hermes", "kanban", "show", card_id])
    if result["exit_code"] != 0:
        print(f"[pipeline_common] ERRO: kanban show falhou: {result['output'][:200]}")
        return None

    output = result["output"]
    lines = output.split("\n")
    
    card = {"id": card_id, "title": "", "body": ""}
    
    # Primeira linha: "Task <id>: <title>"
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("Task"):
            # "Task t_d782ad16: BKL-034: Multi-Upload..."
            colon_pos = line_stripped.find(": ")
            if colon_pos > 0:
                card["title"] = line_stripped[colon_pos + 2:].strip()
            break
    
    # Body: começa após "Body:" e vai até "Events" ou fim
    in_body = False
    body_lines = []
    for line in lines:
        if line.strip() == "Body:":
            in_body = True
            continue
        if in_body:
            if line.strip().startswith("Events"):
                break
            body_lines.append(line)
    
    card["body"] = "\n".join(body_lines).strip()
    return card


def parse_goal(body: str) -> str:
    """Extrai Goal do body."""
    match = re.search(r"(?i)^(?:goal|objetivo|descrição)\s*:\s*(.+)$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Fallback: primeira linha significativa
    for line in body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-") and not line.startswith("AC"):
            # Pode ser o título expandido
            if len(line) > 20:
                return line
    return ""


def parse_acs(body: str) -> list[str]:
    """Extrai ACs do body do card.
    Formatos aceitos:
      - AC1: texto
      - AC#1: texto
      - AC-1: texto
      - AC 1: texto
      AC1: texto
    """
    acs = []
    # Procura linhas que começam com - AC, AC#, AC-, AC
    pattern = re.compile(
        r"^(?:-\s*)?(?:AC\s*[#\-]?\s*\d+\s*:\s*)(.+)$",
        re.MULTILINE | re.IGNORECASE,
    )
    for match in pattern.finditer(body):
        ac_text = match.group(1).strip()
        if ac_text:
            acs.append(ac_text)
    return acs


def parse_test_red(body: str) -> str | None:
    """Extrai path do teste RED do body."""
    patterns = [
        r"(?i)(?:teste\s+red|test\s+file|teste)\s*:\s*(.+?)(?:\n|$)",
        r"(?i)(?:teste_red|test_path)\s*[:=]\s*['\"]?([^'\"]+)['\"]?",
        r"(?:test_[\w/]+\.py)",
    ]
    for p in patterns:
        match = re.search(p, body)
        if match:
            path = match.group(1).strip() if match.lastindex else match.group(0).strip()
            # Limpa e resolve
            path = path.strip("`'\"")
            if ".py" in path:
                return path
    return None


def parse_source_hint(body: str) -> str | None:
    """Extrai hint de arquivo fonte do body."""
    patterns = [
        r"(?i)(?:implementação\s+alvo|alvo|source|arquivo)\s*:\s*(.+?)(?:\n|$)",
        r"(?i)apps/[\w/]+\.tsx?",
        r"(?i)src/[\w/]+\.tsx?",
    ]
    for p in patterns:
        match = re.search(p, body)
        if match:
            path = match.group(0).strip() if not match.lastindex else match.group(1).strip()
            path = path.strip("`'\"")
            if path.startswith("apps/") or path.startswith("src/"):
                return path
    return None


def read_context(card_id: str) -> dict | None:
    """Lê context.json salvo da Fase 2."""
    ensure_contexts_dir()
    ctx_file = CONTEXTS_DIR / f"{card_id}.json"
    if ctx_file.exists():
        return json.loads(ctx_file.read_text())
    return None


def write_context(card_id: str, context: dict):
    """Salva context.json."""
    ensure_contexts_dir()
    ctx_file = CONTEXTS_DIR / f"{card_id}.json"
    ctx_file.write_text(json.dumps(context, indent=2, ensure_ascii=False))


def read_result(card_id: str) -> dict | None:
    """Lê result.json da Fase 3."""
    ensure_contexts_dir()
    result_file = CONTEXTS_DIR / f"{card_id}_result.json"
    if result_file.exists():
        return json.loads(result_file.read_text())
    return None


def write_result(card_id: str, result: dict):
    """Salva result.json."""
    ensure_contexts_dir()
    result_file = CONTEXTS_DIR / f"{card_id}_result.json"
    result_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
