# services/ferramentas/evaluation_suite/run_evaluation.py

import os
import pandas as pd
from dotenv import load_dotenv
from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.schemas import Example
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

# Carrega as variáveis de ambiente. Garanta que LANGCHAIN_PROJECT esteja no seu .env!
load_dotenv()

from workflows.boleta_trader.workflow import get_workflow
from workflows.boleta_trader.evaluator import evaluate_boleta

def prepare_langsmith_dataset(client: Client, dataset_name: str, csv_path: str):
    """Garante que o dataset exista no LangSmith, recriando-o se necessário."""
    if client.has_dataset(dataset_name=dataset_name):
        client.delete_dataset(dataset_name=dataset_name)

    dataset = client.upload_csv(
        csv_file=csv_path,
        input_keys=['test_id', 'phone_number', 'message'],
        output_keys=['golden_answer'],
        name=dataset_name,
        description="Dataset para avaliação robusta do workflow de extração de boletas."
    )
    print(f"Dataset '{dataset_name}' carregado com sucesso.")
    return dataset

def main():
    """
    Orquestra a avaliação de ponta a ponta usando as melhores práticas do LangSmith.
    """
    print("Iniciando a avaliação automatizada do workflow 'Boleta Trader'...")

    client = Client()

    dataset_name = "Boleta Trader Evals"
    csv_path = "workflows/boleta_trader/data/dataset.csv"
    prepare_langsmith_dataset(client, dataset_name, csv_path)

    # Instancia o checkpointer de memória e o workflow
    memory = MemorySaver()
    app = get_workflow(checkpointer=memory)

    def target_for_eval(row: dict):
        """
        Função-alvo que o `evaluate` chamará para CADA LINHA do dataset.
        Ela gerencia o estado da conversa usando o 'test_id'.
        """
        # 1. Extrai os dados da linha do dataset
        test_id = str(row['test_id'])
        phone_number = str(row['phone_number'])
        message_content = row['message']

        # 2. Configura a memória para usar o test_id como a chave da conversa
        config = {"configurable": {"thread_id": test_id}}

        # 3. Formata a entrada para o workflow
        message = HumanMessage(content=message_content, name=phone_number)
        inputs = {"messages": [message]}

        # 4. Invoca o workflow. O checkpointer garante que o estado correto seja carregado.
        final_state = app.invoke(inputs, config=config)

        # 5. Retorna o output relevante para o avaliador.
        #    Se uma boleta foi extraída, ela estará aqui. Senão, o campo será None.
        return {"boleta_extraida": final_state.get('boleta_extraida')}

    print("Executando o workflow em todo o dataset usando o `evaluate` do LangSmith...")

    evaluate(
        target_for_eval,
        data=dataset_name,
        evaluators=[evaluate_boleta], # Nosso avaliador customizado
        experiment_prefix="boleta-trader-robust-run",
        metadata={
            "version": "3.0",
            "description": "Avaliação robusta usando a função evaluate com gerenciamento de estado."
        }
    )

    print("\n--- ✅ AVALIAÇÃO CONCLUÍDA ---")
    print(f"Verifique os resultados detalhados no seu projeto '{os.getenv('LANGCHAIN_PROJECT')}' no LangSmith!")

if __name__ == "__main__":
    main()