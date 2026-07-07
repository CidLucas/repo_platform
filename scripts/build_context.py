#!/usr/bin/env python3
"""
Fase 2: CONTEXTO — Monta context.json a partir do card kanban.
Zero LLM — só heurísticas + filesystem.

Uso: python3 scripts/build_context.py <card_id>
Saída: scripts/contexts/<card_id>.json
"""

import json
import sys
from pathlib import Path

from pipeline_common import (
    REPO_ROOT,
    get_card,
    parse_goal,
    parse_acs,
    parse_test_red,
    parse_source_hint,
    write_context,
)


def find_test_red_heuristic(task_title: str) -> str | None:
    """Heurística: encontra teste RED pelo título da task."""
    test_dir = REPO_ROOT / "tests" / "behaviors"
    if not test_dir.exists():
        return None

    keywords = task_title.lower().replace("_", " ").replace("-", " ").split()
    candidates = []

    for f in sorted(test_dir.glob("test_*.py")):
        fname = f.stem.lower()
        score = 0
        for kw in keywords:
            if len(kw) <= 2:
                continue
            if kw in fname:
                score += len(kw)
        if score > 0:
            candidates.append((score, str(f.relative_to(REPO_ROOT))))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    # Fallback: procura número do behavior (ex: b3 em BKL-036)
    for f in test_dir.glob("test_*.py"):
        fname = f.stem
        # Extrai números da task title
        nums = [w for w in task_title.split() if any(c.isdigit() for c in w)]
        for num in nums:
            if num.lower() in fname:
                return str(f.relative_to(REPO_ROOT))

    return None


def infer_source_from_test(test_path: str | None) -> str | None:
    """Heurística: mapeia teste → source."""
    if not test_path:
        return None

    name = Path(test_path).stem.replace("test_", "")
    keywords = name.split("_")

    src_dirs = [
        REPO_ROOT / "apps" / "blu_v3" / "src" / "services",
        REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app",
        REPO_ROOT / "apps" / "blu_v3" / "src" / "hooks",
        REPO_ROOT / "apps" / "blu_v3" / "src",
    ]

    for d in src_dirs:
        if d.exists():
            for f in d.rglob("*.ts"):
                fname_lower = f.stem.lower()
                for kw in keywords:
                    if len(kw) > 3 and kw in fname_lower:
                        return str(f.relative_to(REPO_ROOT))
    return None


def load_business_rules(task_title: str) -> list:
    """Carrega regras de negócio do contracts/business/rules.json."""
    rules_file = REPO_ROOT / "contracts" / "business" / "rules.json"
    if rules_file.exists():
        try:
            data = json.loads(rules_file.read_text())
            relevant = [
                r for r in data.get("rules", [])
                if any(k in task_title.lower() for k in r.get("scope", "").lower().split())
            ]
            return relevant
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            pass
    return []


def build_context(task_id: str, task_title: str, task_body: str) -> dict:
    """Constrói o context.json completo."""
    goal = parse_goal(task_body) or task_title
    acs = parse_acs(task_body)
    test_red = parse_test_red(task_body) or find_test_red_heuristic(task_title)
    source_hint = parse_source_hint(task_body) or infer_source_from_test(test_red)

    context = {
        "task_id": task_id,
        "goal": goal,
        "description": task_body[:500],
        "acceptance_criteria": acs,
        "repo_root": str(REPO_ROOT),
        "test_red": test_red,
        "source_hint": source_hint,
        "llm_wiki": str(REPO_ROOT / "docs" / "llm_wiki" / "index.md") if (REPO_ROOT / "docs" / "llm_wiki" / "index.md").exists() else None,
        "business_rules": load_business_rules(task_title),
        "constraints": {
            "no_llm": "sem llm" in task_body.lower(),
            "max_files": 10,
            "max_lines_per_file": 200,
        },
        "output_format": {
            "changed_files": "lista de arquivos modificados",
            "test_results": "resultado dos testes",
            "coverage": "porcentagem de cobertura",
            "review_notes": "notas de review",
        },
    }
    return context


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/build_context.py <card_id>")
        sys.exit(1)

    card_id = sys.argv[1]
    print(f"[Fase 2: CONTEXTO] Lendo card {card_id}...", flush=True)

    card = get_card(card_id)
    if not card:
        print(f"[Fase 2] ERRO: Card {card_id} não encontrado ou não pôde ser lido")
        sys.exit(1)

    title = card.get("title", "")
    body = card.get("body", "")

    print(f"[Fase 2] Card: {title[:100]}", flush=True)
    print(f"[Fase 2] Body length: {len(body)} chars", flush=True)

    context = build_context(card_id, title, body)

    print(f"[Fase 2] Goal: {context['goal'][:80] if context['goal'] else 'NÃO ENCONTRADO'}", flush=True)
    print(f"[Fase 2] ACs extraídas: {len(context['acceptance_criteria'])}", flush=True)
    print(f"[Fase 2] Teste RED: {context['test_red'] or 'não encontrado'}", flush=True)
    print(f"[Fase 2] Source hint: {context['source_hint'] or 'não encontrado'}", flush=True)

    write_context(card_id, context)
    print(f"[Fase 2] ✅ Contexto salvo em scripts/contexts/{card_id}.json", flush=True)

    # Saída JSON para consumo por script pai
    print(json.dumps({
        "status": "ok",
        "task_id": card_id,
        "goal": context["goal"],
        "acs_count": len(context["acceptance_criteria"]),
        "test_red": context["test_red"],
        "context_file": f"scripts/contexts/{card_id}.json",
    }))


if __name__ == "__main__":
    main()
