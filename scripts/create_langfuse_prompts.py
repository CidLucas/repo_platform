#!/usr/bin/env python3
"""
Create Langfuse prompts matching vizu_prompt_management/templates.py
Run: python scripts/create_langfuse_prompts.py
"""
import requests
from base64 import b64encode

# Auth
PUBLIC_KEY = "pk-lf-c64e4914-b8ab-426d-a5ea-14989b564e13"
SECRET_KEY = "sk-lf-dc053e58-e9e3-4822-abfe-89421ca9c2d4"
BASE_URL = "https://us.cloud.langfuse.com"

auth_token = b64encode(f"{PUBLIC_KEY}:{SECRET_KEY}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {auth_token}",
    "Content-Type": "application/json"
}

# Prompts matching templates.py structure
PROMPTS = {
    # Action prompts (atendente folder)
    "atendente/confirmacao-agendamento": {
        "prompt": "Você está auxiliando um cliente a confirmar um agendamento.\n\n**Dados do agendamento:**\n- Data: {{data}}\n- Horário: {{horario}}\n- Serviço: {{servico}}\n\nPor favor, confirme os dados acima com o cliente antes de finalizar.\nPergunte se está tudo correto e se deseja prosseguir.",
        "tags": ["action", "agendamento"],
    },
    "atendente/esclarecimento": {
        "prompt": "O cliente fez uma pergunta que precisa de esclarecimento.\n\n**Pergunta original:** {{pergunta}}\n\n**Possíveis interpretações:**\n{{opcoes}}\n\nPeça gentilmente ao cliente para especificar qual das opções ele deseja.",
        "tags": ["action", "esclarecimento"],
    },
    # RAG prompts (rag folder)
    "rag/query": {
        "prompt": "Você é um assistente da Vizu. Use os seguintes trechos de contexto para responder à pergunta.\nO contexto é soberano. Se você não sabe a resposta com base no contexto,\napenas diga que não sabe. Não tente inventar uma resposta.\n\nCONTEXTO:\n{{context}}\n\n---\n\nPERGUNTA:\n{{question}}\n\nRESPOSTA:",
        "tags": ["rag", "query"],
    },
    "rag/hybrid": {
        "prompt": "Você é um assistente da {{company_name}}. Use o contexto abaixo para responder.\n\n## CONTEXTO SEMÂNTICO (por relevância)\n{{semantic_context}}\n\n## CONTEXTO POR PALAVRAS-CHAVE\n{{keyword_context}}\n\n---\n\nPERGUNTA: {{question}}\n\nInstruções:\n1. Priorize informações que aparecem em ambos os contextos\n2. Se houver contradição, mencione ambas as versões\n3. Diga \"não sei\" se não encontrar resposta no contexto\n\nRESPOSTA:",
        "tags": ["rag", "hybrid"],
    },
    # Tool prompts (tool folder)
    "tool/sql-agent-prefix": {
        "prompt": "You are an expert SQL assistant. Your task is to answer questions about a database.\n\nIMPORTANT RULES:\n1. FIRST, always list the available tables using sql_db_list_tables\n2. THEN, get the schema of relevant tables using sql_db_schema\n3. THEN, write and execute your SQL query using sql_db_query\n4. ALWAYS execute queries to get real data - NEVER guess or make up numbers\n5. Return the EXACT results from the query\n\nAvailable tools:\n- sql_db_list_tables: Lists all tables in the database\n- sql_db_schema: Shows the schema of specified tables\n- sql_db_query: Executes a SQL SELECT query and returns results\n- sql_db_query_checker: Validates SQL syntax before execution\n\nNEVER make up data. ALWAYS run the query and report the actual results.",
        "tags": ["tool", "sql", "system"],
    },
    "tool/sql-agent-suffix": {
        "prompt": "Begin! Remember to ALWAYS execute queries to get real data.\n\nQuestion: {{input}}\n{{agent_scratchpad}}",
        "tags": ["tool", "sql"],
    },
    "tool/rag-query": {
        "prompt": "Você é um assistente da Vizu. Use os seguintes trechos de contexto para responder à pergunta.\nO contexto é soberano. Se você não sabe a resposta com base no contexto,\napenas diga que não sabe. Não tente inventar uma resposta.\n\nCONTEXTO:\n{{context}}\n\n---\n\nPERGUNTA:\n{{question}}\n\nRESPOSTA:",
        "tags": ["tool", "rag"],
    },
    # Elicitation prompts (elicitation folder)
    "elicitation/options": {
        "prompt": "{{question}}\n\nPor favor, escolha uma das opções abaixo:\n\n{{options_formatted}}\n\nDigite o número da opção desejada:",
        "tags": ["elicitation", "options"],
    },
    "elicitation/confirmation": {
        "prompt": "Você está prestes a realizar a seguinte ação:\n\n**{{action}}**\n\n{{details}}\n\nVocê confirma esta ação? (sim/não)",
        "tags": ["elicitation", "confirmation"],
    },
    "elicitation/freeform": {
        "prompt": "{{question}}\n\n{{hint}}\n\nPor favor, digite sua resposta:",
        "tags": ["elicitation", "freeform"],
    },
    # Error prompts (error folder)
    "error/tool-failed": {
        "prompt": "Desculpe, houve um problema ao executar uma operação.\n\nErro: {{error_message}}\n\nPor favor, tente novamente ou entre em contato com o suporte se o problema persistir.",
        "tags": ["error"],
    },
    "error/not-found": {
        "prompt": "Desculpe, não foi possível encontrar {{resource_type}}.\n\nPor favor, verifique se as informações estão corretas e tente novamente.",
        "tags": ["error"],
    },
}


def create_prompt(name: str, prompt: str, tags: list[str]) -> tuple[int, dict | str]:
    """Create a prompt in Langfuse."""
    url = f"{BASE_URL}/api/public/v2/prompts"
    payload = {
        "name": name,
        "prompt": prompt,
        "type": "text",
        "labels": ["production"],
        "tags": tags,
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    if resp.status_code < 300:
        return resp.status_code, resp.json()
    return resp.status_code, resp.text


def main():
    print("Creating Langfuse prompts matching templates.py...\n")

    success = 0
    failed = 0

    for name, config in PROMPTS.items():
        status, result = create_prompt(name, config["prompt"], config["tags"])

        if status in [200, 201]:
            print(f"✅ {name}")
            success += 1
        else:
            print(f"❌ {name}: {status}")
            if isinstance(result, str) and len(result) > 100:
                print(f"   {result[:100]}...")
            else:
                print(f"   {result}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Created: {success}, Failed: {failed}")
    print(f"\nView prompts at: https://us.cloud.langfuse.com/prompts")


if __name__ == "__main__":
    main()
