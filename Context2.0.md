Arquitetura de Contexto de Cliente para Agentes de IA
Visão Geral do Problema
Construímos um sistema para pequenas e médias empresas que utiliza agentes de IA para automatizar processos. O desafio central: como fornecer contexto relevante, seguro e modular sobre cada cliente para os agentes, considerando que:

Cada cliente tem necessidades diferentes (tiers, capacidades, estágios de negócio)

Agentes diferentes precisam de contextos diferentes (marketing vs compliance vs operações)

Os dados devem ser seguros (não expor credenciais ou informações confidenciais)

O sistema precisa escalar (múltiplos clientes, múltiplos agentes por cliente)

Solução Proposta: Master Prompt Modular
Desenvolvemos um conceito de "Master Prompt" - um arquivo de contexto estruturado que pode ser injetado seletivamente em diferentes nodes do agent graph.

Principais Componentes Identificados:
Identidade da Empresa (quem são)

Modelo de Negócio (o que fazem)

Contexto de Mercado (onde competem)

Momento Atual (estado dinâmico)

Operações e Políticas (como trabalham)

Capacidades Técnicas (ferramentas disponíveis)

Limites e Guardrails (o que não fazer)

Evolução para o SafeClientContext
Motivação Principal: Segurança por Design
O SafeClientContext nasce da necessidade de ter um container de dados que:

Não possa vazar informações sensíveis (credenciais, dados financeiros detalhados)

Seja imutável durante a execução (evitar modificações acidentais)

Permita injeção seletiva (apenas o contexto necessário para cada agente)

Seja tipado e validado (evitar erros de estrutura)

Estrutura do SafeClientContext - Campo por Campo
1. Campos de Identificação Básica
python
client_id: str          # ID público (não UUID interno)
nome_empresa: str       # Nome público seguro
tier: ClientTier        # Nível de serviço contratado
Motivação: Identificação mínima necessária. O client_id é público e não confidencial. O tier define capacidades disponíveis.

2. Seções do Master Prompt (Modulares)
Cada seção corresponde a uma parte do master prompt que pode ser injetada separadamente:

company_profile: Contexto estratégico da empresa

Motivação: Dá propósito e direção aos agentes

Conexão com Master Prompt: Seção 1 - "Quem somos e para onde vamos"

brand_voice: Como a empresa se comunica

Motivação: Mantém consistência de tom em todas as interações

Conexão com Master Prompt: Diretrizes de comunicação anti-greenwashing

current_moment: A seção mais dinâmica e crítica

Motivação: Agentes precisam saber o "estado atual" - prioridades, desafios, métricas

Conexão com Master Prompt: Seção 4 - "O que estamos focando AGORA"

Por que separada? Atualizada semanalmente vs outras seções (mensal/trimestral)

available_tools: O que o cliente pode fazer

Motivação: Define limites claros do que é permitido

Conexão com Master Prompt: Seção 7 - "Suas ferramentas e limitações"

3. Seções Omissas Intencionalmente
NÃO incluímos:

Credenciais de API (armazenadas em vault separado)

Dados financeiros detalhados

Informações pessoais


Por que omitir? Segurança em camadas. Mesmo se o contexto vazar, não compromete sistemas ou dados sensíveis.

Decisões Arquiteturais Críticas
1. Imutabilidade (frozen=True)
Motivação: Previne que agentes modifiquem acidentalmente o contexto durante a execução. Cada nova versão do contexto cria uma nova instância.

2. Modulabilidade (Enum de seções)
Motivação: Performance e relevância. Um agente de marketing não precisa do schema do banco de dados. Um agente de análise não precisa da voz da marca.

3. Separação Estado Estático vs Dinâmico
Estático: Perfil da empresa, voz da marca (mudam raramente)

Dinâmico: current_moment (muda frequentemente)

Motivação: Diferentes ciclos de atualização. O momento atual é atualizado semanalmente, enquanto o perfil da empresa muda trimestralmente.

4. Tipo Empresa-Segura (CompanyMoment)
Motivação: Dados do "momento atual" seguem um formato padronizado que não expõe informações sensíveis (ex: "crescimento de 20%" em vez de "faturamento R$ 1.2M").

Mecanismo de Injeção Modular
python
# Cada node do graph define o que precisa
node_requirements = {
    "compliance_report": [COMPANY_PROFILE, CURRENT_MOMENT, DATA_SCHEMA],
    "marketing_post": [BRAND_VOICE, TARGET_AUDIENCE, CURRENT_MOMENT]
}

# Compilação seletiva
context.get_compiled_context(required_sections)
Motivação: Reduz token usage, melhora performance, aumenta relevância do contexto.

Arquitetura de Armazenamento
Decisão: Banco Relacional + Cache Opcional
Primary Storage: Banco relacional com estrutura por seção

Motivação: Acesso direto por section_id (O(1)), versionamento granular

Secondary (opcional): Vector DB para busca semântica

Motivação: Para os 10% de casos onde precisamos buscar conceitos específicos

Por que não só vector DB? Porque 90% dos acessos são objetivos - sabemos exatamente quais seções precisamos. Vector DB seria overkill e menos performático para esse padrão.

Conclusões Finais
Princípios Fundamentais Adotados:
Segurança First: Nada sensível no contexto, imutabilidade por padrão

Modularidade Intencional: Injeção seletiva baseada na tarefa

Separação de Preocupações: Dados estáticos vs dinâmicos, identidade vs operações

Pragmatismo: Começar simples (apenas SQL), escalar conforme necessidade

Consistência: Formato padronizado para todos os clientes, com customizações controladas

Benefícios da Abordagem:
Segurança Robusta: Mesmo vazamento não compromete sistemas

Performance Otimizada: Injeção apenas do necessário reduz tokens e latência

Manutenção Facilitada: Atualizações granulares (só a seção que mudou)

Escalabilidade: Novo cliente = nova instância do mesmo modelo

Consistência: Agentes diferentes têm visão coerente do mesmo cliente


Proposta de estrutura de dados de clientes_vizu (Implicaria migraácao no Supabase e atualizaçao dos VIZU Models)

class ClientTier(str, Enum):
    """Tiers disponíveis para clientes"""
    BASIC = "BASIC"      # Até 10 agentes simples
    SME = "SME"          # Agentes + integrações básicas
    ENTERPRISE = "ENTERPRISE"  # Todos agents + customização


class ContextSection(str, Enum):
    """Seções do master prompt disponíveis"""
    # Core Identity
    COMPANY_PROFILE = "company_profile"
    BRAND_VOICE = "brand_voice"

    # Business
    PRODUCT_CATALOG = "product_catalog"
    TARGET_AUDIENCE = "target_audience"
    MARKET_CONTEXT = "market_context"

    # Operations
    CURRENT_MOMENT = "current_moment"  # Dinâmico
    TEAM_STRUCTURE = "team_structure"
    POLICIES_GUARDRAILS = "policies"

    # Technical
    DATA_SCHEMA = "data_schema"
    AVAILABLE_TOOLS = "available_tools"

    # Client-specific
    CLIENT_CUSTOM = "client_custom"  # Para extensões específicas


class CompanyMoment(BaseModel):
    """Modelo para a seção 'Current Moment' - dinâmica e frequentemente atualizada"""
    stage: str  # "startup", "growth", "scaling", "maturity"
    priorities: List[str]
    key_metrics: Dict[str, Any]  # KPIs atuais
    challenges: List[str]
    recent_wins: List[str]
    last_updated: datetime


class SafeClientContext(BaseModel):
    """
    Contexto modular do cliente para uso com LLM.

    Estrutura modular do master prompt - apenas dados seguros.
    Seções podem ser injetadas seletivamente nos agentes.

    NÃO INCLUIR:
    - Credenciais (api_keys, senhas)
    - IDs internos sensíveis
    - Endereços completos de pessoas físicas
    - Dados financeiros detalhados
    - Informações de contratos (valores absolutos)
    """

    model_config = ConfigDict(
        frozen=True,  # Imutável para evitar modificações acidentais
        extra='forbid'  # Não permitir campos extras
    )

    # ===== IDENTIFICAÇÃO BÁSICA (sempre injetada) =====
    client_id: str = Field(description="ID público do cliente (não confidencial)")
    nome_empresa: str
    tier: ClientTier = Field(default=ClientTier.BASIC)

    # ===== SEÇÕES DO MASTER PROMPT (modulares) =====

    # 1. IDENTIDADE DA EMPRESA
    company_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Perfil básico da empresa.
        Exemplo: {
            "legal_name": "Polen Soluções Ambientais Ltda.",
            "trading_name": "Polen",
            "business_archetype": "B2B Environmental Compliance",
            "mission": "Neutralizar externalidades ambientais...",
            "vision": "Ser a plataforma de economia circular...",
            "core_values": ["Transparência Radical", "Impacto Mensurável"]
        }
        """
    )

    brand_voice: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Voz da marca e estilo de comunicação.
        Exemplo: {
            "tone": "profissional, técnico mas acessível",
            "key_adjectives": ["confiável", "inovador", "parceiro"],
            "phrases_to_use": ["economia circular", "rastreabilidade", "compliance"],
            "phrases_to_avoid": ["100% sustentável", "verde", "eco-friendly sem contexto"],
            "communication_style": "Português brasileiro formal para clientes"
        }
        """
    )

    # 2. NEGÓCIO
    product_catalog: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Lista de produtos/serviços com descrições"
    )

    target_audience: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Público-alvo e ICP.
        Exemplo: {
            "primary_audience": "Diretores de Sustentabilidade em empresas de alimentos",
            "demographics": "Empresas com faturamento > R$50M/ano",
            "pain_points": ["Pressão regulatória PNRS", "Compromissos ESG públicos"],
            "buyer_personas": ["Diretor Sustentabilidade", "Jurídico Compliance", "Marketing"]
        }
        """
    )

    market_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Contexto de mercado e posicionamento.
        Exemplo: {
            "key_competitors": ["Empresa A (logística básica)", "Empresa B (consultoria ESG)"],
            "differentiators": ["Tecnologia blockchain", "Foco em embalagens", "Storytelling QR"],
            "regulatory_environment": "PNRS (Lei 12.305/2010) - Logística Reversa obrigatória",
            "market_trends": ["ESG como critério de investimento", "Tributação verde em discussão"]
        }
        """
    )

    # 3. OPERAÇÕES (seção dinâmica)
    current_moment: Optional[CompanyMoment] = Field(
        default=None,
        description="Situação atual da empresa - atualizada frequentemente"
    )

    team_structure: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Estrutura organizacional (aprosta e segura).
        Exemplo: {
            "key_roles": ["CEO (estratégia)", "COO (operações)", "CTO (plataforma)"],
            "main_contact": "Rafael Costa (Customer Success)",
            "communication_preferences": "Slack para urgências, email para formal"
        }
        """
    )

    policies_guardrails: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Políticas e limites operacionais.
        Exemplo: {
            "communication_rules": ["Sempre citar leis específicas", "Evitar greenwashing"],
            "operational_limits": ["Não prometer taxas sem dados reais"],
            "approval_requirements": ["Descontos >15%", "Mudanças em contratos"],
            "red_flags": ["Cliente querendo apenas certificado sem rastreabilidade"]
        }
        """
    )

    # 4. CONTEXTO TÉCNICO
    data_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Schema de dados disponíveis (seguro).
        Exemplo: {
            "available_tables": ["clientes", "coletas", "metricas_esg"],
            "data_formats": {"pesos": "kg", "datas": "DD/MM/AAAA"},
            "key_fields": ["kg_desviados_aterro", "status_rastreabilidade"]
        }
        """
    )

    available_tools: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""
        Ferramentas e capacidades disponíveis para este cliente.
        Exemplo: {
            "tier": "ENTERPRISE",
            "available_agents": ["Analista Compliance", "Otimizador Logística", "Relator ESG"],
            "approved_actions": ["Acessar dados agregados", "Gerar relatórios automáticos"],
            "restricted_actions": ["Alterar contratos", "Aprovar novos parceiros"],
            "workflow_approval": {
                "autonomous": ["Relatórios padrão", "Análises de dados"],
                "cs_approval": ["Mudanças em processos", "Novas integrações"],
                "ceo_approval": ["Parcerias estratégicas"]
            }
        }
        """
    )

    # 5. EXTENSÕES PERSONALIZADAS
    client_custom: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Extensões personalizadas para casos específicos do cliente"
    )

    # ===== META-DADOS PARA INJEÇÃO =====
    section_metadata: Dict[ContextSection, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadados sobre cada seção (tags, last_updated, priority)"
    )


    Resumo Final
O SafeClientContext não é apenas um container de dados - é um sistema de controle de contexto que:

Protege (dados sensíveis ficam fora)

Otimiza (apenas o contexto relevante é injetado)

Padroniza (todos os clientes seguem mesma estrutura)

Dinamiza (o "momento atual" mantém agentes atualizados)

Essa abordagem transforma o desafio do contexto em uma vantagem competitiva: agentes que entendem profundamente cada cliente, de forma segura e eficiente, permitindo personalização em escala para PMEs.