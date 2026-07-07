#!/usr/bin/env python3
"""
Fase 5: BATCH REVIEW — Acumula cards validados e gera relatório via Hermes LLM.
Esta é a ÚNICA fase que usa LLM, e é 1 chamada para N cards.

Gatilho: Acumula BATCH_SIZE cards validados OU cron diário.

Uso: python3 scripts/batch_review.py [--force]
  --force: Gera relatório mesmo com menos de BATCH_SIZE cards
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from pipeline_common import REPO_ROOT, CONTEXTS_DIR, run_cmd, ensure_contexts_dir

BATCH_SIZE = 5
BATCH_DIR = CONTEXTS_DIR / "batches"


def find_validated_cards() -> list[dict]:
    """Encontra todos os cards validados que ainda não foram revisados em lote."""
    ensured = []
    for f in sorted(CONTEXTS_DIR.glob("*_validation.json")):
        card_id = f.stem.replace("_validation", "")
        # Verifica se já foi revisado
        batch_log = BATCH_DIR / f"{card_id}.reviewed"
        if batch_log.exists():
            continue
        try:
            validation = json.loads(f.read_text())
            if validation.get("status") == "pass":
                context_file = CONTEXTS_DIR / f"{card_id}.json"
                context = json.loads(context_file.read_text()) if context_file.exists() else {}
                ensured.append({
                    "card_id": card_id,
                    "goal": context.get("goal", "?"),
                    "pr_number": validation.get("pr_number"),
                    "validation": validation,
                    "validation_file": str(f),
                })
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return ensured


def build_batch_report(cards: list[dict]) -> str:
    """Constrói o prompt para o Hermes LLM gerar o relatório do lote."""
    lines = [
        "# Relatório de Revisão por Lote\n",
        f"Data: {datetime.now().isoformat()}",
        f"Total de cards no lote: {len(cards)}\n",
    ]

    for i, card in enumerate(cards, 1):
        lines.append(f"---")
        lines.append(f"## Card {i}: {card['goal']}")
        lines.append(f"  ID: {card['card_id']}")
        lines.append(f"  PR: #{card['pr_number']}" if card.get('pr_number') else "  PR: N/A")
        lines.append(f"  Status validação: {card['validation'].get('status', '?')}")
        
        # Detalhes dos checks
        checks = card['validation'].get('checks', {})
        if checks.get('pytest'):
            lines.append(f"  Testes: {checks['pytest'].get('detail', '?')}")
        if checks.get('changed_files'):
            files = checks['changed_files'].get('files', [])
            lines.append(f"  Arquivos alterados: {len(files)}")
            for f in files[:5]:
                lines.append(f"    - {f}")
        if checks.get('acs'):
            ac_pass = sum(1 for c in checks['acs'] if c['status'] == 'pass')
            ac_total = len(checks['acs'])
            lines.append(f"  ACs cobertas: {ac_pass}/{ac_total}")

        lines.append("")

    lines.append("## Instrução para o Revisor")
    lines.append("""
Analise este lote de implementações e produza um relatório respondendo:

1. **Aderência ao objetivo**: cada implementação resolve o problema descrito?
2. **Qualidade do código**: há problemas óbvios de arquitetura/segurança?
3. **Consistência**: as implementações seguem o mesmo padrão entre si?
4. **Riscos**: alguma mudança pode quebrar funcionalidades existentes?

Para cada card:
- ✅ Aprovado: PR pode ser merged
- ⚠️ Rework leve: pequenos ajustes antes de merge
- ❌ Rejeitado: precisa refazer

Formato do relatório:
```markdown
## Relatório do Lote {data}

### Cards Aprovados
- PR #N: {goal} ✅

### Cards com Rework
- PR #N: {goal} ⚠️ — motivo

### Cards Rejeitados  
- PR #N: {goal} ❌ — motivo

### Resumo
{aprovados}/{total} aprovados. Recomendação: {aprovar lote / revisar itens}
```
""")

    return "\n".join(lines)


def run_llm_review(prompt: str) -> str:
    """Chama o Hermes LLM para gerar o relatório de revisão."""
    # Escreve prompt em arquivo temporário
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix="batch_review_"
    ) as f:
        f.write(prompt)
        prompt_path = f.name

    try:
        # Chama Hermes como LLM (não como agente)
        result = run_cmd(
            ["hermes", "chat", "-z", f"@{prompt_path}", "--skills", "github-code-review"],
            timeout=300
        )
        return result.get("output", "Erro ao gerar relatório")
    finally:
        os.unlink(prompt_path)


def mark_as_reviewed(cards: list[dict]):
    """Marca cards como revisados para não entrarem em outro lote."""
    ensure_contexts_dir()
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    for card in cards:
        marker = BATCH_DIR / f"{card['card_id']}.reviewed"
        marker.write_text(datetime.now().isoformat())


def main():
    force = "--force" in sys.argv
    
    cards = find_validated_cards()
    
    if not cards:
        print("[Fase 5: BATCH REVIEW] Nenhum card validado para revisar")
        return

    if len(cards) < BATCH_SIZE and not force:
        print(f"[Fase 5: BATCH REVIEW] Apenas {len(cards)}/{BATCH_SIZE} cards prontos.")
        print(f"  Use --force para revisar mesmo assim, ou aguarde acumular.")
        return

    print(f"[Fase 5: BATCH REVIEW] Revisando lote de {len(cards)} cards...")
    
    prompt = build_batch_report(cards)
    report = run_llm_review(prompt)
    
    # Salva relatório
    ensure_contexts_dir()
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = BATCH_DIR / f"batch_report_{timestamp}.md"
    report_file.write_text(report)
    
    mark_as_reviewed(cards)
    
    print(f"[Fase 5] ✅ Relatório salvo em {report_file}")
    print(f"[Fase 5] Cards revisados: {len(cards)}")
    print(f"\n--- RELATÓRIO ---\n{report[:1000]}...\n--- FIM ---")
    
    # Summary JSON for automation
    print(json.dumps({
        "status": "ok",
        "batch_size": len(cards),
        "report_file": str(report_file),
        "cards": [c["card_id"] for c in cards],
    }))


if __name__ == "__main__":
    main()
