# seed_clientes_vizu.py (VERSÃO FINAL E CORRIGIDA)
import requests
import json

# URL base da sua API (verifique a porta no seu docker-compose.yml)
BASE_URL = "http://localhost:8002/api/v1"

# Dados das 5 personas, formatados para o modelo ClienteVizuBase/Create
# Conforme a documentação /docs, os campos são: nome_empresa, tipo_cliente, tier
PERSONAS_PARA_CRIACAO = [
    {
        "nome_empresa": "Oficina Mendes",
        "tipo_cliente": "externo",
        "tier": "sme"
    },
    {
        "nome_empresa": "Studio J",
        "tipo_cliente": "externo",
        "tier": "sme"
    },
    {
        "nome_empresa": "Casa com Alma",
        "tipo_cliente": "externo",
        "tier": "sme"
    },
    {
        "nome_empresa": "Consultório Odontológico Dra. Beatriz Almeida",
        "tipo_cliente": "externo",
        "tier": "sme"
    },
    {
        "nome_empresa": "Marcos Eletricista",
        "tipo_cliente": "externo",
        "tier": "sme"
    }
]

def populate_clientes_vizu():
    """Envia os dados de cada persona para o endpoint /clientes da clients_api."""
    headers = {"Content-Type": "application/json"}
    print("--- INICIANDO POPULAÇÃO DA TABELA 'cliente_vizu' (v2) ---\n")

    for persona_data in PERSONAS_PARA_CRIACAO:
        company_name = persona_data["nome_empresa"]
        print(f"[*] Criando cliente: {company_name}...")

        try:
            # O endpoint correto é /clientes (sem a barra no final)
            response = requests.post(
                f"{BASE_URL}/clientes",
                data=json.dumps(persona_data),
                headers=headers
            )
            response.raise_for_status()

            created_client = response.json()
            client_id = created_client.get("id")
            api_key = created_client.get("api_key")

            print(f"  [+] SUCESSO! Cliente '{company_name}' criado.")
            print(f"      ID: {client_id}")
            print(f"      API Key: {api_key}\n")

        except requests.exceptions.RequestException as e:
            print(f"  [!] ERRO ao criar cliente '{company_name}': {e}")
            if e.response:
                # Melhorando o tratamento de erros para exibir a mensagem do FastAPI
                error_details = e.response.json().get('detail', 'Nenhum detalhe fornecido.')
                print(f"      Detalhes do Erro de Validação: {error_details}\n")

    print("--- POPULAÇÃO FINALIZADA ---")

if __name__ == "__main__":
    populate_clientes_vizu()