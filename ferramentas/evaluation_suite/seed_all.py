# evaluation_suite/seed_all.py

import os
import requests
import json
from typing import List, Dict, Any

# URL base da sua API de Clientes (Clients API)
# Prioriza a variável de ambiente `BASE_URL` (útil quando o script roda dentro de um
# container). Quando rodando localmente contra o docker-compose use: localhost:8005
BASE_URL = os.getenv("BASE_URL", "http://localhost:8005/api/v1")

# =============================================================================
# == 1. DADOS DAS PERSONAS (CLIENTES)
# =============================================================================

# Dados das 5 personas (para POST /clientes)
PERSONAS_PARA_CRIACAO = [
    {
        "nome_empresa": "Oficina Mendes",
        "tipo_cliente": "EXTERNO",
        "tier": "SME"
    },
    {
        "nome_empresa": "Studio J",
        "tipo_cliente": "EXTERNO",
        "tier": "SME"
    },
    {
        "nome_empresa": "Casa com Alma",
        "tipo_cliente": "EXTERNO",
        "tier": "SME"
    },
    {
        "nome_empresa": "Consultório Odontológico Dra. Beatriz Almeida",
        "tipo_cliente": "EXTERNO",
        "tier": "SME"
    },
    {
        "nome_empresa": "Marcos Eletricista",
        "tipo_cliente": "EXTERNO",
        "tier": "SME"
    }
]

# =============================================================================
# == 2. DADOS DAS CONFIGURAÇÕES (CONTEXTO E PERMISSÕES)
# =============================================================================

# Configurações para as 5 personas
PERSONA_CONFIGS: Dict[str, Dict[str, Any]] = {
    "Oficina Mendes": {
        # RAG e SQL desabilitados para focar em agendamento (ferramenta que seria interna)
        "prompt_base": "Você é um atendente virtual da 'Oficina Mendes'. Seja direto, profissional e confiável, refletindo a reputação de honestidade construída por duas gerações. Seu objetivo é ajudar clientes a agendar serviços de mecânica geral (motor, freio, suspensão) para carros populares e fornecer cotações para serviços simples. Para diagnósticos complexos ou carros com muita eletrônica, encaminhe a conversa diretamente para o Ricardo. A prioridade é manter a confiança do cliente e a reputação da oficina.",
        "horario_funcionamento": {"seg-sex": "08:00-18:00", "sab": "08:00-12:00"},
        "ferramenta_rag_habilitada": False,
        "ferramenta_sql_habilitada": False
    },
    "Studio J": {
        # RAG e SQL desabilitados
        "prompt_base": "Você é o assistente virtual do 'Studio J', um salão de beleza moderno em Botafogo, especializado em cortes e técnicas de coloração. Sua personalidade deve ser criativa, amigável e conectada, como a da Juliana. Sua principal função é gerenciar a agenda, que é muito disputada e caótica via WhatsApp. Você deve automatizar a marcação de horários, consultar horários disponíveis e enviar lembretes, liberando o tempo da Juliana para que ela possa focar em seu trabalho artístico.",
        "horario_funcionamento": {"ter-sex": "10:00-20:00", "sab": "09:00-18:00"},
        "ferramenta_rag_habilitada": False,
        "ferramenta_sql_habilitada": False
    },
    "Casa com Alma": {
        # RAG Habilitado para testar o roteamento para a Tool Pool API
        "prompt_base": "Você é um consultor virtual da 'Casa com Alma', uma loja de decoração especializada em produtos artesanais e sustentáveis. Seu foco é o design de interiores. Sua comunicação é sofisticada, calma e muito focada em entender as necessidades de estilo do cliente. Use a base de conhecimento RAG para descrever produtos e materiais.",
        "horario_funcionamento": {"seg-sex": "09:00-17:00"},
        "ferramenta_rag_habilitada": True,
        "ferramenta_sql_habilitada": False
    },
    "Consultório Odontológico Dra. Beatriz Almeida": {
        # SQL Habilitado para testar o roteamento para a Tool Pool API
        "prompt_base": "Você é a secretária virtual do 'Consultório Dra. Beatriz Almeida'. Sua comunicação é empática, informativa e muito profissional. Sua principal função é responder dúvidas sobre tratamentos e horários, e verificar o status financeiro dos pacientes (para isso, use o Agente SQL).",
        "horario_funcionamento": {"seg-sex": "08:30-18:30"},
        "ferramenta_rag_habilitada": False,
        "ferramenta_sql_habilitada": True
    },
    "Marcos Eletricista": {
        # Ambos Habilitados para teste de prioridade do LLM
        "prompt_base": "Você é o assistente técnico de Marcos Eletricista. Sua comunicação é prática, direta e focada em solução de problemas elétricos residenciais. Use todas as ferramentas disponíveis para orçamentos (SQL) ou para consultas técnicas (RAG).",
        "horario_funcionamento": {"seg-dom": "08:00-22:00"},
        "ferramenta_rag_habilitada": True,
        "ferramenta_sql_habilitada": True
    }
}


# =============================================================================
# == 3. LÓGICA DE POPULAÇÃO UNIFICADA
# =============================================================================

def populate_all():
    """
    Cria os clientes e suas configurações em uma única passagem.
    """
    headers = {"Content-Type": "application/json"}
    api_keys_map = {}

    print("--- INICIANDO POPULAÇÃO DE CLIENTES E CONFIGURAÇÕES ---\n")

    for persona_data in PERSONAS_PARA_CRIACAO:
        company_name = persona_data["nome_empresa"]
        print(f"\n[*] Processando cliente: {company_name}...")

        # CORREÇÃO I: Inicializa client_id e flag de sucesso antes do bloco try
        client_id = None
        client_creation_succeeded = False

        # --- A. CRIAR CLIENTE E OBTER CHAVES (POST /clientes) ---
        try:
            print(f"  [1/2] Criando cliente base...")
            # Use `json=` para enviar JSON corretamente e deixe requests setar headers
            response = requests.post(
                f"{BASE_URL}/clientes",
                json=persona_data,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            created_client = response.json()
            client_id = created_client.get("id")
            api_key = created_client.get("api_key")

            if not client_id or not api_key:
                raise ValueError("Resposta da API de Clientes incompleta (ID ou API Key ausente).")

            api_keys_map[company_name] = api_key
            print(f"      ID: {client_id}")
            print(f"      API Key: {api_key}")
            client_creation_succeeded = True  # Sucesso!

        except requests.exceptions.RequestException as e:
            print("\n--- ERRO DO SERVIDOR ENCONTRADO ---")

            # CORREÇÃO II: Melhora a leitura do status code e corpo da resposta
            status_code = e.response.status_code if e.response is not None else "N/A"
            response_text = e.response.text if e.response is not None else str(e)

            print("Status Code:", status_code)
            print("Corpo da Resposta (NÃO JSON):", response_text)
            print("------------------------------------\n")

            error_details = 'Resposta não é JSON. Veja o corpo da resposta acima.'
            # Tente ler o detalhe apenas se o conteúdo for JSON (opcional)
            try:
                if e.response is not None:
                    try:
                        error_details = e.response.json().get('detail', e.response.text)
                    except ValueError:
                        error_details = e.response.text
            except Exception:
                pass

            print(f"  [!] ERRO FATAL na criação do cliente '{company_name}': {error_details}")

        # --- B. CONFIGURAR CLIENTE (POST /configuracoes) ---
        # CORREÇÃO III: Só prossegue para a configuração se a criação do cliente foi um sucesso
        if client_creation_succeeded and company_name in PERSONA_CONFIGS:
            config_data = PERSONA_CONFIGS[company_name].copy()
            config_data["cliente_vizu_id"] = client_id

            try:
                print(f"  [2/2] Enviando configuração de contexto...")
                resp_config = requests.post(
                    f"{BASE_URL}/configuracoes",
                    json=config_data,
                    headers=headers,
                    timeout=10,
                )

                resp_config.raise_for_status()
                print(f"  [+] SUCESSO! Configuração criada e associada ao cliente.")

            except requests.exceptions.RequestException as e:
                body = None
                try:
                    body = e.response.json()
                except Exception:
                    body = getattr(e.response, 'text', str(e))
                print(f"  [!] ERRO FATAL na configuração: status={getattr(e.response,'status_code', 'N/A')} body={body}")
        elif not client_creation_succeeded:
             print(f"  [!] CONFIGURAÇÃO PULADA: Criação do cliente '{company_name}' falhou. Configuração ignorada.")
        else:
            print(f"  [!] AVISO: Nenhuma configuração definida para '{company_name}'.")

    # --- RESULTADO FINAL ---
    print("\n\n=================================================")
    print("=== POPULAÇÃO FINALIZADA: CHAVES PARA TESTE ===")
    print("=================================================")
    for name, key in api_keys_map.items():
        print(f"| {name:<40} | Key: {key}")
    print("=================================================\n")

if __name__ == "__main__":
    populate_all()