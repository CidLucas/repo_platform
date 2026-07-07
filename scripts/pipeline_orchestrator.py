#!/usr/bin/env python3
"""
Pipeline Orchestrator — conecta Fase 2→3→4.

Varre cards 'ready' no kanban e executa:
  1. Fase 2: build_context.py (context.json)
  2. Fase 3: run_opencode.py (OpenCode)
  3. Fase 4: validate_result.py (pytest + ACs)

Se Fase 4 passar → card fica pronto para batch review (Fase 5).
Se falhar → card volta para blocked com diagnóstico.

Uso: python3 scripts/pipeline_orchestrator.py
Rodar como cron a cada 10 minutos.
"""

import json
import subprocess
import sys
from pathlib import Path

from pipeline_common import REPO_ROOT, CONTEXTS_DIR, run_cmd

SCRIPTS_DIR = Path(__file__).parent


def get_ready_cards() -> list[dict]:
    """Lista cards 'ready' do kanban."""
    result = run_cmd(["hermes", "kanban", "list", "--json"])
    if result["exit_code"] != 0:
        print(f"ERRO: Não foi possível listar cards: {result['output'][:200]}")
        return []
    try:
        cards = json.loads(result["output"])
    except json.JSONDecodeError:
        return []

    # Filtra apenas ready (status '▶' ou 'ready')
    ready = []
    for card in cards:
        status = card.get("status", "")
        if status in ("ready", "▶"):
            ready.append(card)
    return ready


def run_phase(phase_name: str, script: str, card_id: str) -> bool:
    """Executa uma fase do pipeline."""
    print(f"\n{'='*60}")
    print(f"[Orquestrador] FASE {phase_name}: {script} {card_id}")
    print('='*60)

    result = run_cmd(
        [sys.executable, script, card_id],
        timeout=600,  # 10 min para OpenCode
    )

    if result["exit_code"] != 0:
        print(f"[Orquestrador] ❌ Fase {phase_name} falhou")
        print(f"  Exit: {result['exit_code']}")
        print(f"  Output: {result['output'][:500]}")
        return False

    print(f"[Orquestrador] ✅ Fase {phase_name} OK")
    return True


def main():
    print(f"\n{'#'*60}")
    print(f"# Pipeline Orchestrator v2.0 — {__file__}")
    print(f"{'#'*60}\n")

    # 1. Busca cards ready
    ready_cards = get_ready_cards()
    print(f"[Orquestrador] Cards ready encontrados: {len(ready_cards)}")

    if not ready_cards:
        # 2. Verifica se há cards para batch review
        validated = list(CONTEXTS_DIR.glob("*_validation.json"))
        if validated:
            print(f"[Orquestrador] {len(validated)} cards validados aguardando batch review")
            batch_result = run_cmd(
                [sys.executable, str(SCRIPTS_DIR / "batch_review.py"), "--force"]
            )
            if batch_result["exit_code"] == 0:
                print(f"[Orquestrador] ✅ Batch review gerado")
        else:
            print(f"[Orquestrador] Nenhum card para processar")
        return

    # 3. Processa cada card ready
    for card in ready_cards[:1]:  # 1 card por tick
        card_id = card.get("id", card.get("task_id", ""))
        title = card.get("title", "?")

        print(f"\n[Orquestrador] Processando card: {title} ({card_id})")

        # Move para running
        run_cmd(["hermes", "kanban", "promote", "--force", card_id])

        # Fase 2: Contexto
        if not run_phase("2 — CONTEXTO", str(SCRIPTS_DIR / "build_context.py"), card_id):
            run_cmd(["hermes", "kanban", "block", card_id, "Falha na Fase 2 (contexto)"])
            continue

        # Fase 3: Execução via OpenCode
        if not run_phase("3 — EXECUÇÃO", str(SCRIPTS_DIR / "run_opencode.py"), card_id):
            run_cmd(["hermes", "kanban", "block", card_id, "Falha na Fase 3 (OpenCode)"])
            continue

        # Fase 4: Validação
        if not run_phase("4 — VALIDAÇÃO", str(SCRIPTS_DIR / "validate_result.py"), card_id):
            run_cmd(["hermes", "kanban", "block", card_id, "Falha na validação (testes não passam)"])
            continue

        # Passou! Move para done — aguarda batch review
        run_cmd(["hermes", "kanban", "complete", card_id,
                 "--summary", "Pipeline 2.0 — Implementado + Validado. Aguardando batch review.",
                 "--metadata", json.dumps({"tag": "validated", "next_step": "batch-review"})])

        print(f"[Orquestrador] ✅ Card {card_id} concluído com sucesso!")

    # 4. Verifica batch review após processar
    validated_files = list(CONTEXTS_DIR.glob("*_validation.json"))
    if len(validated_files) >= 5:
        print(f"[Orquestrador] {len(validated_files)} cards validados — gerando batch review")
        run_cmd([sys.executable, str(SCRIPTS_DIR / "batch_review.py")])


if __name__ == "__main__":
    main()
