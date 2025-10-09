# check_langsmith.py
import os
from dotenv import load_dotenv
from langsmith import Client

print("--- Iniciando diagnóstico LangSmith ---")

# 1. Carregar variáveis de ambiente
if load_dotenv():
    print("✅ Arquivo .env encontrado e carregado.")
else:
    print("❌ Arquivo .env NÃO encontrado.")
    exit()

# 2. Ler e verificar as variáveis
api_key = os.getenv("LANGCHAIN_API_KEY")
project = os.getenv("LANGCHAIN_PROJECT")

print(f"API Key Encontrada: {'Sim' if api_key else 'Não'}")
print(f"Project Encontrado: {'Sim' if project else 'Não'}")

if not api_key or not project:
    print("--- ❌ ERRO: Variáveis de ambiente faltando. ---")
    exit()

# 3. Tentar instanciar o cliente
try:
    print("\nTentando instanciar o langsmith.Client()...")
    client = Client()
    if client:
        print("✅ Cliente LangSmith instanciado com sucesso!")
        print(f"   -> Tipo do objeto: {type(client)}")
    else:
        # Este é o cenário que causa o seu erro!
        print("❌ ATENÇÃO: langsmith.Client() retornou None!")
        exit()

    # 4. Tentar criar um run simples (fora de um 'with' para teste)
    print("\nTentando criar um run de teste...")
    test_run = client.create_run(name="Teste de Conexão", run_type="test")
    if test_run:
        print("✅ Run de teste criado com sucesso!")
        print(f"   -> ID do Run: {test_run.id}")
        client.end_run(test_run) # Finaliza o run
    else:
        print("❌ ERRO CRÍTICO: client.create_run() retornou None!")

except Exception as e:
    print(f"\n--- ❌ Ocorreu uma exceção inesperada ---")
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Diagnóstico concluído ---")