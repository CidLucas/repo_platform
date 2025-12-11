import logging

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

# Auth wrapper
from atendente_core.api.auth import get_auth_result

# --- 2. IMPORTS LOCAIS ---
from atendente_core.api.schemas import (
    ChatRequest,
    ChatResponse,
    ClientContextResponse,
    ElicitationOption,
    # Re-exported from vizu_models
    ElicitationRequest,
    ElicitationType,
    ModelsResponse,
    ToolInfo,
)
from atendente_core.core.nodes import filter_tools_for_client
from atendente_core.core.service import AtendenteService
from atendente_core.services.mcp_client import mcp_manager
from vizu_auth.core.models import AuthResult
from vizu_context_service.context_service import ContextService

# --- 1. INTEGRAÇÃO COM LIB COMPARTILHADA (O Segredo da Limpeza) ---
# Em vez de criar conexões Redis/DB aqui, importamos a dependência pronta.
# Isso garante que todos os microserviços usem a mesma lógica de conexão.
from vizu_context_service.dependencies import get_context_service, get_redis_service
from vizu_context_service.redis_service import RedisService

# DB helpers
from vizu_db_connector.database import get_db_session

# Importa ModelInfo diretamente de vizu_models (para /models endpoint)
from vizu_models import ClienteVizu, ModelInfo

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level agent_graph placeholder so tests can patch it.
agent_graph = None


# --- 3. INJEÇÃO DE DEPENDÊNCIA DO SERVIÇO ---
def get_atendente_service(
    # AQUI ESTÁ A MÁGICA:
    # O FastAPI resolve 'get_context_service', que por sua vez resolve
    # 'get_redis_client' e 'get_db_session' automaticamente.
    context_service: ContextService = Depends(get_context_service),
) -> AtendenteService:
    """
    Fábrica que entrega o AtendenteService pronto para uso,
    com banco e cache já conectados.
    """
    return AtendenteService(context_service)


# Dependency used to validate incoming Twilio webhook requests.
# Tests import and override this dependency, so keep it lightweight.
def validate_twilio_request(signature: str | None = Header(None)):
    """
    Default Twilio request validator placeholder.
    In production this should validate the X-Twilio-Signature header.
    Tests will override this dependency.
    """
    return None


# Incoming endpoint used by integration tests (WhatsApp-like webhook)
@router.post("/api/v1/incoming")
async def incoming(
    From: str = Form(...),
    Body: str = Form(...),
    api_key: str | None = Header(None, alias="X-Vizu-API-Key"),
    db: Session = Depends(get_db_session),
    cache: RedisService = Depends(get_redis_service),
    _validate=Depends(validate_twilio_request),
):
    # Basic authorization
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    statement = select(ClienteVizu).where(ClienteVizu.api_key == api_key)
    cliente = db.execute(statement).scalars().first()
    if not cliente:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Populate cache (TTL 24h)
    redis_key = f"context:client:{api_key}"
    cache.set_json(redis_key, {"cliente": cliente.nome_empresa}, ttl_seconds=86400)

    # Invoke the agent graph (tests patch `atendente_core.api.router.agent_graph`)
    current_graph = agent_graph
    if current_graph is None:
        # Fallback lightweight response when no graph is available
        return Response(content=f"Olá {cliente.nome_empresa}", media_type="text/plain")

    result = current_graph.invoke(input=Body, cliente=cliente)
    messages = result.get("messages", [])
    texts = [getattr(m, "content", str(m)) for m in messages]
    return Response(content="\n".join(texts), media_type="text/plain")


# ============================================================================
# ENDPOINT 1: CHAT JSON (Para Testes Locais, Frontend e Curl)
# ============================================================================
@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    # Header alternativo para especificar modelo
    x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
    # Substitui o header direto por uma dependency que valida JWT ou API-Key
    auth_result: AuthResult = Depends(get_auth_result),
    service: AtendenteService = Depends(get_atendente_service),
):
    """
    Endpoint principal de chat.

    O modelo LLM pode ser especificado de 3 formas (em ordem de prioridade):
    1. Campo `model` no body JSON
    2. Header `X-LLM-Model`
    3. Modelo padrão do provider configurado

    ## PHASE 3: Elicitation (Human-in-the-Loop)

    Quando o agente precisa de confirmação ou input do usuário, a resposta
    incluirá `elicitation_pending` com detalhes sobre o que é necessário.

    Para responder a uma elicitation:
    1. Envie novo request com o mesmo `session_id`
    2. Inclua `elicitation_response` com `elicitation_id` e `response`

    Exemplo:
    ```json
    {
        "message": "sim",
        "session_id": "123",
        "elicitation_response": {
            "elicitation_id": "abc-123",
            "response": true
        }
    }
    ```

    Exemplos de modelos disponíveis no Ollama Cloud:
    - gpt-oss:20b (rápido, 20B parâmetros)
    - gpt-oss:120b (poderoso, 120B parâmetros)
    - deepseek-v3.1:671b (muito poderoso, 671B parâmetros)
    - qwen3-coder:480b (especializado em código)
    """
    try:
        # Determina o modelo a usar (body tem prioridade sobre header)
        model_override = body.model or x_llm_model

        # Prepara resposta de elicitation se fornecida
        elicitation_response = None
        if body.elicitation_response:
            elicitation_response = {
                "elicitation_id": body.elicitation_response.elicitation_id,
                "response": body.elicitation_response.response,
            }

        # Chama a lógica de negócio pura (sem saber se veio de HTTP ou Twilio)
        result = await service.process_message(
            api_key=None,
            session_id=body.session_id,
            message_text=body.message,
            cliente_vizu_id=auth_result.cliente_vizu_id,
            model_override=model_override,
            elicitation_response=elicitation_response,
        )

        # PHASE 3: Convert pending_elicitation to API schema
        pending_elicitation = None
        if result.pending_elicitation:
            pe = result.pending_elicitation
            options = None
            if pe.get("options"):
                options = [
                    ElicitationOption(
                        value=opt["value"],
                        label=opt["label"],
                        description=opt.get("description"),
                    )
                    for opt in pe["options"]
                ]

            pending_elicitation = ElicitationRequest(
                elicitation_id=pe["elicitation_id"],
                type=ElicitationType(pe["type"]),
                message=pe["message"],
                options=options,
                metadata=pe.get("metadata"),
            )

        return ChatResponse(
            response=result.response,
            session_id=body.session_id,
            model_used=result.model_used,
            elicitation_pending=pending_elicitation,
        )

    except ValueError as e:
        # Erros de negócio (ex: Cliente não encontrado) -> 401
        logger.warning(f"Erro de validação no /chat: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        # Erros inesperados -> 500
        logger.error(f"Erro interno no /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno no processamento.")


# ============================================================================
# ENDPOINT 2: WEBHOOK TWILIO (Para WhatsApp)
# ============================================================================
@router.post("/webhook/twilio")
async def twilio_webhook(
    # O Twilio envia os dados como FORM DATA (application/x-www-form-urlencoded)
    From: str = Form(...),
    Body: str = Form(...),
    # Em produção, precisaremos de uma estratégia para mapear o número 'To'
    # para uma API Key ou Cliente ID. Por enquanto, deixamos preparado.
    service: AtendenteService = Depends(get_atendente_service),
):
    try:
        logger.info(f"Recebido Webhook Twilio de {From}: {Body}")

        # TODO: Recuperar API KEY do cliente baseada no número de destino (To)
        # api_key = await service.get_api_key_from_phone(...)

        # Mock temporário para resposta (pois não temos a API Key no header do Twilio)
        response_text = "Olá! O webhook foi recebido, mas a identificação do cliente via WhatsApp ainda está sendo configurada."

        # Resposta em XML TwiML (exigido pelo Twilio)
        twiml = MessagingResponse()
        twiml.message(response_text)

        return Response(content=str(twiml), media_type="application/xml")

    except Exception as e:
        logger.error(f"Erro no webhook Twilio: {e}", exc_info=True)
        # Mesmo em erro, o Twilio espera XML válido para não retentar infinitamente
        return Response(content=str(MessagingResponse()), media_type="application/xml")


# ============================================================================
# ENDPOINT 3: LISTAR MODELOS DISPONÍVEIS
# ============================================================================
@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """
    Lista os modelos LLM disponíveis para uso.

    Retorna modelos do provider atualmente configurado (LLM_PROVIDER)
    e os tiers disponíveis (fast, default, powerful).

    Use o nome do modelo no campo `model` do /chat ou no header X-LLM-Model.
    """
    from vizu_llm_service import (
        MODEL_MAPPINGS,
        LLMProvider,
        ModelTier,
        get_llm_settings,
    )

    settings = get_llm_settings()
    current_provider = LLMProvider(settings.LLM_PROVIDER)

    models = []

    # Modelos do provider atual por tier
    provider_models = MODEL_MAPPINGS.get(current_provider, {})
    for tier, model_name in provider_models.items():
        models.append(
            ModelInfo(
                name=model_name,
                provider=current_provider.value,
                tier=tier.value,
                description=f"Modelo {tier.value} do provider {current_provider.value}",
            )
        )

    # Se for Ollama Cloud, adiciona modelos específicos do cloud
    if current_provider == LLMProvider.OLLAMA_CLOUD:
        cloud_models = [
            ("gpt-oss:20b", "Modelo rápido com 20B parâmetros, bom para testes"),
            ("gpt-oss:120b", "Modelo poderoso com 120B parâmetros"),
            ("deepseek-v3.1:671b", "DeepSeek V3.1 com 671B parâmetros - muito capaz"),
            ("qwen3-coder:480b", "Qwen3 especializado em código - 480B parâmetros"),
            ("cogito-2.1:671b", "Cogito 2.1 - raciocínio avançado"),
            ("kimi-k2:1t", "Kimi K2 - 1 trilhão de parâmetros"),
        ]
        for name, desc in cloud_models:
            if not any(m.name == name for m in models):
                models.append(
                    ModelInfo(
                        name=name,
                        provider="ollama_cloud",
                        tier="cloud",
                        description=desc,
                    )
                )

    default_model = provider_models.get(ModelTier.DEFAULT, "unknown")

    return ModelsResponse(
        models=models,
        current_provider=current_provider.value,
        default_model=default_model,
    )


# ============================================================================
# ENDPOINT 4: CONTEXTO DO CLIENTE (PHASE 2 - Dynamic Personalized Context)
# ============================================================================
@router.get("/context", response_model=ClientContextResponse)
async def get_client_context(
    auth_result: AuthResult = Depends(get_auth_result),
    context_service: ContextService = Depends(get_context_service),
):
    """
    Retorna o contexto do cliente autenticado.

    Mostra quais ferramentas estão habilitadas, configurações de negócio
    e outras informações de contexto (apenas dados seguros).

    Útil para:
    - Debug: verificar se um cliente tem RAG/SQL habilitado
    - Frontend: mostrar features disponíveis
    - Testes: validar configuração do cliente
    """
    from uuid import UUID

    from vizu_models.safe_client_context import InternalClientContext

    # Obtém o contexto completo do cliente
    try:
        uuid_obj = UUID(str(auth_result.cliente_vizu_id))
        client_context = await context_service.get_client_context_by_id(uuid_obj)
    except Exception as e:
        logger.error(f"Erro ao obter contexto do cliente: {e}")
        raise HTTPException(
            status_code=500, detail="Erro ao carregar contexto do cliente"
        )

    if not client_context:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Separa contexto seguro
    internal_ctx = InternalClientContext.from_vizu_client_context(client_context)
    safe_ctx = internal_ctx.get_safe_context()

    # Obtém todas as tools do MCP e filtra
    all_tools = mcp_manager.tools or []
    filtered_tools = filter_tools_for_client(all_tools, safe_ctx)

    # Monta lista de tools com status
    available_tools = []
    for tool in all_tools:
        is_enabled = any(t.name == tool.name for t in filtered_tools)
        available_tools.append(
            ToolInfo(name=tool.name, description=tool.description, enabled=is_enabled)
        )

    return ClientContextResponse(
        nome_empresa=safe_ctx.nome_empresa,
        ferramenta_rag_habilitada=safe_ctx.ferramenta_rag_habilitada,
        ferramenta_sql_habilitada=safe_ctx.ferramenta_sql_habilitada,
        collection_rag=safe_ctx.collection_rag,
        available_tools=available_tools,
        horario_funcionamento=safe_ctx.horario_funcionamento,
        has_custom_prompt=bool(safe_ctx.prompt_base),
    )
