# services/ferramentas/evaluation_suite/run_evaluation.py

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from tqdm import tqdm
from datetime import datetime
import importlib

# --- Configurações ---
load_dotenv()
WORKFLOW_UNDER_TEST = "boleta_trader"
PROJECT_NAME_PREFIX = "Boleta-Trader-Ev"

def main():
    """
    Orquestra a avaliação simulando CONVERSAS COMPLETAS e avaliando o resultado
    final de cada uma.
    """
    print(f"--- Iniciando avaliação do workflow '{WORKFLOW_UNDER_TEST}' ---")

    # --- 1. Setup do Ambiente e LangSmith ---
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("--- ❌ ERRO: 'LANGCHAIN_API_KEY' não encontrada no .env ---", file=sys.stderr)
        sys.exit(1)

    workflow_module = importlib.import_module(f"workflows.{WORKFLOW_UNDER_TEST}.workflow")
    evaluator_module = importlib.import_module(f"workflows.{WORKFLOW_UNDER_TEST}.evaluator")

    project_name = f"{PROJECT_NAME_PREFIX}-{WORKFLOW_UNDER_TEST}-{datetime.now().strftime('%Y%m%d-%H%M')}"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    client = Client()

    # --- 2. Preparação da Simulação ---
    dataset_csv_path = f"workflows/{WORKFLOW_UNDER_TEST}/data/dataset.csv"
    eval_df = pd.read_csv(dataset_csv_path)
    eval_df['conversation_id'] = eval_df['test_id'].apply(lambda x: x.split('_')[0])
    print(f"Dataset com {len(eval_df)} mensagens em {eval_df['conversation_id'].nunique()} conversas carregado.")

    print(f"\n--- INICIANDO SIMULAÇÃO POR CONVERSA ---")
    print(f"Traces serão enviados para o projeto: '{project_name}' no LangSmith\n")

    evaluation_results = []

    # --- 3. Execução: Itera sobre cada CONVERSA ---
    for conv_id, group in tqdm(eval_df.groupby('conversation_id'), desc="Processando Conversas"):
        memory = SqliteSaver.from_conn_string(":memory:")
        app_with_memory = workflow_module.get_workflow(checkpointer=memory)
        config = {"configurable": {"thread_id": conv_id}}

        final_state = None
        for _, row in group.iterrows():
            human_message = HumanMessage(content=row['message'], name=str(row['phone_number']))
            inputs = {"messages": [human_message]}

            # #########################################################
            # ## CORREÇÃO DEFINITIVA DO KEYERROR APLICADA AQUI ##
            # #########################################################
            # O último 'chunk' emitido pelo stream é o estado final.
            for chunk in app_with_memory.stream(inputs, config=config, stream_mode="values"):
                final_state = chunk
            # #########################################################

        # --- 4. Avaliação: Acontece no final da conversa ---
        golden_answer = group.iloc[-1]['golden_answer']

        if pd.notna(golden_answer):
            mock_run_obj = type('obj', (object,), {'outputs': final_state})()
            example = type('obj', (object,), {'outputs': {'golden_answer': golden_answer}})()
            eval_result = evaluator_module.evaluate_boleta(mock_run_obj, example)
            evaluation_results.append({"conversation_id": conv_id, **eval_result})

    print("\n--- ✅ SIMULAÇÃO CONCLUÍDA ---")

    # --- 5. Relatório Final ---
    print("\n--- RELATÓRIO FINAL DA AVALIAÇÃO ---")
    if evaluation_results:
        results_df = pd.DataFrame(evaluation_results)
        successes = results_df[results_df['score'] == 1].shape[0]
        total_tests = len(results_df)
        accuracy = (successes / total_tests) * 100 if total_tests > 0 else 0

        print(f"Total de Conversas com Boleta Avaliadas: {total_tests}")
        print(f"Sucessos: {successes}")
        print(f"Taxa de Acerto: {accuracy:.2f}%\n")
        print("Resultados Detalhados:")
        print(results_df.to_string(index=False))
    else:
        print("Nenhuma conversa com 'golden_answer' foi encontrada para avaliar.")

    print(f"\nVerifique os traces detalhados no projeto '{project_name}' no LangSmith.")

if __name__ == "__main__":
    main()