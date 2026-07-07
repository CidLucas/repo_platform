#!/usr/bin/env python3
"""
Fase 3: EXECUÇÃO — Chama OpenCode com o body do card como prompt.
Zero LLM — só repassa o card para o OpenCode CLI.

Uso: python3 scripts/run_opencode.py <card_id>
Entrada: scripts/contexts/<card_id>.json (opcional — só para validação)
Saída: scripts/contexts/<card_id>_result.json
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from pipeline_common import (
    REPO_ROOT,
    get_card,
    read_context,
    write_result,
    run_cmd,
)


def build_prompt_from_card(card_id: str) -> str:
    """Constrói prompt a partir do card kanban (mais confiável que context.json)."""
    card = get_card(card_id)
    if not card:
        raise RuntimeError(f"Card {card_id} não encontrado")

    title = card.get("title", "")
    body = card.get("body", "")

    if not body:
        # Se não conseguiu extrair o body, usa context.json
        ctx = read_context(card_id)
        if ctx:
            body = ctx.get("description", "")
            title = ctx.get("goal", title)

    prompt = f"{title}\n\n{body}" if title else body

    # Adiciona instrução final se não estiver no body
    if "implemente" not in prompt.lower() and "crie" not in prompt.lower():
        prompt += (
            "\n\n## Instrução\n"
            "Implemente o código GREEN mínimo para fazer o teste RED passar. "
            "Não adicione funcionalidades extras. "
            "Crie um PR com as alterações."
        )

    return prompt.strip()


def run_opencode(prompt: str, card_id: str = "card") -> dict:
    """Executa opencode run com o prompt."""
    # Limpa vars AWS
    env = os.environ.copy()
    for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]:
        env.pop(key, None)

    # Verifica se opencode existe
    which = subprocess.run(["which", "opencode"], capture_output=True, text=True, timeout=10)
    if which.returncode != 0:
        return {"output": "opencode não encontrado no PATH", "exit_code": -1, "error": "missing_dependency"}

    # Escreve o card num arquivo markdown no diretório do repo
    prompt_dir = Path(REPO_ROOT) / "scripts" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"opencode_{card_id}.md"
    prompt_path.write_text(prompt)

    try:
        print(f"[Fase 3] Prompt salvo em {prompt_path} ({len(prompt)} chars)", flush=True)
        print(f"[Fase 3] Executando: opencode run @{prompt_path}", flush=True)

        result = subprocess.run(
            ["opencode", "run", f"@{prompt_path}"],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min
            cwd=str(REPO_ROOT),
            env=env,
        )

        output = (result.stdout + result.stderr).strip()

        # Tenta extrair PR number
        pr_number = None
        for line in output.split("\n"):
            pr_match = re.search(r'(?:PR|pull request)\s*#?(\d+)', line, re.IGNORECASE)
            if pr_match:
                pr_number = int(pr_match.group(1))
                break

        return {
            "output": output,
            "exit_code": result.returncode,
            "pr_number": pr_number,
        }

    except subprocess.TimeoutExpired:
        return {"output": "TIMEOUT — OpenCode excedeu 10 minutos", "exit_code": -1, "error": "timeout"}


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/run_opencode.py <card_id>")
        sys.exit(1)

    card_id = sys.argv[1]
    print(f"[Fase 3: EXECUÇÃO] Preparando prompt para card {card_id}...", flush=True)

    try:
        prompt = build_prompt_from_card(card_id)
    except RuntimeError as e:
        print(f"[Fase 3] ERRO: {e}", flush=True)
        sys.exit(1)

    print(f"[Fase 3] Prompt: {prompt[:200]}...", flush=True)

    result = run_opencode(prompt, card_id)

    # Salva resultado
    write_result(card_id, result)

    if result["exit_code"] == 0:
        print(f"[Fase 3] ✅ OpenCode concluído com sucesso", flush=True)
        if result.get("pr_number"):
            print(f"[Fase 3] PR #{result['pr_number']} criado", flush=True)
        print(json.dumps({"status": "ok", **result}), flush=True)
    else:
        print(f"[Fase 3] ❌ OpenCode falhou (exit={result['exit_code']})", flush=True)
        print(f"  {result.get('output', '')[:500]}", flush=True)
        print(json.dumps({"status": "error", **result}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
