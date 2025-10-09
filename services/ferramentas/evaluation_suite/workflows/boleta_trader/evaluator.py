# services/ferramentas/evaluation_suite/workflows/boleta_trader/evaluator.py

import json
from typing import Dict, Any
import pandas as pd

# O mapa de nomes precisa estar disponível para o avaliador também.
PHONE_TO_NAME_MAP = {
    "+5521999990001": "João",
    "+5521999990002": "Maria",
    "+5521999990003": "Carlos",
    "+5521999990004": "Ana"
}

def evaluate_boleta(run, example) -> Dict[str, Any]:
    """
    Avaliador customizado e sincronizado com o estado final do workflow.
    Avalia o resultado final de uma conversa completa.
    """
    try:
        # 1. Obter dados do estado final (run.outputs)
        final_state = run.outputs
        predicted_data = final_state.get('dados_extraidos')

        # 2. Obter gabarito (golden_answer) do final da conversa
        expected_boleta_str = example.outputs.get('golden_answer')

        # Caso 1: Nenhuma boleta é esperada no final desta conversa.
        if pd.isna(expected_boleta_str):
            if final_state.get('boleta_formatada'):
                return {"score": 0, "comment": "Falha: Boleta gerada quando nenhuma era esperada."}
            else:
                return {"score": 1, "comment": "Sucesso: Nenhuma boleta era esperada e nenhuma foi gerada."}

        # Caso 2: Uma boleta é esperada.
        if not predicted_data or "error" in predicted_data:
            return {"score": 0, "comment": "Falha: Boleta esperada, mas dados numéricos não foram extraídos."}

        expected_boleta = json.loads(expected_boleta_str)

        # 3. Mapear IDs previstos para nomes
        predicted_vendedor_id = final_state.get('vendedor_id', '')
        predicted_comprador_id = final_state.get('comprador_id', '')
        vendedor_id_clean = predicted_vendedor_id.replace('+', '') if predicted_vendedor_id else ''
        comprador_id_clean = predicted_comprador_id.replace('+', '') if predicted_comprador_id else ''
        predicted_vendedor_nome = next((name for key, name in PHONE_TO_NAME_MAP.items() if vendedor_id_clean in key), None)
        predicted_comprador_nome = next((name for key, name in PHONE_TO_NAME_MAP.items() if comprador_id_clean in key), None)

        # 4. Lógica de Comparação Robusta
        vendedor_match = predicted_vendedor_nome == expected_boleta.get('vendedor')
        comprador_match = predicted_comprador_nome == expected_boleta.get('comprador')
        cotacao_match = abs(predicted_data.get('valor_cotacao', 0.0) - expected_boleta.get('valor_cotacao', -1.0)) < 0.01
        valor_total_match = abs(predicted_data.get('valor_total', 0.0) - expected_boleta.get('valor_total', -1.0)) < 0.01

        score = (vendedor_match + comprador_match + cotacao_match + valor_total_match) / 4.0

        if score == 1.0:
            comment = "Sucesso: Todos os campos correspondem."
        else:
            # CORREÇÃO DE SINTAXE: Lógica de formatação simplificada e robusta
            report_lines = ["Falha Parcial:"]

            vendedor_status = 'OK' if vendedor_match else f"FALHA (Esperado: {expected_boleta.get('vendedor')}, Previsto: {predicted_vendedor_nome})"
            report_lines.append(f"- Vendedor: {vendedor_status}")

            comprador_status = 'OK' if comprador_match else f"FALHA (Esperado: {expected_boleta.get('comprador')}, Previsto: {predicted_comprador_nome})"
            report_lines.append(f"- Comprador: {comprador_status}")

            cotacao_status = 'OK' if cotacao_match else f"FALHA (Esperado: {expected_boleta.get('valor_cotacao')}, Previsto: {predicted_data.get('valor_cotacao')})"
            report_lines.append(f"- Cotação: {cotacao_status}")

            valor_total_status = 'OK' if valor_total_match else f"FALHA (Esperado: {expected_boleta.get('valor_total')}, Previsto: {predicted_data.get('valor_total')})"
            report_lines.append(f"- Valor Total: {valor_total_status}")

            comment = "\n".join(report_lines)

        return {"score": score, "comment": comment}

    except Exception as e:
        return { "score": 0, "comment": f"Erro catastrófico durante a avaliação: {type(e).__name__} - {str(e)}" }