# scripts/evaluate_agent.py
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fakeredis import FakeStrictRedis

# Importe os componentes que você precisa testar
from atendente_api.core.graph import create_agent_graph
from atendente_api.core.state import AgentState
from atendente_api.services.context_service import ContextService
from atendente_api.services.redis_service import RedisService
from atendente_api.core.schemas import VizuClientContext

# --- 1. SETUP DO AMBIENTE DE TESTE CONTROLADO ---

# Mock do Banco de Dados: Use SQLite em memória
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# (Aqui você pode adicionar código para criar as tabelas e popular com um cliente de teste)

# Mock do Redis
fake_redis_client = FakeStrictRedis()
redis_service = RedisService(redis_client=fake_redis_client)

# Instancia o ContextService com o DB em memória
db_session = TestingSessionLocal()
context_service = ContextService(db_session, redis_service)

# Instancia o Grafo do Agente
agent_graph = create_agent_graph()

# --- 2. CARREGAR O DATASET DE CONVERSAS ---
# Exemplo de conversas_teste.csv:
# conversation_id,user_input,expected_output_keywords
# 1,"Olá, gostaria de agendar um corte de cabelo","agendar,horários"
# 1,"Pode ser às 15h?","confirmado,15h"
# 2,"Qual o status do meu pedido 123?","pedido,status"

df = pd.read_csv("data/conversas_teste.csv")
results = []

# --- 3. EXECUTAR A AVALIAÇÃO EM LOTE ---

# Primeiro, pegue o contexto UMA VEZ para simular o cliente real
# (Supondo que você populou o DB em memória com um cliente com essa API Key)
test_api_key = "api_key_de_teste"
client_context = context_service.get_client_context(test_api_key)

if not client_context:
    raise Exception("Não foi possível carregar o contexto do cliente de teste do DB em memória.")

# Itera sobre cada conversa no DataFrame
for conv_id, group in df.groupby("conversation_id"):
    print(f"--- Iniciando Conversa de Teste #{conv_id} ---")

    # Config para o LangGraph saber qual thread/conversa estamos
    config = {"configurable": {"thread_id": f"test-thread-{conv_id}"}}

    # O estado inicial precisa do contexto do cliente
    initial_state = AgentState(messages=[], contexto_cliente=client_context)

    for index, row in group.iterrows():
        user_input = row["user_input"]
        print(f"  [Usuário]: {user_input}")

        # Invoca o grafo com a mensagem do usuário
        # O estado da conversa é mantido automaticamente pelo LangGraph usando o thread_id
        final_state = agent_graph.invoke(
            {"messages": ("human", user_input)},
            config=config,
            # Se for a primeira mensagem, podemos precisar passar o estado inicial
            # (isso depende da implementação exata do seu grafo)
        )

        # Pega a última resposta da IA
        ai_response = final_state["messages"][-1].content
        print(f"  [Agente]: {ai_response}")

        # Avalia o resultado
        expected_keywords = row["expected_output_keywords"].split(',')
        is_success = all(keyword in ai_response for keyword in expected_keywords)

        results.append({
            "conversation_id": conv_id,
            "user_input": user_input,
            "ai_response": ai_response,
            "success": is_success
        })

# --- 4. EXIBIR O RELATÓRIO ---
results_df = pd.DataFrame(results)
print("\n--- Relatório de Avaliação ---")
print(results_df)

success_rate = results_df["success"].mean() * 100
print(f"\nTaxa de Sucesso: {success_rate:.2f}%")