# Serviço: Atendente API

## 1. Propósito

O `atendente-api` é o microserviço central responsável por orquestrar a lógica de conversação do Atendente Virtual Inteligente da Vizu. Ele utiliza o framework LangGraph para gerenciar o estado da conversa e invocar ferramentas (`tools`) para interagir com sistemas externos, como bancos de dados de clientes, bases de conhecimento vetorial e APIs de agendamento.

Este serviço expõe uma API RESTful para receber mensagens (via webhooks, como do Twilio) e retorna as respostas geradas pela IA.

## 2. Como Executar Localmente

### Pré-requisitos

- Python 3.11+
- Poetry (gerenciador de dependências)
- Acesso a uma instância do Redis

### Passos para Instalação

1.  **Navegue até o diretório do serviço:**

    ```bash
    cd /path/to/vizu-mono/services/atendente_api
    ```

2.  **Instale as dependências:**
    O Poetry irá instalar as dependências locais (`libs`) e externas listadas no `pyproject.toml`.

    ```bash
    poetry install
    ```

3.  **Configure as Variáveis de Ambiente:**
    Copie o arquivo `.env.example` para `.env` e preencha com suas credenciais de desenvolvimento.

    ```bash
    cp .env.example .env
    ```

    **Arquivo `.env`:**

    ```env
    ENVIRONMENT="development"
    LANGCHAIN_API_KEY="sua_chave_langsmith_aqui"
    CLIENTS_API_URL="http://localhost:8001/api/v1" # Ou o serviço correspondente
    REDIS_HOST="localhost"
    REDIS_PORT="6379"
    ```

4.  **Execute a Aplicação:**
    Use o `uvicorn` para iniciar o servidor FastAPI.
    ```bash
    poetry run uvicorn src.atendente_api.main:app --reload
    ```
    A API estará disponível em `http://127.0.0.1:8000`.

## 3. Como Rodar os Testes

Os testes são fundamentais para garantir a qualidade e a estabilidade do serviço.

Para executar toda a suíte de testes (unitários e de integração), utilize o `pytest`:

```bash
# A partir do diretório services/atendente_api
poetry run pytest
```
