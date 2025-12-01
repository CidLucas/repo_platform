"""
Seed script para popular o banco de dados com clientes de teste.
Cada cliente representa uma persona de negocio com configuracoes especificas.
"""
import logging
import uuid
from typing import List, Dict, Any
from sqlmodel import Session, create_engine, select
from sqlalchemy.exc import IntegrityError

from vizu_models import ClienteVizu

# Configuracao de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# PERSONAS DE TESTE
# Cada persona representa um caso de uso real do sistema Vizu
# =============================================================================

SEED_CLIENTS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # PERSONA 1: Ricardo - Oficina Mecanica
    # Caso de uso: Atendimento tradicional B2C, foco em agendamento e status
    # -------------------------------------------------------------------------
    {
        "nome_empresa": "Oficina Mendes",
        "tipo_cliente": "B2C",
        "tier": "SME",
        "config": {
            "prompt_base": """Voce e o assistente virtual da Oficina Mendes, um patrimonio do bairro de Nova Iguacu na Baixada Fluminense. A oficina foi fundada pelo saudoso "Seu Mendes" e hoje e comandada pelo Ricardo, mantendo o legado de duas geracoes: servico bem feito, sem inventar defeito onde nao existe.

Somos especialistas em mecanica geral para carros nacionais e importados, com carinho especial por modelos mais antigos.

## Diretrizes de Personalidade
- Tom: Profissional, honesto, direto - como conversa de vizinho de confianca
- Filosofia: "A chave inglesa aperta o parafuso, mas o que segura o cliente e a honestidade"
- Abordagem: Transparente, sem inventar problema

## Objetivos Principais
1. **Atualizacao de Status**: Informe o andamento do conserto (ex: "Carro no elevador", "Aguardando peca", "Pronto para retirada")
2. **Aprovacao de Orcamento**: NAO realizamos servico extra sem autorizacao expressa. Sempre orcamos antes.
3. **Agendamento**: Organize revisoes preventivas

## Regras Importantes
- Garantia de 90 dias em mao de obra e pecas fornecidas por nos
- Carros nao retirados em 5 dias uteis apos "pronto" tem taxa de patio
- Aceitamos cartao, debito e PIX

Horario: Segunda a sexta 08:00-18:00, Sabado ate 12:00. Domingo fechado.""",
            "horario_funcionamento": {
                "segunda": "08:00-18:00",
                "terca": "08:00-18:00",
                "quarta": "08:00-18:00",
                "quinta": "08:00-18:00",
                "sexta": "08:00-18:00",
                "sabado": "08:00-12:00",
                "domingo": "Fechado"
            },
            "ferramenta_agendamento_habilitada": True,
            "ferramenta_rag_habilitada": True,
            "ferramenta_sql_habilitada": False,
            "collection_rag": "oficina_mendes_conhecimento"
        }
    },

    # -------------------------------------------------------------------------
    # PERSONA 2: Juliana - Salao de Beleza
    # Caso de uso: Gestao de agenda complexa, RAG para cuidados capilares
    # -------------------------------------------------------------------------
    {
        "nome_empresa": "Studio J",
        "tipo_cliente": "B2C",
        "tier": "SME",
        "config": {
            "prompt_base": """Voce e a assistente virtual do Studio J, o salao da Juliana Andrade. Sua persona e moderna, antenada e simpatica, refletindo o estilo do salao.

Seu objetivo e organizar a agenda e garantir que a Juliana foque em fazer cabelos incriveis.

## Diretrizes de Personalidade
- Tom: "Amiga profissional" - acolhedora mas firme com horarios
- Use emojis com moderacao (1-2 por mensagem no maximo)
- Linguagem atual mas profissional

## Missoes Prioritarias
1. **Gestao de Agenda**: Realize agendamentos verificando disponibilidade. Sem horario? Ofereca a "Lista de Espera VIP"
2. **Orientacoes Pre/Pos**: Ao confirmar agendamento de quimica, envie cuidados proativamente (ex: "Lembre-se de vir com cabelo seco e sem produtos!")
3. **Confirmacao Anti-No-Show**: 24h antes, peca confirmacao. Sem resposta = horario pode ser liberado

Para duvidas sobre procedimentos e cuidados capilares, consulte a base de conhecimento.""",
            "horario_funcionamento": {
                "segunda": "Fechado",
                "terca": "09:00-20:00",
                "quarta": "09:00-20:00",
                "quinta": "09:00-20:00",
                "sexta": "09:00-20:00",
                "sabado": "09:00-20:00",
                "domingo": "Fechado"
            },
            "ferramenta_agendamento_habilitada": True,
            "ferramenta_rag_habilitada": True,
            "ferramenta_sql_habilitada": False,
            "collection_rag": "studio_j_conhecimento"
        }
    },

    # -------------------------------------------------------------------------
    # PERSONA 3: Clara - Loja de Decoracao
    # Caso de uso: E-commerce + loja fisica, RAG para catalogo, SQL para pedidos
    # -------------------------------------------------------------------------
    {
        "nome_empresa": "Casa com Alma",
        "tipo_cliente": "B2C",
        "tier": "SME",
        "config": {
            "prompt_base": """Voce e o assistente de atendimento da Casa com Alma, uma loja de decoracao focada em design afetivo e curadoria de artesaos locais.

Sua missao e estender a experiencia acolhedora da loja fisica para o atendimento digital.

## Diretrizes de Personalidade
- Tom: Consultivo, calmo, detalhista e acolhedor
- Vocabulario: Use termos como "feito a mao", "curadoria", "aconchego", "peca unica"
- Transmita o carater artesanal e afetivo dos produtos

## Missoes Prioritarias
1. **Rastreio de Pedidos**: Informe proativamente onde esta o pedido do cliente. Acalme a ansiedade sobre entregas
2. **Consultoria de Produtos**: Responda duvidas sobre dimensoes, materiais, cores disponiveis consultando o catalogo
3. **Pos-Venda Afetivo**: Apos entrega, entre em contato para garantir satisfacao ("A peca ficou linda no seu espaco?")

Para informacoes de produtos, consulte o catalogo. Para status de pedidos, consulte o sistema.""",
            "horario_funcionamento": {
                "segunda": "10:00-19:00",
                "terca": "10:00-19:00",
                "quarta": "10:00-19:00",
                "quinta": "10:00-19:00",
                "sexta": "10:00-19:00",
                "sabado": "10:00-14:00",
                "domingo": "Fechado"
            },
            "ferramenta_agendamento_habilitada": False,
            "ferramenta_rag_habilitada": True,
            "ferramenta_sql_habilitada": True,
            "collection_rag": "casa_alma_catalogo"
        }
    },

    # -------------------------------------------------------------------------
    # PERSONA 4: Beatriz - Consultorio Odontologico
    # Caso de uso: Saude, agenda de consultas, FAQ clinico via RAG
    # -------------------------------------------------------------------------
    {
        "nome_empresa": "Consultorio Dra. Beatriz Almeida",
        "tipo_cliente": "B2C",
        "tier": "SME",
        "config": {
            "prompt_base": """Voce e a secretaria virtual do consultorio odontologico da Dra. Beatriz Almeida. O ambiente e de saude, seriedade e etica profissional.

Sua funcao e transmitir seguranca e organizar o fluxo de pacientes com eficiencia.

## Diretrizes de Personalidade
- Tom: Formal, respeitoso, claro e empatico
- Evite girias ou informalidade excessiva
- Prioridade absoluta: saude e bem-estar do paciente

## Missoes Prioritarias
1. **Recall Preventivo**: Identifique pacientes sem consulta ha mais de 6 meses e sugira cordialmente um check-up
2. **FAQ Clinico**: Responda perguntas administrativas (convenios, valores) e duvidas clinicas simples baseadas no FAQ aprovado
3. **Agendamento Organizado**: Gerencie a agenda de consultas com confirmacao previa

IMPORTANTE: Para questoes clinicas especificas ou emergencias, oriente o paciente a ligar diretamente para o consultorio.""",
            "horario_funcionamento": {
                "segunda": "08:00-18:00",
                "terca": "08:00-18:00",
                "quarta": "08:00-18:00",
                "quinta": "08:00-18:00",
                "sexta": "08:00-18:00",
                "sabado": "Fechado",
                "domingo": "Fechado",
                "observacao": "Intervalo: 12:00-14:00. Emergencias: (11) 99999-0000"
            },
            "ferramenta_agendamento_habilitada": True,
            "ferramenta_rag_habilitada": True,
            "ferramenta_sql_habilitada": False,
            "collection_rag": "dra_beatriz_faq"
        }
    },

    # -------------------------------------------------------------------------
    # PERSONA 5: Marcos - Eletricista Autonomo
    # Caso de uso: Profissional autonomo, formalizacao de comunicacao
    # -------------------------------------------------------------------------
    {
        "nome_empresa": "Marcos Eletricista",
        "tipo_cliente": "B2C",
        "tier": "BASIC",
        "config": {
            "prompt_base": """Voce e o assistente do Marcos Vinicius, eletricista profissional com mais de 15 anos de experiencia. Ele atua como autonomo trazendo seguranca tecnica de grande empresa com atendimento personalizado.

Sua funcao e ser a "cara profissional" do negocio, transformando comunicacoes informais em atendimento de qualidade.

## Diretrizes de Personalidade
- Tom: Prestativo, simples, direto e muito educado
- Linguagem: Clara e acessivel, sem jargoes tecnicos
- Valores: Pontualidade, limpeza apos servico, transparencia

## Missoes Prioritarias
1. **Formalizacao**: Transforme informacoes informais em comunicacoes profissionais (orcamentos detalhados, confirmacoes)
2. **Agendamento Inteligente**: Agende visitas agrupando clientes do mesmo bairro (Campo Grande e Zona Oeste do RJ)
3. **Orcamentos**: Servicos simples podem ser estimados via WhatsApp com fotos. Problemas complexos exigem visita tecnica.

## Pagamento e Garantia
- PIX (preferencial) ou dinheiro
- Parcelamento no cartao para servicos maiores (com taxa)
- Garantia de 90 dias na mao de obra
- Nao se responsabiliza por pecas compradas pelo cliente

Chave PIX: marcos.eletricista@email.com""",
            "horario_funcionamento": {
                "segunda": "07:00-19:00",
                "terca": "07:00-19:00",
                "quarta": "07:00-19:00",
                "quinta": "07:00-19:00",
                "sexta": "07:00-19:00",
                "sabado": "08:00-16:00",
                "domingo": "Somente emergencias"
            },
            "ferramenta_agendamento_habilitada": True,
            "ferramenta_rag_habilitada": True,
            "ferramenta_sql_habilitada": False,
            "collection_rag": "marcos_eletricista_conhecimento"
        }
    },
]

def run_LOCAL_DATABASE(db_url: str):
    """
    Função principal de Seed.
    É chamada automaticamente pelo comando 'vizu-db LOCAL_DATABASE'.
    """
    logger.info(f"🌱 Iniciando Seed no banco: {db_url.split('@')[-1]}")

    # Cria a engine de conexão
    engine = create_engine(db_url)

    with Session(engine) as session:
        count_inserted = 0
        count_skipped = 0

        for client_data in SEED_CLIENTS:
            nome = client_data["nome_empresa"]

            # 1. Verifica se o cliente já existe para evitar duplicatas
            statement = select(ClienteVizu).where(ClienteVizu.nome_empresa == nome)
            existing_client = session.exec(statement).first()

            if existing_client:
                logger.info(f"   ⚠️  Cliente '{nome}' já existe. Pulando.")
                count_skipped += 1
                continue

            # 2. Cria o Cliente
            # O SQLModel/Pydantic validará se a string corresponde a um Enum válido automaticamente
            try:
                novo_cliente = ClienteVizu(
                    nome_empresa=nome,
                    tipo_cliente=client_data["tipo_cliente"],
                    tier=client_data["tier"],
                    id=uuid.uuid4(),
                    api_key=str(uuid.uuid4())
                )
                session.add(novo_cliente)

                # Flush para gerar o ID do cliente e usarmos na config
                session.flush()

                # 3. Popula os campos de configuração diretamente no Cliente (merged model)
                config_data = client_data.get("config", {})
                novo_cliente.prompt_base = config_data.get("prompt_base", "Você é um assistente útil.")
                novo_cliente.horario_funcionamento = config_data.get("horario_funcionamento")
                novo_cliente.ferramenta_rag_habilitada = config_data.get("ferramenta_rag_habilitada", False)
                novo_cliente.ferramenta_sql_habilitada = config_data.get("ferramenta_sql_habilitada", False)
                novo_cliente.ferramenta_agendamento_habilitada = config_data.get("ferramenta_agendamento_habilitada", False)
                novo_cliente.collection_rag = config_data.get("collection_rag")
                session.add(novo_cliente)

                count_inserted += 1
                logger.info(f"   ✅ Cliente '{nome}' preparado para inserção.")

            except Exception as e:
                logger.error(f"   ❌ Erro ao preparar cliente '{nome}': {e}")
                session.rollback()
                continue

        # Commit final da transação
        try:
            session.commit()
            logger.info("="*40)
            logger.info(f"🎉 Seed concluído!")
            logger.info(f"   Novos registros: {count_inserted}")
            logger.info(f"   Existentes (pulados): {count_skipped}")
            logger.info("="*40)
        except IntegrityError as e:
            session.rollback()
            logger.error(f"❌ Erro de integridade ao salvar LOCAL_DATABASE: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erro inesperado no commit: {e}")