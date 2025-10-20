# services/ferramentas/evaluation_suite/run_evaluation.py

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from tqdm import tqdm
import importlib
from pprint import pprint

# --- Configurações ---
load_dotenv()
WORKFLOW_UNDER_TEST = "boleta_trader"

def is_langsmith_enabled():
    """Verifica se as variáveis de ambiente do LangSmith estão configuradas."""
    return all(os.getenv(var) for var in ["LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2"])

def main():
    print(f"--- Iniciando observação do workflow '{WORKFLOW_UNDER_TEST}' ---")

    # --- 1. Setup ---
    workflow_module = importlib.import_module(f"workflows.{WORKFLOW_UNDER_TEST}.workflow")
    evaluator_module = importlib.import_module(f"workflows.{WORKFLOW_UNDER_TEST}.evaluator")


    # --- 2. Preparação da Simulação ---
    dataset_csv_path = f"workflows/{WORKFLOW_UNDER_TEST}/data/amostra_teste_anonimizada.csv"
    try:
        run_df = pd.read_csv(dataset_csv_path)
    except FileNotFoundError:
        print(f"--- ❌ ERRO: Arquivo de dataset não encontrado em '{dataset_csv_path}' ---", file=sys.stderr)
        sys.exit(1)

    # Preenche valores NaN na coluna 'message' para evitar erros
    run_df['message'] = run_df['message'].fillna('')
    print(f"Dataset com {len(run_df)} mensagens carregado para uma única simulação de conversa.\n")

    # --- 3. Execução da Simulação Única ---

    # PONTO CHAVE DA CORREÇÃO:
    # A memória e o workflow são criados UMA VEZ, fora do loop de mensagens.
    # Isso simula um único chat contínuo.
    memory = SqliteSaver.from_conn_string(":memory:")
    app_with_memory = workflow_module.get_workflow(checkpointer=memory)

    # Usamos um ID de conversa fixo para toda a execução do teste.
    conversation_id = "simulacao_unica_conversa"
    config = {"configurable": {"thread_id": conversation_id}}

    final_state_of_conversation = None

    print(f"--- [DEBUG] Processando Conversa: {conversation_id} ---")

    # Itera sobre cada MENSAGEM do DataFrame
    for _, row in tqdm(run_df.iterrows(), total=len(run_df), desc="Processando Mensagens"):
        sender_id = str(row['nome_fantasia'])
        message_content = str(row['message']).strip()

        # Pula mensagens vazias que possam existir no CSV
        if not message_content:
            continue

        print(f"\n[DEBUG] Enviando de '{sender_id}': '{message_content}'")

        human_message = HumanMessage(content=message_content, name=sender_id)
        inputs = {"messages": [human_message]}

        # Envia a mensagem e atualiza o estado final a cada passo
        for chunk in app_with_memory.stream(inputs, config=config, stream_mode="values"):
            final_state_of_conversation = chunk


    print(f"--- [DEBUG] Fim da Conversa: {conversation_id} ---")

    # --- 4. Avaliação (ao final de TODA a conversa) ---
    print("\n--- ✅ EXECUÇÃO CONCLUÍDA ---")
    if final_state_of_conversation:
        mock_run_obj = type('obj', (object,), {'outputs': final_state_of_conversation})()
        summary = evaluator_module.summarize_for_manual_review(mock_run_obj)

        # --- 5. Relatório Final ---
        print("\n--- RELATÓRIO DE OBSERVAÇÃO ---")
        results_df = pd.DataFrame([{"conversation_id": conversation_id, **summary}])
        print(results_df.to_string(index=False))
    else:
        print("Nenhum resultado foi sumarizado.")

if __name__ == "__main__":
    main()