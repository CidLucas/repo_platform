# services/ferramentas/evaluation_suite/workflows/boleta_trader/evaluator.py

import json
from typing import Dict, Any

def evaluate_boleta(run, example) -> Dict[str, Any]:
    """
    Avaliador customizado para o LangSmith que compara a boleta extraída
    com a boleta esperada (ground truth).
    """
    try:
        predicted_boleta_str = run.outputs.get('boleta_extraida')
        if not predicted_boleta_str:
            return {"score": 0, "comment": "Falha: Nenhuma boleta foi extraída."}

        predicted_boleta = predicted_boleta_str

        # CORREÇÃO APLICADA AQUI: Busca a chave 'golden_answer' ao invés de 'expected_output'
        expected_boleta_str = example.outputs.get('golden_answer')
        if not expected_boleta_str:
            return {"score": 0, "comment": "Erro no Dataset: 'golden_answer' não encontrado."}

        expected_boleta = json.loads(expected_boleta_str)

        # Se o gabarito indica que nada deveria ser extraído
        if expected_boleta.get('vendedor') is None:
            # E o modelo de fato não extraiu nada (ou extraiu um dict vazio)
            if not predicted_boleta:
                 return {"score": 1, "comment": "Sucesso: Nenhuma boleta foi extraída, como esperado."}
            else:
                 return {"score": 0, "comment": "Falha: Uma boleta foi extraída quando não deveria."}

        # Lógica de Comparação
        vendedor_match = predicted_boleta['vendedor'] == expected_boleta['vendedor']
        comprador_match = predicted_boleta['comprador'] == expected_boleta['comprador']
        cotacao_match = abs(predicted_boleta['valor_cotacao'] - expected_boleta['valor_cotacao']) < 0.01
        valor_total_match = abs(predicted_boleta['valor_total'] - expected_boleta['valor_total']) < 0.01

        score = (vendedor_match + comprador_match + cotacao_match + valor_total_match) / 4.0

        if score == 1.0:
            comment = "Sucesso: Todos os campos correspondem."
        else:
            comment = (
                f"Falha Parcial:\n"
                f"- Vendedor: {'OK' if vendedor_match else 'FALHA'}\n"
                f"- Comprador: {'OK' if comprador_match else 'FALHA'}\n"
                f"- Cotação: {'OK' if cotacao_match else 'FALHA'}\n"
                f"- Valor Total: {'OK' if valor_total_match else 'FALHA'}"
            )

        return {"score": score, "comment": comment}

    except Exception as e:
        return {"score": 0, "comment": f"Erro catastrófico durante a avaliação: {str(e)}"}