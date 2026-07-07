#!/usr/bin/env python3
"""
factory-coder script — substituto do perfil LLM factory-coder.

Lê o card kanban, constrói o prompt para o OpenCode a partir do body do card,
executa o OpenCode e chama kanban_complete.

Modo de uso:
  python3 factory-coder.py <card_id>

Pré-requisitos:
  - opencode instalado e configurado
  - hermes CLI disponível no PATH
  - Executar dentro do diretório do repo (~/repo_platform)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_DIR = os.environ.get("REPO_DIR", os.path.expanduser("~/repo_platform"))


def run_cmd(cmd: list[str], timeout: int = 120) -> dict:
    """Run a command and return {'output': str, 'exit_code': int}."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=REPO_DIR,
        )
        return {
            "output": result.stdout + result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"output": "TIMEOUT", "exit_code": -1}
    except FileNotFoundError as e:
        return {"output": f"Comando não encontrado: {e}", "exit_code": -1}


def get_card(card_id: str) -> dict | None:
    """Get card details via `hermes kanban show --json`."""
    result = run_cmd(["hermes", "kanban", "show", card_id, "--json"])
    if result["exit_code"] != 0:
        print(f"ERRO: Não foi possível ler card {card_id}: {result['output']}")
        return None
    try:
        return json.loads(result["output"])
    except json.JSONDecodeError:
        print(f"ERRO: JSON inválido do kanban show: {result['output'][:500]}")
        return None


def build_opencode_prompt(card: dict) -> str:
    """Build the OpenCode prompt from the card body."""
    title = card.get("title", "")
    body = card.get("body", "")

    # Tenta extrair partes estruturadas do body
    goal = ""
    acs = []
    test_path = ""
    lines = body.split("\n")
    current_section = None
    ac_counter = 0

    for line in lines:
        line_stripped = line.strip()
        if line_stripped.lower().startswith("goal:"):
            goal = line_stripped[5:].strip()
            current_section = "goal"
        elif line_stripped.lower().startswith("ac") and ":" in line_stripped:
            ac_counter += 1
            ac_text = line_stripped.split(":", 1)[1].strip()
            acs.append(f"AC{ac_counter}: {ac_text}")
            current_section = "acs"
        elif line_stripped.lower().startswith("teste red") or "test_" in line_stripped.lower():
            # Extrai path do teste
            parts = line_stripped.split()
            for p in parts:
                if "test_" in p and ".py" in p:
                    test_path = p.strip("`'\"")
        elif line_stripped and current_section == "goal":
            goal += " " + line_stripped
        elif not line_stripped:
            current_section = None

    # Fallback: se não conseguiu extrair ACs, usa o body inteiro
    if not acs and body:
        return (
            f"Objetivo: {title}\n\n"
            f"{body}\n\n"
            f"Implemente o código GREEN mínimo para fazer o teste RED passar. "
            f"Não adicione funcionalidades extras. Crie um PR."
        )

    # Constrói prompt estruturado
    prompt_parts = [f"Objetivo: {goal or title}"]
    if acs:
        prompt_parts.append("\nCritérios de Aceitação:")
        prompt_parts.extend(f"  {ac}" for ac in acs)
    if test_path:
        prompt_parts.append(f"\nTeste RED: {test_path}")
    prompt_parts.append(
        "\n\nImplemente o código GREEN mínimo para fazer o teste RED passar. "
        "Não adicione funcionalidades extras. Crie um PR com as alterações."
    )

    return "\n".join(prompt_parts)


def run_opencode(prompt: str) -> dict:
    """Run opencode with the given prompt."""
    # Escreve prompt em arquivo temporário para evitar problemas de escaping
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix="opencode_prompt_"
    ) as f:
        f.write(prompt)
        prompt_path = f.name

    try:
        # Limpa vars AWS (famoso problema)
        env = os.environ.copy()
        for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]:
            env.pop(key, None)

        result = subprocess.run(
            ["opencode", "run", f"@{prompt_path}"],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout para OpenCode
            cwd=REPO_DIR,
            env=env,
        )
        return {
            "output": result.stdout + result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"output": "TIMEOUT — OpenCode excedeu 10 minutos", "exit_code": -1}
    finally:
        os.unlink(prompt_path)


def complete_card(card_id: str, summary: str, metadata: dict):
    """Mark the kanban card as complete."""
    metadata_json = json.dumps(metadata)
    result = run_cmd(
        [
            "hermes", "kanban", "complete", card_id,
            "--summary", summary,
            "--metadata", metadata_json,
        ]
    )
    if result["exit_code"] != 0:
        print(f"AVISO: kanban_complete falhou: {result['output']}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 factory-coder.py <card_id>")
        sys.exit(1)

    card_id = sys.argv[1]
    print(f"[factory-coder] Lendo card {card_id}...")

    card = get_card(card_id)
    if not card:
        print(f"[factory-coder] ERRO: Card {card_id} não encontrado")
        sys.exit(1)

    print(f"[factory-coder] Card: {card.get('title', 'sem título')}")

    # Verifica se opencode existe
    which_check = run_cmd(["which", "opencode"])
    if which_check["exit_code"] != 0:
        print("[factory-coder] ERRO: opencode não está instalado")
        sys.exit(1)

    # Constrói prompt e executa
    prompt = build_opencode_prompt(card)
    print(f"[factory-coder] Executando OpenCode...")
    print(f"  Prompt: {prompt[:200]}...")

    result = run_opencode(prompt)

    if result["exit_code"] == 0:
        print(f"[factory-coder] ✅ OpenCode concluído com sucesso")
        complete_card(
            card_id,
            summary="Implementado via OpenCode — GREEN",
            metadata={"tag": "green", "next_step": "reviewer"},
        )
        print(f"[factory-coder] ✅ Card {card_id} concluído e passado para reviewer")
    else:
        print(f"[factory-coder] ❌ OpenCode falhou (exit={result['exit_code']})")
        print(f"  Output: {result['output'][:1000]}")
        # Card fica como running — o dispatcher pode retentar
        sys.exit(1)


if __name__ == "__main__":
    main()
