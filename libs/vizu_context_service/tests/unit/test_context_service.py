from unittest.mock import MagicMock
from uuid import UUID
from sqlalchemy.orm import Session

# Código que estamos testando
from vizu_context_service.context_service import ContextService
from vizu_context_service.redis_service import RedisService

# Modelos que usamos
from vizu_models.vizu_client_context import VizuClientContext


def test_get_client_context_cache_hit(
    mocker: MagicMock,
    mock_cliente_id: UUID,
    mock_vizu_client_context_dict: dict # O dict que vem do cache
):
    """
    Testa o 'caminho feliz' (Cache Hit).
    Garante que, se o cache do Redis retornar dados, o DB não é consultado.
    """
    # 1. Arrange (Organizar)
    # Mockamos as dependências de I/O
    mock_db = mocker.MagicMock(spec=Session)
    mock_redis = mocker.MagicMock(spec=RedisService)

    # Patchamos o módulo 'crud' que é importado pelo service
    mock_crud = mocker.patch("vizu_context_service.context_service.crud")

    # Configuramos o mock do Redis para retornar o dict do contexto
    cache_key = f"context:client:{mock_cliente_id}"
    mock_redis.get_json.return_value = mock_vizu_client_context_dict

    # Instanciamos o serviço REAL com dependências mockadas
    service = ContextService(db_session=mock_db, cache_service=mock_redis)

    # 2. Act (Agir)
    contexto = service.get_client_context_by_id(mock_cliente_id)

    # 3. Assert (Verificar)
    mock_redis.get_json.assert_called_once_with(cache_key)
    mock_crud.get_cliente_vizu_by_id.assert_not_called() # DB NÃO foi chamado
    assert isinstance(contexto, VizuClientContext)
    assert contexto.cliente_id == mock_cliente_id


def test_get_client_context_cache_miss(
    mocker: MagicMock,
    mock_cliente_id: UUID,
    mock_vizu_client_context: VizuClientContext # O modelo Pydantic
):
    """
    Testa o 'Caminho Feliz' (Cache Miss).
    Garante que o serviço busca no DB, retorna o contexto e armazena no cache.
    """
    # 1. Arrange
    mock_db = mocker.MagicMock(spec=Session)
    mock_redis = mocker.MagicMock(spec=RedisService)
    mock_crud = mocker.patch("vizu_context_service.context_service.crud")

    # Cache Miss: Redis retorna None
    mock_redis.get_json.return_value = None

    # DB Hit: O crud retorna um objeto que VizuClientContext.model_validate entende
    # (No código real, seria um modelo SQLAlchemy; aqui, mockamos o resultado
    # já como um dict para simplificar a validação do model_validate)
    mock_db_return = mock_vizu_client_context.model_dump()
    mock_crud.get_cliente_vizu_by_id.return_value = mock_db_return

    service = ContextService(db_session=mock_db, cache_service=mock_redis)
    cache_key = f"context:client:{mock_cliente_id}"

    # 2. Act
    contexto = service.get_client_context_by_id(mock_cliente_id)

    # 3. Assert
    mock_redis.get_json.assert_called_once_with(cache_key)
    mock_crud.get_cliente_vizu_by_id.assert_called_once_with(mock_db, mock_cliente_id)

    # Verifica se o serviço ARMAZENOU no cache
    mock_redis.set_json.assert_called_once_with(
        key=cache_key,
        data=contexto, # Deve ter chamado com o objeto Pydantic
        ttl_seconds=service.CACHE_TTL_SECONDS
    )
    assert contexto.cliente_id == mock_cliente_id


def test_get_client_context_not_found(mocker: MagicMock, mock_cliente_id: UUID):
    """
    Testa o caso em que o cliente não é encontrado nem no cache nem no DB.
    """
    # 1. Arrange
    mock_db = mocker.MagicMock(spec=Session)
    mock_redis = mocker.MagicMock(spec=RedisService)
    mock_crud = mocker.patch("vizu_context_service.context_service.crud")

    # Cache Miss
    mock_redis.get_json.return_value = None
    # DB Miss
    mock_crud.get_cliente_vizu_by_id.return_value = None

    service = ContextService(db_session=mock_db, cache_service=mock_redis)

    # 2. Act
    contexto = service.get_client_context_by_id(mock_cliente_id)

    # 3. Assert
    mock_redis.get_json.assert_called_once()
    mock_crud.get_cliente_vizu_by_id.assert_called_once()
    mock_redis.set_json.assert_not_called() # Não deve cachear 'None'
    assert contexto is None