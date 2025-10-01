import uuid
from datetime import datetime
import pytest
from pydantic import ValidationError

from vizu_shared_models.cliente_vizu import ClienteVizuCreate, TierCliente, TipoCliente
from vizu_shared_models.configuracao import ConfiguracaoNegocioCreate
from vizu_shared_models.cliente_final import ClienteFinalCreate
from vizu_shared_models.conversa import ConversaCreate, MensagemCreate, Remetente

# --- Testes para ClienteVizu ---

def test_criar_clientevizu_com_sucesso():
    """Verifica a criação bem-sucedida de um ClienteVizu."""
    data = {
        "nome_empresa": "Empresa Teste LTDA",
        "tipo_cliente": TipoCliente.EXTERNO,
        "tier": TierCliente.SME
    }
    cliente = ClienteVizuCreate(**data)
    assert cliente.nome_empresa == data["nome_empresa"]
    assert cliente.tipo_cliente == data["tipo_cliente"]
    assert cliente.tier == data["tier"]

def test_criar_clientevizu_com_tier_invalido():
    """Verifica que um tier inválido levanta um ValidationError."""
    with pytest.raises(ValidationError):
        ClienteVizuCreate(
            nome_empresa="Empresa Invalida",
            tipo_cliente="externo",
            tier="nao_existe"  # Valor inválido
        )

# --- Testes para ConfiguracaoNegocio ---

def test_criar_configuracao_negocio_com_sucesso():
    """Verifica a criação bem-sucedida de uma configuração."""
    cliente_id = uuid.uuid4()
    config = ConfiguracaoNegocioCreate(
        cliente_vizu_id=cliente_id,
        prompt_base="Seja um assistente prestativo.",
        ferramenta_rag_habilitada=True
    )
    assert config.cliente_vizu_id == cliente_id
    assert config.ferramenta_rag_habilitada is True
    assert config.horario_funcionamento is None

# --- Testes para ClienteFinal ---

def test_criar_cliente_final_com_sucesso():
    """Verifica a criação bem-sucedida de um cliente final."""
    cliente_vizu_id = uuid.uuid4()
    data = {
        "id_externo": "5511999998888",
        "nome": "João da Silva",
        "metadados": {"cidade": "São Paulo"},
        "cliente_vizu_id": cliente_vizu_id
    }
    cliente_final = ClienteFinalCreate(**data)
    assert cliente_final.id_externo == data["id_externo"]
    assert cliente_final.cliente_vizu_id == cliente_vizu_id
    assert cliente_final.metadados["cidade"] == "São Paulo"

def test_criar_cliente_final_sem_id_externo():
    """Verifica que a ausência do campo obrigatório 'id_externo' falha."""
    with pytest.raises(ValidationError):
        ClienteFinalCreate(
            nome="Maria",
            cliente_vizu_id=uuid.uuid4()
        )

# --- Testes para Conversa e Mensagem ---

def test_criar_conversa_com_sucesso():
    """Verifica a criação bem-sucedida de uma conversa."""
    conversa = ConversaCreate(cliente_final_id=123)
    assert conversa.cliente_final_id == 123
    # Verifica se o timestamp foi criado por padrão
    assert isinstance(conversa.timestamp_inicio, datetime)

def test_criar_mensagem_com_sucesso():
    """Verifica a criação bem-sucedida de uma mensagem."""
    conversa_id = uuid.uuid4()
    mensagem = MensagemCreate(
        conversa_id=conversa_id,
        remetente=Remetente.USER,
        conteudo="Olá, tudo bem?"
    )
    assert mensagem.conversa_id == conversa_id
    assert mensagem.remetente == Remetente.USER
    assert mensagem.conteudo == "Olá, tudo bem?"

def test_criar_mensagem_remetente_invalido():
    """Verifica que um remetente inválido levanta um ValidationError."""
    with pytest.raises(ValidationError):
        MensagemCreate(
            conversa_id=uuid.uuid4(),
            remetente="INVALIDO", # Valor inválido
            conteudo="Teste"
        )