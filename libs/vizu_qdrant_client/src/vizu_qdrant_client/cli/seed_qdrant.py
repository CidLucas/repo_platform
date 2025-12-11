"""
Seed script para popular o Qdrant com dados de teste para RAG.
Cada collection corresponde a um cliente com ferramenta_rag_habilitada=True.

Uso:
    python -m vizu_qdrant_client.cli.seed_qdrant

Requer:
    - QDRANT_URL (default: http://localhost:6333)
    - EMBEDDING_SERVICE_URL (default: http://localhost:11435)
    - EMBEDDING_VECTOR_SIZE (default: 1024 para multilingual-e5-large)

IMPORTANTE: Este script usa EXCLUSIVAMENTE o .env da RAIZ do monorepo.
"""
import logging
import os
from typing import Any

from qdrant_client import QdrantClient, models

# Configuracao de log
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACAO (lida do .env da raiz via variáveis de ambiente)
# =============================================================================

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:11435")

# Dimensao do vetor - DEVE corresponder ao modelo configurado no embedding_service
# intfloat/multilingual-e5-large = 1024
# sentence-transformers/all-MiniLM-L6-v2 = 384
VECTOR_SIZE = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1024"))

# =============================================================================
# DADOS DE TESTE PARA RAG
# Cada entrada corresponde a uma collection_rag definida no seed.py
# =============================================================================

RAG_DATA: dict[str, list[dict[str, Any]]] = {
    # -------------------------------------------------------------------------
    # Studio J - Base de conhecimento (Juliana - Salao de Beleza)
    # Estruturado para consulta rapida de regras e servicos
    # -------------------------------------------------------------------------
    "studio_j_conhecimento": [
        {
            "id": "sobre_studio_j",
            "title": "Sobre o Studio J",
            "content": """O Studio J nasceu da paixao de Juliana Andrade pela arte de transformar a autoestima. Comecando como assistente e crescendo atraves do poder das redes sociais, Juliana criou um espaco moderno e "instagramavel" em Botafogo, Rio de Janeiro. Nosso foco nao e apenas cortar cabelos, mas criar uma experiencia de beleza personalizada e atual.

Localizacao: Rua Voluntarios da Patria, Botafogo, RJ. (Proximo ao metro)."""
        },
        {
            "id": "servicos_studio_j",
            "title": "Servicos do Studio J",
            "content": """NOSSOS SERVICOS

Morena Iluminada e Mechas: Nossa assinatura. Tecnicas de clareamento que preservam a saude do fio, criando contrastes naturais e sofisticados.

Corte Personalizado: Cortes modernos (Long Bob, Shaggy, Pixie) adaptados ao formato do rosto e textura do fio da cliente.

Tratamentos e Cronograma: Hidratacao, Nutricao e Reconstrucao com produtos de linhas premium para recuperar a saude pos-quimica.

Finalizacao e Styling: Escovas modeladas e ondas (Babyliss) para eventos."""
        },
        {
            "id": "politica_agendamento_studio_j",
            "title": "Politica de Agendamento e Cancelamento",
            "content": """POLITICA DE AGENDAMENTO E CANCELAMENTO (LEIA COM ATENCAO)

Para garantir o respeito ao tempo de todas as nossas clientes e da nossa equipe, seguimos regras estritas:

Atrasos: Tolerancia maxima de 15 minutos. Apos esse tempo, o atendimento podera ser reduzido ou cancelado para nao prejudicar a cliente seguinte.

Cancelamentos e Reagendamentos: Devem ser feitos com no minimo 24 horas de antecedencia.

No-Show (Nao comparecimento): O nao comparecimento sem aviso previo nos impede de encaixar outra cliente. Em caso de reincidencia, sera cobrada uma taxa de reserva antecipada de 50% para novos agendamentos.

Sinal: Para procedimentos longos (como mechas), exigimos um sinal de reserva via PIX no momento do agendamento.

PAGAMENTO: Aceitamos cartoes de credito, debito e PIX."""
        },
        {
            "id": "cuidados_pre_quimica",
            "title": "Cuidados Pre-Quimica",
            "content": """CUIDADOS ANTES DE PROCEDIMENTOS QUIMICOS

Para Coloracao e Mechas:
- Venha com o cabelo seco e sem produtos (sem leave-in, oleo ou creme)
- Nao lave o cabelo no dia do procedimento - a oleosidade natural protege o couro cabeludo
- Evite usar chapinha ou babyliss nos 3 dias anteriores
- Informe se usou henna ou tintura de caixa nos ultimos 6 meses

Para Progressiva e Alisamentos:
- Cabelo deve estar limpo e SEM residuos de silicone
- Ultima lavagem: 24-48h antes do procedimento
- Nao usar nenhum produto apos a lavagem
- Traga fotos de referencia do resultado desejado"""
        },
        {
            "id": "cuidados_pos_coloracao",
            "title": "Cuidados Pos-Coloracao",
            "content": """CUIDADOS APOS COLORACAO

Primeiras 48 horas:
- NAO lave o cabelo nas primeiras 48 horas
- Evite piscina, mar e chuva
- Nao use secador muito quente

Manutencao Semanal:
- Use shampoo e condicionador para cabelos coloridos
- Aplique mascara de hidratacao 1x por semana
- Tonalizante para manter a cor: a cada 15-20 dias

Retoque:
- Raiz: a cada 30-45 dias dependendo do crescimento
- Mechas: a cada 60-90 dias"""
        }
    ],

    # -------------------------------------------------------------------------
    # Casa com Alma - Base de conhecimento (Clara - Loja de Decoracao)
    # Texto corrido para capturar o tom emocional e historia da marca
    # -------------------------------------------------------------------------
    "casa_alma_catalogo": [
        {
            "id": "historia_casa_alma",
            "title": "Historia e Filosofia da Casa com Alma",
            "content": """A Casa com Alma nao e apenas uma loja de decoracao, e a materializacao do sonho de Clara Ribeiro. Apos anos trabalhando como compradora em grandes redes de varejo e sentindo a frieza dos produtos produzidos em massa, Clara decidiu criar um refugio em Ipanema, Rio de Janeiro, onde cada objeto conta uma historia. Localizada na Rua Visconde de Piraja, a loja e um convite para desacelerar. O negocio valoriza profundamente o design brasileiro e o trabalho manual, operando com a filosofia de que nossa casa deve ser o nosso santuario."""
        },
        {
            "id": "produtos_casa_alma",
            "title": "Produtos da Casa com Alma",
            "content": """PRODUTOS SELECIONADOS A DEDO PELA CLARA

Ceramicas Artesanais: Pecas de oleiros locais, perfeitas para compor mesas afetivas. Cada peca e unica e feita a mao.

Perfumaria para Casa: Velas de cera vegetal e difusores com aromas naturais para criar atmosferas acolhedoras.

Curadoria de Texteis: Almofadas bordadas a mao e mantas de algodao organico. Todas as pecas sao feitas com materiais naturais e tingimento artesanal.

Papelaria Fina: Secao especial para quem ama a escrita, com cadernos, agendas e cartoes artesanais.

O servico da Casa com Alma e puramente consultivo: a equipe e treinada para ajudar o cliente a encontrar o presente perfeito ou a peca que falta para trazer aconchego a um ambiente, tanto na loja fisica quanto no atendimento via WhatsApp."""
        },
        {
            "id": "politicas_casa_alma",
            "title": "Politicas de Trocas e Entregas",
            "content": """POLITICAS DA CASA COM ALMA

Trocas: Aceitamos trocas de produtos em perfeito estado e com a etiqueta original no prazo de ate 30 dias corridos apos a compra.

Defeitos: Em caso de defeito de fabricacao (raro, dada a nossa conferencia manual), a troca e imediata ou o valor e devolvido.

Entregas:
- Zona Sul do Rio: entrega via motoboy
- Todo o Brasil: envio via transportadora
- Compras online ou via WhatsApp

IMPORTANTE: Por trabalharmos com pecas artesanais unicas, o estoque da loja fisica e do site podem ter pequenas variacoes de disponibilidade. Sempre avisaremos o cliente imediatamente caso haja qualquer divergencia.

Nosso compromisso e com a beleza, a verdade e a satisfacao de quem leva um pedacinho da nossa alma para casa.

Pequenas variacoes nas pecas artesanais sao caracteristicas do processo manual e NAO configuram defeito."""
        },
        {
            "id": "texteis_luminarias",
            "title": "Texteis e Luminarias Artesanais",
            "content": """COLECAO TEXTEIS - Tecidos Naturais
Todas as pecas sao feitas com algodao organico e tingimento natural.

Almofadas Decorativas:
- Almofada Abraco 45x45cm: R$ 119 (cores: off-white, bege, terracota)
- Almofada No 30x50cm: R$ 99 (cores: cru, mostarda, verde salvia)

Mantas:
- Manta Aconchego 130x170cm: R$ 289 (100% algodao com franjas artesanais)
- Manta Trico 100x150cm: R$ 349 (feita a mao em trico grosso)

Cuidados: Lavar a mao com sabao neutro. Nao usar alvejante. Secar a sombra.

LUMINARIAS ARTESANAIS - Linha Fibra
- Pendente Ninho 40cm: R$ 389 (rattan natural, luz difusa)
- Pendente Sino 30cm: R$ 289 (palha trancada)
- Abajur Mesa 45cm: R$ 249 (base ceramica + cupula palha)

Todas com soquete E27. Lampada nao inclusa (recomendamos LED 7W amarela)."""
        }
    ],

    # -------------------------------------------------------------------------
    # Dra. Beatriz - FAQ Odontologico
    # Estruturado para passar credibilidade tecnica e clareza administrativa
    # -------------------------------------------------------------------------
    "dra_beatriz_faq": [
        {
            "id": "historia_dra_beatriz",
            "title": "Historia e Filosofia do Consultorio",
            "content": """NOSSA HISTORIA E FILOSOFIA

Com mais de 25 anos de atuacao na Tijuca, a Dra. Beatriz Almeida construiu um consultorio pautado na etica, na seguranca e na odontologia baseada em evidencias. Diferente das "clinicas de massa", aqui o atendimento e individualizado, focado na saude bucal a longo prazo e na prevencao, fugindo de modismos esteticos que comprometem a estrutura dental.

Endereco: Praca Saens Pena, Tijuca, Rio de Janeiro - RJ. (Edificio Comercial)."""
        },
        {
            "id": "servicos_dra_beatriz",
            "title": "Servicos Prestados",
            "content": """SERVICOS PRESTADOS

Clinica Geral e Prevencao: Limpeza (profilaxia), aplicacao de fluor, restauracoes e check-up semestral.

Reabilitacao Oral: Proteses fixas e removiveis, coroas e facetas de porcelana (com indicacao funcional).

Implantodontia: Implantes dentarios para reposicao de perdas, realizados com planejamento cirurgico minucioso.

Endodontia (Canal): Tratamento realizado com tecnologias rotatorias para maior conforto."""
        },
        {
            "id": "politicas_dra_beatriz",
            "title": "Politicas do Consultorio",
            "content": """INFORMACOES AO PACIENTE E POLITICAS

Agendamento: As consultas sao marcadas com intervalo de tempo suficiente para um atendimento sem pressa e esterilizacao rigorosa da sala entre pacientes.

Reagendamento: Pedimos a gentileza de avisar com 24 horas de antecedencia caso nao possa comparecer, para que possamos oferecer o horario a um paciente em lista de espera ou com dor.

Pagamentos e Reembolsos: O atendimento e particular. Oferecemos suporte completo para reembolso (Livre Escolha), emitindo recibos, notas fiscais e laudos necessarios para que o paciente solicite o ressarcimento junto ao seu plano de saude de forma agil.

Formas de pagamento: PIX, transferencia e cartoes.

Emergencias: Buscamos sempre encaixar pacientes antigos com dor aguda no mesmo dia, dentro do horario comercial."""
        },
        {
            "id": "cuidados_saude_bucal",
            "title": "Cuidados com Saude Bucal",
            "content": """CUIDADOS DIARIOS COM SAUDE BUCAL

Escovacao Correta:
- Escove pelo menos 3x ao dia (manha, apos almoco, antes de dormir)
- Use escova de cerdas macias
- Movimentos circulares suaves
- Tempo minimo: 2 minutos
- Troque a escova a cada 3 meses

Fio Dental:
- Use TODOS os dias, preferencialmente a noite
- Passe suavemente entre todos os dentes
- Nao "serre" o fio - movimentos de vai-e-vem

Sinais de Alerta - Procure o dentista se notar:
- Sangramento gengival frequente
- Dor de dente persistente
- Sensibilidade ao frio/calor
- Mau halito constante
- Feridas que nao cicatrizam

Prevencao: Consulta de rotina a cada 6 meses."""
        }
    ],

    # -------------------------------------------------------------------------
    # Oficina Mendes - Base de conhecimento (Ricardo - Mecanica)
    # Texto corrido para passar sensacao de tradicao e confianca
    # -------------------------------------------------------------------------
    "oficina_mendes_conhecimento": [
        {
            "id": "historia_oficina",
            "title": "Historia da Oficina Mendes",
            "content": """A Oficina Mendes e um patrimonio do bairro de Nova Iguacu, na Baixada Fluminense. A historia comecou com o pai de Ricardo, o saudoso "Seu Mendes", que ensinou ao filho que a chave inglesa aperta o parafuso, mas o que segura o cliente e a honestidade. Hoje, Ricardo Mendes comanda a oficina mantendo o legado de duas geracoes: servico bem feito, sem inventar defeito onde nao existe.

Somos especialistas em mecanica geral para carros nacionais e importados, com um carinho especial por modelos mais antigos que exigem ouvido treinado, mas tambem atendemos a frota moderna com dignidade.

Localizacao: Proximo ao centro de Nova Iguacu, facil acesso."""
        },
        {
            "id": "servicos_oficina",
            "title": "Servicos da Oficina Mendes",
            "content": """NOSSOS SERVICOS PRINCIPAIS

Revisao Preventiva: Troca de oleo, filtros e correias. Fundamental para evitar problemas maiores.

Manutencao de Freios: Pastilhas, discos e fluidos. Seguranca em primeiro lugar.

Reparos de Suspensao: Amortecedores, molas e buchas.

Alinhamento Basico: Para seu carro rodar reto e os pneus durarem mais.

Diagnosticos de Motor: Identificamos problemas atraves de experiencia e equipamentos.

Horario de Funcionamento:
- Segunda a sexta: 08:00 as 18:00
- Sabado: ate 12:00
- Domingo: NAO trabalhamos"""
        },
        {
            "id": "garantias_oficina",
            "title": "Garantias e Regras da Oficina",
            "content": """GARANTIAS E REGRAS - Na Oficina Mendes, a palavra vale ouro, mas as regras sao claras para proteger a todos.

Garantia: Todos os nossos servicos de mao de obra e as pecas fornecidas por nos possuem garantia legal de 90 dias.

Autorizacao: NAO realizamos nenhum servico extra sem a autorizacao expressa do cliente. Se o carro entrou para trocar oleo e vimos que o freio esta ruim, nos avisamos, orcamos e so mexemos se o dono autorizar.

Pagamentos: Aceitamos cartoes de credito, debito e PIX.

Taxa de Patio: Carros que nao forem retirados em ate 5 dias uteis apos o aviso de "pronto" estarao sujeitos a uma taxa de diaria de patio. Nosso espaco fisico e limitado e precisamos girar a oficina para atender outros vizinhos que precisam.

Confianca e via de mao dupla, e aqui voce pode deixar seu carro tranquilo."""
        }
    ],

    # -------------------------------------------------------------------------
    # Marcos Eletricista - Base de conhecimento
    # Estruturado como portfolio/orcamento formal
    # -------------------------------------------------------------------------
    "marcos_eletricista_conhecimento": [
        {
            "id": "sobre_marcos",
            "title": "Quem e Marcos Eletricista",
            "content": """QUEM SOU

Sou Marcos Vinicius, eletricista profissional com mais de 15 anos de experiencia. Minha formacao vem da pratica em grandes construtoras e cursos de aperfeicoamento. Atuo hoje como autonomo, trazendo para sua casa ou comercio a seguranca tecnica de uma grande empresa, mas com atendimento personalizado.

Prezo pela pontualidade, limpeza apos o servico e transparencia nos valores.

AREA DE ATENDIMENTO
Foco principal em Campo Grande (RJ) e bairros vizinhos da Zona Oeste. Atendo residencias, pequenos comercios e condominios."""
        },
        {
            "id": "servicos_marcos",
            "title": "Servicos de Eletrica",
            "content": """MEUS SERVICOS

Instalacao Eletrica Residencial:
- Fiacao nova
- Instalacao de tomadas e interruptores
- Ventiladores de teto
- Luminarias

Manutencao e Reparos:
- Identificacao e conserto de curto-circuito
- Troca de disjuntores
- Instalacao de chuveiros
- Reparo de "fuga de energia" (conta alta)

Padrao de Entrada:
- Adequacao de medidores
- Quadros de distribuicao (QDC) conforme normas da concessionaria"""
        },
        {
            "id": "orcamentos_marcos",
            "title": "Orcamentos e Visitas Tecnicas",
            "content": """ORCAMENTOS E VISITAS TECNICAS

Orcamento Estimado: Para servicos simples (ex: trocar 1 chuveiro), posso passar uma estimativa por WhatsApp se voce enviar fotos e videos.

Visita Tecnica: Para problemas complexos (ex: "luz caindo toda hora") ou instalacoes grandes, e necessaria uma visita para avaliacao.

Formalizacao: Todo servico aprovado tera um orcamento enviado por escrito (PDF ou texto detalhado), listando mao de obra e materiais necessarios."""
        },
        {
            "id": "pagamento_garantia_marcos",
            "title": "Pagamento e Garantia",
            "content": """FORMAS DE PAGAMENTO E GARANTIA

Pagamento:
- PIX (preferencial)
- Dinheiro
- Para servicos maiores, podemos negociar parcelamento no cartao (mediante taxa da maquininha)

Garantia:
- Ofereco garantia de 90 dias na minha mao de obra
- Se o problema voltar, eu volto e resolvo sem custo adicional
- NAO me responsabilizo por defeitos de fabricacao em pecas compradas pelo cliente, mas ajudo no diagnostico"""
        }
    ]
}


def get_embedding(text: str) -> list[float]:
    """
    Gera embedding usando o serviço de embedding local (HuggingFace).
    Usa o endpoint /embed do embedding_service que aplica os prefixos E5 automaticamente.
    """
    import requests

    try:
        response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/embed",
            json={"texts": [text]},
            timeout=60  # Timeout maior para modelos grandes
        )
        if response.status_code == 200:
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                embedding = embeddings[0]
                logger.debug(f"   Embedding gerado: {len(embedding)} dims")
                return embedding
        else:
            logger.error(f"   Erro do embedding service: {response.status_code} - {response.text}")
            raise Exception(f"Embedding service retornou {response.status_code}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"   Não foi possível conectar ao embedding service em {EMBEDDING_SERVICE_URL}")
        logger.error(f"   Erro: {e}")
        logger.error("   Certifique-se de que o embedding_service está rodando (docker compose up embedding_service)")
        raise
    except Exception as e:
        logger.error(f"   Erro ao gerar embedding: {e}")
        raise


def create_collection_if_not_exists(client: QdrantClient, collection_name: str, force_recreate: bool = True):
    """
    Cria collection se nao existir.
    Se force_recreate=True e a collection existir, deleta e recria para garantir dimensões corretas.
    """
    try:
        existing = client.get_collection(collection_name)
        existing_size = existing.config.params.vectors.size

        if force_recreate or existing_size != VECTOR_SIZE:
            logger.info(f"   Collection '{collection_name}' existe com {existing_size} dims, recriando com {VECTOR_SIZE}...")
            client.delete_collection(collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"   Collection '{collection_name}' recriada com {VECTOR_SIZE} dims")
            return False
        else:
            logger.info(f"   Collection '{collection_name}' ja existe com dimensões corretas ({VECTOR_SIZE})")
            return True
    except Exception:
        logger.info(f"   Criando collection '{collection_name}' com {VECTOR_SIZE} dims...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE
            )
        )
        return False


def seed_collection(client: QdrantClient, collection_name: str, documents: list[dict[str, Any]]):
    """Popula uma collection com documentos."""
    logger.info(f"\n{'='*60}")
    logger.info(f"📚 Populando collection: {collection_name}")
    logger.info(f"{'='*60}")

    # Cria collection se necessario
    create_collection_if_not_exists(client, collection_name)

    # Prepara pontos para upsert
    points = []
    for idx, doc in enumerate(documents):
        doc_id = doc.get("id", f"doc_{idx}")
        title = doc.get("title", "")
        content = doc.get("content", "")

        # Texto combinado para embedding
        text_for_embedding = f"{title}\n\n{content}"

        logger.info(f"   Gerando embedding para: {title}...")
        embedding = get_embedding(text_for_embedding)

        point = models.PointStruct(
            id=idx + 1,  # IDs numericos sequenciais
            vector=embedding,
            payload={
                "doc_id": doc_id,
                "title": title,
                "content": content,
                "collection": collection_name
            }
        )
        points.append(point)

    # Upsert em batch
    logger.info(f"   Inserindo {len(points)} documentos...")
    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )

    logger.info(f"   ✅ Collection '{collection_name}' populada com {len(points)} documentos")


def run_seed():
    """Funcao principal de seed do Qdrant."""
    logger.info("\n" + "="*60)
    logger.info("🌱 SEED QDRANT - Populando collections de teste")
    logger.info("="*60)
    logger.info(f"   Qdrant URL: {QDRANT_URL}")
    logger.info(f"   Vector Size: {VECTOR_SIZE}")
    logger.info(f"   Embedding Service: {EMBEDDING_SERVICE_URL}")

    # Conecta ao Qdrant
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        # Testa conexao
        client.get_collections()
        logger.info("   ✅ Conectado ao Qdrant")
    except Exception as e:
        logger.error(f"   ❌ Erro ao conectar ao Qdrant: {e}")
        logger.error("   Verifique se o Qdrant esta rodando em " + QDRANT_URL)
        return

    # Popula cada collection
    for collection_name, documents in RAG_DATA.items():
        try:
            seed_collection(client, collection_name, documents)
        except Exception as e:
            logger.error(f"   ❌ Erro ao popular '{collection_name}': {e}")
            import traceback
            traceback.print_exc()

    logger.info("\n" + "="*60)
    logger.info("🎉 SEED QDRANT FINALIZADO")
    logger.info("="*60)

    # Lista collections criadas
    collections = client.get_collections()
    logger.info("\n   Collections disponiveis:")
    for col in collections.collections:
        info = client.get_collection(col.name)
        logger.info(f"   - {col.name}: {info.points_count} pontos, {info.config.params.vectors.size} dims")


if __name__ == "__main__":
    run_seed()
