# 1. Dra. Beatriz (Dentista)
# Adicionado: Ferramenta SQL para "Gerenciamento de Insumos"
dados_persona_beatriz = {
    "nome_empresa": "Consultório Dra. Beatriz Almeida",
    "tipo_cliente": "B2C",
    "tier": "SME",
    "prompt_base": """
Você é a secretária virtual sênior do consultório da Dra. Beatriz.
Suas funções principais:
1. Gestão de Agenda: Marcar, desmarcar e reagendar consultas. Verifique disponibilidade sempre.
2. Tira-Dúvidas (RAG): Responda sobre preços, procedimentos e políticas usando a base de conhecimento.
3. Gestão de Insumos (Interno): Se a Dra. Beatriz perguntar sobre "estoque de anestésico" ou "luvas", use a ferramenta de busca em banco de dados (SQL) para verificar a quantidade disponível.

Tom de voz: Formal, acolhedor e muito organizado.
    """.strip(),
    "horario_funcionamento": {
        "segunda_a_sexta": "08:00 - 18:00",
        "almoco": "12:00 - 14:00"
    },
    "ferramenta_agendamento_habilitada": True,  # Para Consultas
    "ferramenta_rag_habilitada": True,          # Para Preços/Políticas
    "ferramenta_sql_habilitada": True,          # Para Insumos
    "collection_rag": "faq_beatriz_v2"
}

# 2. Pixel Store (Loja de Eletrônicos)
# Foco: Vendas e Estoque
dados_persona_pixel = {
    "nome_empresa": "Pixel Store",
    "tipo_cliente": "B2C",
    "tier": "SME",
    "prompt_base": """
Você é o vendedor especialista da Pixel Store, loja de eletrônicos focada em gamers e entusiastas.
Suas funções principais:
1. Vendas Consultivas (RAG): Ajude o cliente a escolher o produto ideal explicando especificações técnicas e garantias.
2. Checagem de Estoque (SQL): Antes de fechar a venda, SEMPRE verifique na "planilha/banco" (ferramenta SQL) se o produto está disponível na cor/modelo desejado.
3. Status de Pedido: Informe onde está a entrega do cliente.

Tom de voz: Tech-savvy, entusiasta, ágil e usa termos técnicos quando necessário, mas simplifica para leigos.
    """.strip(),
    "horario_funcionamento": {
        "segunda_a_sabado": "10:00 - 22:00",
        "domingo": "14:00 - 20:00"
    },
    "ferramenta_agendamento_habilitada": False,
    "ferramenta_rag_habilitada": True,          # Para Specs/Políticas
    "ferramenta_sql_habilitada": True,          # Para Estoque/Planilha
    "collection_rag": "catalogo_pixel_store"
}

# 3. Brasa & Malte (Restaurante com Delivery)
# Foco: Pedidos, Cardápio e Reservas
dados_persona_restaurante = {
    "nome_empresa": "Brasa & Malte Burger",
    "tipo_cliente": "B2C",
    "tier": "SME",
    "prompt_base": """
Você é o atendente do Brasa & Malte, uma hamburgueria artesanal com delivery forte.
Suas funções principais:
1. Tirar Pedidos (Delivery): Pergunte o que o cliente quer, confirme o endereço e a forma de pagamento. Use o cardápio (RAG) para sugerir adicionais.
2. Reservas de Mesa: Agende mesas para o salão, respeitando a tolerância de atraso.
3. Cardápio: Tire dúvidas sobre ingredientes e alérgenos.

Tom de voz: Descontraído, "dá água na boca" (use adjetivos apetitosos), mas eficiente para não atrasar o pedido.
    """.strip(),
    "horario_funcionamento": {
        "terca_a_domingo": "18:00 - 23:30",
        "segunda": "Fechado"
    },
    "ferramenta_agendamento_habilitada": True,  # Para Reservas
    "ferramenta_rag_habilitada": True,          # Para Cardápio/Preços
    "ferramenta_sql_habilitada": False,         # Pedidos geralmente vão para um checkout, não SQL direto aqui
    "collection_rag": "cardapio_brasa_malte"
}


Dr Beatriz
## DESCRITIVO DO NEGÓCIO
O Consultório Dra. Beatriz Almeida é referência em odontologia humanizada na Tijuca. Com 25 anos de experiência, focamos em saúde bucal preventiva e reabilitação oral.

## SERVIÇOS E PREÇOS (TABELA PARTICULAR 2024)
* **Consulta Inicial / Avaliação:** R$ 350,00 (Inclui anamnese e raio-x periapical).
* **Profilaxia (Limpeza Completa):** R$ 250,00.
* **Restauração em Resina:** A partir de R$ 400,00.
* **Clareamento Caseiro (Moldeira):** R$ 900,00. (Mais confortável, feito em casa com supervisão).
* **Clareamento a Laser (Consultório):** R$ 1.500,00. (Resultado mais rápido, ideal para quem tem pressa, mas pode gerar mais sensibilidade).
* **Tratamento de Canal (Endodontia):** A partir de R$ 800,00 (Molar).

## CONVÊNIOS E REEMBOLSOS
* **Não aceitamos convênios diretamente** para cobrir o tratamento. Todo atendimento é particular.
* **Sistema de Reembolso (Livre Escolha):** Aceitamos pacientes com **Bradesco Saúde, SulAmérica, Amil e One Health** que possuam a modalidade de livre escolha.
* **Como funciona:** Você paga a consulta/procedimento, nós emitimos a Nota Fiscal e o relatório clínico detalhado no mesmo dia, e você solicita o reembolso integral ou parcial ao seu plano. Ajudamos com a documentação.

## DOCUMENTAÇÃO FISCAL
* Emitimos Nota Fiscal para todos os procedimentos, essencial para declaração de Imposto de Renda e pedidos de reembolso. Basta solicitar na recepção ou via WhatsApp após o pagamento.

## POLÍTICAS DE AGENDAMENTO
* **Cancelamentos:** Devem ser feitos com 24h de antecedência.
* **Atrasos:** Tolerância de 15 minutos.
* **Emergências:** Tentamos encaixe no mesmo dia para casos de dor aguda.

## ENDEREÇO E HORÁRIOS
Praça Saens Peña, 45, Sala 808 - Tijuca, RJ.
Seg-Sex: 08:00 às 18:00. (Almoço 12:00-14:00).

Pixel Store
## DESCRITIVO DO NEGÓCIO
A Pixel Store é o paraíso dos geeks e entusiastas de tecnologia. Localizada em um quiosque moderno no Shopping Metropolitano, oferecemos o que há de mais recente em periféricos, áudio e acessórios para smartphones, com consultoria especializada de quem realmente entende do assunto.

## SERVIÇOS E PRODUTOS (BEST-SELLERS)
* **Vendas Consultivas:** Auxiliamos na escolha do produto ideal para o seu setup.
* **Fone Bluetooth Noise Cancelling (Modelo X-Pro):** R$ 399,90.
* **Carregador Turbo USB-C 30W:** R$ 120,00.
* **Teclado Mecânico RGB (Switch Blue/Red):** R$ 280,00.
* **Mouse Gamer 12000 DPI:** R$ 150,00.
* **Power Bank 20.000mAh:** R$ 180,00.
* *Obs: Para disponibilidade de estoque (cores e modelos), consulte sempre nosso sistema.*

## POLÍTICAS DE TROCA E DEVOLUÇÃO
* **Direito de Arrependimento (Compras Online):** 7 dias corridos após o recebimento para devolução total, desde que o produto esteja lacrado.
* **Defeito de Fabricação:** Garantia de 90 dias direto na loja. Após esse prazo, a garantia é com o fabricante (geralmente 1 ano).
* **Troca por Gosto (Loja Física):** Permitimos troca por outro produto em até 30 dias, desde que a embalagem esteja intacta e com nota fiscal. Não trocamos produtos com sinais de uso.

## ENDEREÇO
Av. Embaixador Abelardo Bueno, 1300 - Shopping Metropolitano Barra, Piso L2 (Quiosque em frente ao cinema). Rio de Janeiro - RJ.

## HORÁRIO DE FUNCIONAMENTO
Segunda a Sábado: 10:00 às 22:00.
Domingo: 14:00 às 20:00.

## FORMAS DE PAGAMENTO
* PIX.
* Cartão de Crédito (até 10x sem juros).
* Cartão de Débito.
* Apple Pay / Samsung Pay.

Brasa e malte
## DESCRITIVO DO NEGÓCIO
O Brasa & Malte é uma hamburgueria artesanal que une a rusticidade da carne feita na brasa com a praticidade do delivery. Nosso ambiente físico é descontraído, ideal para happy hours, e nosso delivery é conhecido pela rapidez e embalagens térmicas que mantém o lanche quente.

## CARDÁPIO E SERVIÇOS (PREÇOS DELIVERY/SALÃO)
* **Hambúrguer Clássico:** (Blend 180g, queijo cheddar, maionese da casa, pão brioche) - R$ 32,00.
* **Hambúrguer da Casa (O Brabo):** (Blend 180g, bacon crocante, cebola caramelizada, cheddar, pão australiano) - R$ 39,00.
* **Batata Frita Rústica (Porção individual):** R$ 16,00.
* **Refrigerante Lata:** R$ 7,00.
* **Milkshake de Nutella:** R$ 22,00.
* **Taxa de Entrega:** Fixa em R$ 8,00 para raio de até 5km. Grátis acima de R$ 100,00.

## SERVIÇOS OFERECIDOS
* Delivery (iFood e WhatsApp Próprio).
* Reservas de mesa para comemorações.
* Retirada no balcão (Take away).

## POLÍTICAS E RESERVAS
* **Reservas:** Aceitamos reservas para o salão até as 20:30. Tolerância de atraso de 15 minutos. Após isso, a mesa é liberada por ordem de chegada.
* **Delivery - Erros/Trocas:** Se o lanche chegar frio ou errado, enviamos um novo imediatamente ou estornamos o valor via PIX.
* **Cancelamento de Pedido:** Só é permitido se o pedido ainda não tiver entrado em produção (status: "Na Cozinha").

## ENDEREÇO
Rua Olegário Maciel, 250 - Barra da Tijuca, Rio de Janeiro - RJ.

## HORÁRIO DE FUNCIONAMENTO
Terça a Domingo: 18:00 às 23:30.
Segunda-feira: Fechado para manutenção.

## FORMAS DE PAGAMENTO
* **Delivery:** PIX no pedido, Cartão na maquininha (entregador leva), Dinheiro (informar troco). Não aceitamos cheque.
* **Salão:** Todos os cartões de crédito/débito, Vale Refeição (VR/Alelo/Sodexo) e PIX.