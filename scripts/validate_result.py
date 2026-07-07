#!/usr/bin/env python3
"""
Fase 4: VALIDAÇÃO — Verifica se o output do OpenCode atende os ACs.
Zero LLM — roda pytest, confere arquivos, verifica contrato.

Uso: python3 scripts/validate_result.py <card_id>
Entrada: scripts/contexts/<card_id>.json + <card_id>_result.json
Saída: scripts/contexts/<card_id>_validation.json
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pipeline_common import REPO_ROOT, read_context, read_result, run_cmd


def check_opencodes_exit(result: dict) -> dict:
    """Verifica se o OpenCode terminou com sucesso."""
    checks = []
    all_ok = True

    if result.get("exit_code") == 0:
        checks.append({"check": "OpenCode exit code", "status": "pass", "detail": "exit=0"})
    else:
        checks.append({"check": "OpenCode exit code", "status": "fail",
                       "detail": f"exit={result.get('exit_code')}, {result.get('error', '')}"})
        all_ok = False

    if result.get("pr_number"):
        checks.append({"check": "PR criado", "status": "pass",
                       "detail": f"PR #{result['pr_number']}"})
    else:
        checks.append({"check": "PR criado", "status": "warn",
                       "detail": "PR number não detectado no output"})

    return {"all_ok": all_ok, "checks": checks}


def run_pytest(context: dict) -> dict:
    """Roda pytest no teste RED especificado."""
    test_red = context.get("test_red")
    if not test_red:
        return {"status": "skipped", "detail": "Nenhum teste RED especificado"}
    
    test_path = REPO_ROOT / test_red
    if not test_path.exists():
        return {"status": "error", "detail": f"Arquivo de teste não encontrado: {test_path}"}

    result = run_cmd(["python3", "-m", "pytest", str(test_path), "-v", "--tb=short"],
                     timeout=120)
    
    # Parse output
    passed = "passed" in result["output"] and "failed" not in result["output"]
    failed_count = 0
    for line in result["output"].split("\n"):
        if "FAILED" in line:
            failed_count += 1

    return {
        "status": "pass" if passed else "fail",
        "detail": f"{'✅ Passou' if passed else '❌ Falhou'} ({failed_count} falhas)",
        "output": result["output"][:2000],
        "exit_code": result["exit_code"],
        "passed": passed,
        "failed_count": failed_count,
    }


def check_changed_files(context: dict) -> dict:
    """Verifica se arquivos foram modificados (git diff)."""
    result = run_cmd(["git", "diff", "--name-only"], timeout=15)
    files = [f.strip() for f in result["output"].split("\n") if f.strip()]
    
    return {
        "status": "pass" if files else "warn",
        "detail": f"{len(files)} arquivo(s) modificado(s)",
        "files": files,
    }


def check_acs_coverage(acs: list[str], output: str) -> list[dict]:
    """Tenta verificar se cada AC foi mencionado no output do OpenCode.
    Heurística simples — não substitui revisão humana."""
    checks = []
    for i, ac in enumerate(acs, 1):
        # Procura keywords do AC no output
        keywords = ac.lower().split()[:5]  # primeiras 5 palavras
        found = any(kw in output.lower() for kw in keywords if len(kw) > 3)
        
        # Procura "AC{i}" ou AC descriptions
        ac_pattern = f"ac{i}" in output.lower()
        ac_description_found = any(kw in output.lower() for kw in ["implement", ac.split(" ")[0].lower()] if len(kw) > 3)
        
        checks.append({
            "ac": f"AC{i}: {ac}",
            "status": "pass" if found or ac_pattern else "warn",
            "evidence": "mencionado no output" if found else "não verificado automaticamente",
        })
    return checks


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/validate_result.py <card_id>")
        sys.exit(1)

    card_id = sys.argv[1]
    print(f"[Fase 4: VALIDAÇÃO] Validando resultado de {card_id}...")

    context = read_context(card_id)
    if not context:
        print(f"[Fase 4] ERRO: context.json não encontrado para {card_id}")
        sys.exit(1)

    result_data = read_result(card_id)
    if not result_data:
        print(f"[Fase 4] ERRO: result.json não encontrado para {card_id}")
        sys.exit(1)

    acs = context.get("acceptance_criteria", [])
    output = result_data.get("output", "")

    # 1. Verifica exit code do OpenCode
    oc_check = check_opencodes_exit(result_data)

    # 2. Roda pytest
    test_check = run_pytest(context)

    # 3. Verifica arquivos modificados
    files_check = check_changed_files(context)

    # 4. Verifica cobertura dos ACs no output
    ac_checks = check_acs_coverage(acs, output)

    # Monta resultado
    validation = {
        "task_id": card_id,
        "status": "pass" if (oc_check["all_ok"] and test_check.get("status") == "pass") else "fail",
        "pr_number": result_data.get("pr_number"),
        "checks": {
            "opencode": oc_check["checks"],
            "pytest": test_check,
            "changed_files": files_check,
            "acs": ac_checks,
        },
        "summary": {
            "total_checks": len(oc_check["checks"]) + 1 + 1 + len(ac_checks),
            "passes": sum(1 for c in oc_check["checks"] if c["status"] == "pass") +
                      (1 if test_check.get("status") == "pass" else 0) +
                      (1 if files_check.get("status") == "pass" else 0) +
                      sum(1 for c in ac_checks if c["status"] == "pass"),
            "fails": sum(1 for c in oc_check["checks"] if c["status"] == "fail") +
                     (1 if test_check.get("status") == "fail" else 0) +
                     (1 if files_check.get("status") == "fail" else 0) +
                     sum(1 for c in ac_checks if c["status"] == "fail"),
        },
    }

    # Salva validação
    from pipeline_common import ensure_contexts_dir, CONTEXTS_DIR
    ensure_contexts_dir()
    val_file = CONTEXTS_DIR / f"{card_id}_validation.json"
    val_file.write_text(json.dumps(validation, indent=2, ensure_ascii=False))

    print(f"[Fase 4] ✅ Validação salva em scripts/contexts/{card_id}_validation.json")
    print(f"[Fase 4] Status: {'✅ PASS' if validation['status'] == 'pass' else '❌ FAIL'}")
    print(f"[Fase 4] PR: #{validation['pr_number']}" if validation['pr_number'] else "[Fase 4] PR: não detectado")
    print(f"[Fase 4] Testes: {test_check.get('detail', 'N/A')}")
    print(f"[Fase 4] Arquivos: {files_check.get('detail', 'N/A')}")
    print(f"[Fase 4] ACs: {sum(1 for c in ac_checks if c['status'] == 'pass')}/{len(acs)} cobertas")

    sys.exit(0 if validation["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
