# src/atendente_api/api/routes.py

from fastapi import APIRouter, Depends, Request, Response, HTTPException, Header
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator

# Importações dos nossos módulos
from atendente_api.core.config import get_settings, Settings
from vizu_db_connector.core import get_db
from atendente_api.services.context_service import ContextService
from atendente_api.services.redis_service import get_redis_service, RedisService
from atendente_api.core.graph import create_agent_graph

# --- CORREÇÃO FINAL: Dependência para o Validador do Twilio ---
def get_twilio_validator(settings: Settings = Depends(get_settings)) -> RequestValidator:
    """
    Dependência que cria e fornece o validador do Twilio.
    Isso garante que get_settings() só seja chamado quando a validação for necessária.
    """
    return RequestValidator(settings.TWILIO_AUTH_TOKEN)

async def validate_twilio_request(
    request: Request,
    validator: RequestValidator = Depends(get_twilio_validator),
    x_twilio_signature: str = Header(None)
):
    """
    Valida a requisição do Twilio usando o validador injetado.
    """
    if not x_twilio_signature:
        raise HTTPException(status_code=403, detail="Requisição sem assinatura do Twilio.")
    try:
        form_data = await request.form()
        url = str(request.url)
        params = dict(form_data)
        if not validator.validate(url, params, x_twilio_signature):
            raise HTTPException(status_code=403, detail="Assinatura do Twilio inválida.")
        return params
    except Exception:
        raise HTTPException(status_code=403, detail="Falha ao validar a requisição do Twilio.")

# --- Rota Principal da API ---

router = APIRouter()
agent_graph = create_agent_graph()

@router.post("/incoming", dependencies=[Depends(validate_twilio_request)])
async def handle_incoming_message(
    request: Request,
    db: Session = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
    settings: Settings = Depends(get_settings)
):
    validated_data = await request.form()
    api_key = request.headers.get("X-Vizu-API-Key")
    from_number = validated_data.get("From")
    message_body = validated_data.get("Body")

    if not api_key:
        raise HTTPException(status_code=401, detail="X-Vizu-API-Key header ausente.")

    context_service = ContextService(db, redis_service)
    client_context = context_service.get_client_context(api_key)

    if not client_context:
        raise HTTPException(status_code=403, detail="Cliente não encontrado ou inativo.")

    thread_id = f"whatsapp:{from_number}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {"contexto_cliente": client_context}

    final_state = agent_graph.invoke(
        {"messages": ("human", message_body), **initial_state},
        config=config,
    )

    ai_response = final_state["messages"][-1].content
    twiml_response = f'<Response><Message>{ai_response}</Message></Response>'
    return Response(content=twiml_response, media_type="application/xml")