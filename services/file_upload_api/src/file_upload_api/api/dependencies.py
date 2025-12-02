import uuid
import logging
# from fastapi.security import APIKeyHeader # Exemplo de como seria a auth real

logger = logging.getLogger(__name__)

# --- Padrão Vizu: Stub de Autenticação para Desenvolvimento ---
# TODO: Implementar lógica de autenticação real (ex: API Key via BD/Secrets).
# Por enquanto, usamos um valor estático para desenvolvimento e teste,
# assim como modelado na 'clientes_finais_api'.

# Exemplo de como seria o header:
# api_key_header = APIKeyHeader(name="X-VIZU-API-KEY", auto_error=False)

# Um ID estático para simular um cliente autenticado.
DUMMY_CLIENTE_VIZU_ID = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")

def get_cliente_vizu_id_from_token() -> uuid.UUID:
    """
    Dependência de Autenticação (Stub/Placeholder).

    Em um ambiente de produção, esta função faria:
    1. Receberia o token (ex: key: str = Depends(api_key_header)).
    2. Validaria o token (consultando o BD ou um serviço de auth).
    3. Retornaria o 'cliente_vizu_id' associado.
    4. Lançaria um HTTPException 401/403 se o token fosse inválido.

    Para fins de desenvolvimento (e para os testes de unidade),
    retornamos um ID estático.
    """
    logger.warning(
        f"AUTENTICAÇÃO STUB: Usando DUMMY_CLIENTE_VIZU_ID: {DUMMY_CLIENTE_VIZU_ID}"
    )

    # --- Exemplo de Lógica Real (Comentada) ---
    # if not key:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Missing API Key"
    #     )
    #
    # db_cliente = auth_service.get_cliente_by_api_key(key) # Lógica de BD
    # if not db_cliente:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Invalid API Key"
    #     )
    # return db_cliente.id
    # ----------------------------------------------

    return DUMMY_CLIENTE_VIZU_ID