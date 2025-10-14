# services/ferramentas/evaluation_suite/workflows/boleta_trader/evaluator.py

from typing import Dict, Any
import re

def summarize_for_manual_review(run) -> Dict[str, Any]:
    """
    Extrai e organiza os dados do estado final para fácil revisão humana.
    Esta versão é robusta à limpeza de estado que ocorre no workflow.
    """
    # Pega o dicionário de outputs do estado final da execução
    if not run or not run.outputs:
        return {"boleta_gerada": False, "detalhes": "A execução não produziu um estado final."}

    final_state = run.outputs
    boleta_formatada = final_state.get('boleta_formatada')

    # --- Cenário 1: Sucesso ---
    # A fonte da verdade é a existência da boleta formatada.
    if boleta_formatada:
        # Extrai os dados diretamente da string da boleta para o relatório.
        # Isso torna o avaliador independente dos campos de estado intermediários.
        try:
            vendedor = re.search(r"\*\*Vendedor:\*\* (.*?)\n", boleta_formatada).group(1)
            comprador = re.search(r"\*\*Comprador:\*\* (.*?)\n", boleta_formatada).group(1)
            cotacao = re.search(r"\*\*Cotação:\*\* R\$ (.*?)\n", boleta_formatada).group(1)
            volume = re.search(r"\*\*Volume:\*\* \$(.*)", boleta_formatada).group(1)

            summary_details = (
                f"Vendedor: {vendedor}, Comprador: {comprador}, "
                f"Cotação: {cotacao}, Volume: {volume}"
            )

            return {
                "boleta_gerada": True,
                "detalhes": summary_details
            }
        except AttributeError:
            # Caso a boleta exista mas tenha um formato inesperado
            return {
                "boleta_gerada": True,
                "detalhes": f"Boleta gerada, mas com formato irreconhecível: {boleta_formatada}"
            }

    # --- Cenário 2: Falha ou Nenhuma Ação ---
    # Se não houve boleta, investigamos a causa.
    else:
        dados_extraidos = final_state.get('dados_extraidos')

        # Verifica se houve um erro explícito na extração
        if isinstance(dados_extraidos, dict) and "error" in dados_extraidos:
            error_details = dados_extraidos.get('error', 'Erro desconhecido')
            return {
                "boleta_gerada": False,
                "detalhes": f"Erro na extração de dados: {error_details}"
            }

        # Se não houve erro explícito, significa que a conversa terminou sem gerar uma transação
        return {
            "boleta_gerada": False,
            "detalhes": "Nenhuma boleta foi formatada ao final da conversa."
        }