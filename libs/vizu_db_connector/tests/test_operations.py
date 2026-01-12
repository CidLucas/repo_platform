from sqlalchemy.orm import Session

from vizu_models import ClienteVizu, FonteDeDados, TipoFonte
from vizu_models.cliente_vizu import TierCliente, TipoCliente


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
        tier=TierCliente.ENTERPRISE,
    )

    # 2. Adiciona à sessão e commita (dentro da transação do teste)
    db_session.add(novo_cliente)
    db_session.commit()
    db_session.refresh(novo_cliente)

    # 3. Busca o cliente no banco de dados para verificar
    cliente_do_banco = (
        db_session.query(ClienteVizu).filter_by(nome_empresa="Cliente Teste SA").one()
    )

    # 4. Asserts: Verifica se os dados foram salvos corretamente
    assert cliente_do_banco is not None
    assert cliente_do_banco.nome_empresa == "Cliente Teste SA"
    assert cliente_do_banco.tier == TierCliente.ENTERPRISE
    assert cliente_do_banco.id is not None
    assert cliente_do_banco.api_key is not None

    def test_create_fonte_de_dados_for_cliente(db_session: Session):
        """
        Testa a criação de uma FonteDeDados e seu relacionamento com ClienteVizu.
        """

    # 1. Setup: Criar um cliente "pai" primeiro
    cliente_pai = ClienteVizu(
        nome_empresa="Empresa Fonte de Dados",
        tipo_cliente=TipoCliente.EXTERNO,
        tier=TierCliente.SME,
    )
    db_session.add(cliente_pai)
    db_session.commit()
    db_session.refresh(cliente_pai)

    # 2. Criação: Criar a FonteDeDados associada ao cliente
    nova_fonte = FonteDeDados(
        client_id=cliente_pai.id,
        tipo_fonte=TipoFonte.URL,
        caminho="https://vizu.ai/docs",
    )
    db_session.add(nova_fonte)
    db_session.commit()
    db_session.refresh(nova_fonte)

    # 3. Asserts: Verificar os dados da fonte
    assert nova_fonte.id is not None
    assert nova_fonte.tipo_fonte == TipoFonte.URL
    assert nova_fonte.client_id == cliente_pai.id

    # 4. Verificar o relacionamento a partir do cliente
    #    Recarregar o cliente da sessão para ver as mudanças do relacionamento
    db_session.refresh(cliente_pai)
    assert len(cliente_pai.fontes_de_dados) == 1
    assert cliente_pai.fontes_de_dados[0].caminho == "https://vizu.ai/docs"
