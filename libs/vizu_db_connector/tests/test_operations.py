from sqlalchemy.orm import Session
from vizu_db_connector.models.cliente_vizu import ClienteVizu
from vizu_shared_models.cliente_vizu import TipoCliente, TierCliente

def test_create_cliente_vizu(db_session: Session):
    """
    Testa a criação de uma nova entrada na tabela ClienteVizu.

    Args:
        db_session: A fixture do pytest que fornece uma sessão de DB.
    """
    # 1. Cria uma instância do modelo SQLAlchemy
    novo_cliente = ClienteVizu(
        nome_empresa="Cliente Teste SA",
        tipo_cliente=TipoCliente.EXTERNO,
        tier=TierCliente.ENTERPRISE
    )

    # 2. Adiciona à sessão e commita (dentro da transação do teste)
    db_session.add(novo_cliente)
    db_session.commit()
    db_session.refresh(novo_cliente)

    # 3. Busca o cliente no banco de dados para verificar
    cliente_do_banco = db_session.query(ClienteVizu).filter_by(nome_empresa="Cliente Teste SA").one()

    # 4. Asserts: Verifica se os dados foram salvos corretamente
    assert cliente_do_banco is not None
    assert cliente_do_banco.nome_empresa == "Cliente Teste SA"
    assert cliente_do_banco.tier == TierCliente.ENTERPRISE
    assert cliente_do_banco.id is not None
    assert cliente_do_banco.api_key is not None