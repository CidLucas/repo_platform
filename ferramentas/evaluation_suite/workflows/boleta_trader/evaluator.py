# ferramentas/evaluation_suite/workflows/boleta_trader/evaluator.py
"""
Boleta Trader Evaluator - Custom evaluation functions for workflow output.

This module provides helper functions to evaluate and summarize the workflow
results for manual review or automated scoring.
"""

import re
from typing import Any


def summarize_for_manual_review(run) -> dict[str, Any]:
    """
    Extract and organize data from the final state for easy human review.

    This version is robust to state clearing that occurs in the workflow.

    Args:
        run: The workflow execution run object containing outputs

    Returns:
        Dict with boleta_gerada (bool) and detalhes (str) describing the result
    """
    # Get the outputs dictionary from the final state
    if not run or not run.outputs:
        return {
            "boleta_gerada": False,
            "detalhes": "The execution did not produce a final state."
        }

    final_state = run.outputs
    boleta_formatada = final_state.get('boleta_formatada')

    # --- Scenario 1: Success ---
    # The source of truth is the existence of the formatted boleta
    if boleta_formatada:
        try:
            # Extract data directly from the boleta string for the report
            # This makes the evaluator independent of intermediate state fields

            # Try to extract from the new format (Confirmation Ticket)
            triggered_by_match = re.search(r"\*\(Triggered by: (.*?)\)\*", boleta_formatada)
            quote_match = re.search(r"\*\*Quote:\*\* R\$ ([\d.]+)", boleta_formatada)
            volume_match = re.search(r"\*\*Volume:\*\* \$([\d,.]+)", boleta_formatada)

            if quote_match and volume_match:
                triggered_by = triggered_by_match.group(1) if triggered_by_match else "Unknown"
                cotacao = quote_match.group(1)
                volume = volume_match.group(1)

                summary_details = (
                    f"Triggered by: {triggered_by}, "
                    f"Quote: {cotacao}, Volume: {volume}"
                )

                return {
                    "boleta_gerada": True,
                    "detalhes": summary_details
                }

            # Fallback: Try legacy format (Vendedor/Comprador)
            vendedor_match = re.search(r"\*\*Vendedor:\*\* (.*?)\n", boleta_formatada)
            comprador_match = re.search(r"\*\*Comprador:\*\* (.*?)\n", boleta_formatada)
            cotacao_legacy = re.search(r"\*\*Cotação:\*\* R\$ (.*?)\n", boleta_formatada)
            volume_legacy = re.search(r"\*\*Volume:\*\* \$(.*)", boleta_formatada)

            if vendedor_match and comprador_match and cotacao_legacy and volume_legacy:
                summary_details = (
                    f"Vendedor: {vendedor_match.group(1)}, "
                    f"Comprador: {comprador_match.group(1)}, "
                    f"Cotação: {cotacao_legacy.group(1)}, "
                    f"Volume: {volume_legacy.group(1)}"
                )
                return {
                    "boleta_gerada": True,
                    "detalhes": summary_details
                }

            # Format not recognized but boleta exists
            return {
                "boleta_gerada": True,
                "detalhes": f"Boleta generated with unrecognized format: {boleta_formatada[:200]}..."
            }

        except AttributeError as e:
            # Boleta exists but has unexpected format
            return {
                "boleta_gerada": True,
                "detalhes": f"Boleta generated, but format unrecognizable: {str(e)}"
            }

    # --- Scenario 2: Failure or No Action ---
    # If no boleta was generated, investigate the cause
    dados_extraidos = final_state.get('dados_extraidos')

    # Check if there was an explicit extraction error
    if isinstance(dados_extraidos, dict) and "error" in dados_extraidos:
        error_details = dados_extraidos.get('error', 'Unknown error')
        return {
            "boleta_gerada": False,
            "detalhes": f"Data extraction error: {error_details}"
        }

    # Check validation data for more context
    dados_validacao = final_state.get('dados_validacao')
    if isinstance(dados_validacao, dict):
        if dados_validacao.get('negociacao_concluida') is False:
            justificativa = dados_validacao.get('justificativa', 'No justification provided')
            return {
                "boleta_gerada": False,
                "detalhes": f"Trade not validated: {justificativa}"
            }

    # No explicit error, conversation ended without generating a transaction
    return {
        "boleta_gerada": False,
        "detalhes": "No boleta was formatted at the end of the conversation."
    }


def evaluate_extraction_accuracy(
    extracted: dict[str, Any],
    expected: dict[str, Any]
) -> dict[str, Any]:
    """
    Compare extracted values against expected ground truth.

    Args:
        extracted: Dictionary with extracted values (valor_cotacao, valor_total)
        expected: Dictionary with expected values

    Returns:
        Dictionary with accuracy metrics
    """
    if not extracted or "error" in extracted:
        return {
            "match": False,
            "score": 0.0,
            "details": "Extraction failed or returned error"
        }

    results = {
        "match": True,
        "score": 1.0,
        "field_results": {}
    }

    # Check quote (cotacao)
    if "valor_cotacao" in expected:
        expected_quote = float(expected["valor_cotacao"])
        extracted_quote = float(extracted.get("valor_cotacao", 0))
        quote_diff = abs(expected_quote - extracted_quote)
        quote_tolerance = expected_quote * 0.001  # 0.1% tolerance

        if quote_diff <= quote_tolerance:
            results["field_results"]["valor_cotacao"] = {"match": True, "diff": quote_diff}
        else:
            results["field_results"]["valor_cotacao"] = {"match": False, "diff": quote_diff}
            results["match"] = False
            results["score"] -= 0.5

    # Check volume (total)
    if "valor_total" in expected:
        expected_volume = float(expected["valor_total"])
        extracted_volume = float(extracted.get("valor_total", 0))
        volume_diff = abs(expected_volume - extracted_volume)
        volume_tolerance = expected_volume * 0.01  # 1% tolerance

        if volume_diff <= volume_tolerance:
            results["field_results"]["valor_total"] = {"match": True, "diff": volume_diff}
        else:
            results["field_results"]["valor_total"] = {"match": False, "diff": volume_diff}
            results["match"] = False
            results["score"] -= 0.5

    results["score"] = max(0.0, results["score"])
    return results
