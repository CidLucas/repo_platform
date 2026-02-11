"""
Built-in prompt templates for Vizu services.

These templates serve as defaults when no database prompts are configured.
They can be overridden per-client in the database.
"""

from dataclasses import dataclass, field
from enum import Enum


class PromptCategory(Enum):
    """Categories for organizing prompts."""

    SYSTEM = "system"  # System prompts for agent initialization
    ACTION = "action"  # Action-specific prompts (confirmations, etc.)
    RAG = "rag"  # RAG-related prompts
    ELICITATION = "elicitation"  # User clarification prompts
    ERROR = "error"  # Error handling prompts


@dataclass
class PromptTemplateConfig:
    """Configuration for a prompt template."""

    name: str
    content: str
    category: PromptCategory
    description: str = ""
    required_variables: list[str] = field(default_factory=list)
    optional_variables: dict[str, str] = field(default_factory=dict)
    version: int = 1




# Builtin fallback - Langfuse prompt "basic" takes precedence
ATENDENTE = PromptTemplateConfig(
    name="basic",
    category=PromptCategory.SYSTEM,
    description="Data Analyst agent prompt - builtin fallback",
    required_variables=["nome_empresa"],
    optional_variables={
        "tools_description": "",
        "context_sections": "",
    },
    content="""Você é o analista de dados da **{{ nome_empresa }}**.

{% if context_sections %}
# CONTEXTO
{{ context_sections }}
{% endif %}

{% if tools_description %}
# FERRAMENTAS
{{ tools_description }}
{% endif %}

# REGRAS

## Uso de Ferramentas
- Perguntas sobre dados → chame `executar_sql_agent` com a pergunta em linguagem natural
- Perguntas sobre processos/políticas → chame `executar_rag_cliente`
- NUNCA responda sobre dados sem consultar uma ferramenta

## Estratégias de Fallback

Quando uma métrica ou dimensão não estiver disponível, ofereça alternativas:

| Pedido | Se não tiver | Ofereça |
|--------|--------------|---------|
| Por bairro | → | Por cidade ou estado |
| Por cidade | → | Por estado ou região |
| Recência (dias sem comprar) | → | Frequência mensal ou data última compra |
| Margem/lucro | → | Receita total ou ticket médio |
| Quantidade de clientes novos | → | Total de clientes ou pedidos no período |
| Por vendedor | → | Por região |
| Por categoria | → | Por produto (top 10) |

Sempre que usar um fallback, explique: "Não temos dados por bairro, mas posso mostrar por cidade."

## Situações Comuns

**Período não especificado:** Assuma últimos 6 meses e mencione isso.

**Ranking sem limite:** Use top 10 por padrão.

**Dados zerados ou ausentes:** Informe claramente ("3 clientes não têm pedidos nos últimos 30 dias").

**Empates em rankings:** Mencione se houver valores iguais.

## Formato da Resposta

⚠️ **Os dados detalhados já aparecem em uma tabela interativa.**

Seu texto deve ser um **resumo de 2-3 frases** bem formatado:

**Estrutura:**
1. **Visão geral** - total, média, ou principal métrica
2. **Destaque** - quem lidera ou anomalia relevante
3. **Próximo passo** - pergunta ou sugestão (opcional)

**Formatação Markdown:**
- Use **negrito** para números importantes e nomes de destaque
- Use listas `-` para múltiplos pontos
- Não use tabelas no texto (já temos a tabela interativa)
- Quebre em parágrafos curtos para facilitar leitura

**✅ BOM:**
> **5 cidades** com receita total de **R$ 85M** nos últimos 6 meses.
>
> **Pindamonhangaba** concentra 78% do volume, seguida por Ipúja (14%).
>
> Quer ver a evolução mensal?

**❌ RUIM:**
> Pindamonhangaba teve R$ 66,7M da Novelis, representando 78.5% do total. Ipúja teve R$ 11,6M da Valgroup, representando 13.7% do total. Curitiba teve R$ 3,2M da Magna...

## Valores
- Moeda: **R$ 1.234,56** ou **R$ 2,5M** (negrito para destaque)
- Percentuais: **78%** (não 0.78)
- Nunca exponha IDs técnicos
"""
)


# =============================================================================
# ACTION PROMPTS
# =============================================================================

CONFIRMACAO_AGENDAMENTO = PromptTemplateConfig(
    name="atendente/confirmacao-agendamento",
    category=PromptCategory.ACTION,
    description="Appointment confirmation prompt",
    required_variables=["data", "horario", "servico"],
    content="""Você está auxiliando um cliente a confirmar um agendamento.

**Dados do agendamento:**
- Data: {{ data }}
- Horário: {{ horario }}
- Serviço: {{ servico }}

Por favor, confirme os dados acima com o cliente antes de finalizar.
Pergunte se está tudo correto e se deseja prosseguir.
"""
)

ESCLARECIMENTO_PROMPT = PromptTemplateConfig(
    name="atendente/esclarecimento",
    category=PromptCategory.ACTION,
    description="Clarification request prompt",
    required_variables=["pergunta", "opcoes"],
    content="""O cliente fez uma pergunta que precisa de esclarecimento.

**Pergunta original:** {{ pergunta }}

**Possíveis interpretações:**
{{ opcoes }}

Peça gentilmente ao cliente para especificar qual das opções ele deseja.
"""
)


# =============================================================================
# RAG PROMPTS
# =============================================================================

RAG_QUERY_PROMPT = PromptTemplateConfig(
    name="rag/query",
    category=PromptCategory.RAG,
    description="RAG query answering prompt",
    required_variables=["context", "question"],
    content="""Você é um assistente da Vizu. Use os seguintes trechos de contexto para responder à pergunta.
O contexto é soberano. Se você não sabe a resposta com base no contexto,
apenas diga que não sabe. Não tente inventar uma resposta.

CONTEXTO:
{{ context }}

---

PERGUNTA:
{{ question }}

RESPOSTA:"""
)

RAG_HYBRID_PROMPT = PromptTemplateConfig(
    name="rag/hybrid",
    category=PromptCategory.RAG,
    description="RAG with hybrid search context",
    required_variables=["semantic_context", "keyword_context", "question"],
    optional_variables={"company_name": "Vizu"},
    content="""Você é um assistente da {{ company_name }}. Use o contexto abaixo para responder.

## CONTEXTO SEMÂNTICO (por relevância)
{{ semantic_context }}

## CONTEXTO POR PALAVRAS-CHAVE
{{ keyword_context }}

---

PERGUNTA: {{ question }}

Instruções:
1. Priorize informações que aparecem em ambos os contextos
2. Se houver contradição, mencione ambas as versões
3. Diga "não sei" se não encontrar resposta no contexto

RESPOSTA:"""
)


# =============================================================================
# ELICITATION PROMPTS
# =============================================================================

ELICITATION_OPTIONS_PROMPT = PromptTemplateConfig(
    name="elicitation/options",
    category=PromptCategory.ELICITATION,
    description="Present options to user",
    required_variables=["question", "options"],
    content="""{{ question }}

Por favor, escolha uma das opções abaixo:

{% for option in options %}
{{ loop.index }}. {{ option.label }}{% if option.description %} - {{ option.description }}{% endif %}

{% endfor %}
Digite o número da opção desejada:"""
)

ELICITATION_CONFIRMATION_PROMPT = PromptTemplateConfig(
    name="elicitation/confirmation",
    category=PromptCategory.ELICITATION,
    description="Confirmation request",
    required_variables=["action", "details"],
    content="""Você está prestes a realizar a seguinte ação:

**{{ action }}**

{{ details }}

Você confirma esta ação? (sim/não)"""
)

ELICITATION_FREEFORM_PROMPT = PromptTemplateConfig(
    name="elicitation/freeform",
    category=PromptCategory.ELICITATION,
    description="Freeform input request",
    required_variables=["question"],
    optional_variables={"hint": ""},
    content="""{{ question }}

{% if hint %}
Dica: {{ hint }}
{% endif %}

Por favor, digite sua resposta:"""
)


# =============================================================================
# ERROR PROMPTS
# =============================================================================

ERROR_TOOL_FAILED = PromptTemplateConfig(
    name="error/tool-failed",
    category=PromptCategory.ERROR,
    description="Tool execution failure message",
    required_variables=["tool_name"],
    optional_variables={"error_message": "Ocorreu um erro inesperado."},
    content="""Desculpe, houve um problema ao executar uma operação.

Erro: {{ error_message }}

Por favor, tente novamente ou entre em contato com o suporte se o problema persistir."""
)

ERROR_NOT_FOUND = PromptTemplateConfig(
    name="error/not-found",
    category=PromptCategory.ERROR,
    description="Resource not found message",
    required_variables=["resource_type"],
    content="""Desculpe, não foi possível encontrar {{ resource_type }}.

Por favor, verifique se as informações estão corretas e tente novamente."""
)



# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

# All built-in templates in a registry for easy access
BUILTIN_TEMPLATES: dict[str, PromptTemplateConfig] = {
    # System prompts
    ATENDENTE.name: ATENDENTE,
    # Action prompts
    CONFIRMACAO_AGENDAMENTO.name: CONFIRMACAO_AGENDAMENTO,
    ESCLARECIMENTO_PROMPT.name: ESCLARECIMENTO_PROMPT,
    # RAG prompts
    RAG_QUERY_PROMPT.name: RAG_QUERY_PROMPT,
    RAG_HYBRID_PROMPT.name: RAG_HYBRID_PROMPT,
    # Elicitation prompts
    ELICITATION_OPTIONS_PROMPT.name: ELICITATION_OPTIONS_PROMPT,
    ELICITATION_CONFIRMATION_PROMPT.name: ELICITATION_CONFIRMATION_PROMPT,
    ELICITATION_FREEFORM_PROMPT.name: ELICITATION_FREEFORM_PROMPT,
    # Error prompts
    ERROR_TOOL_FAILED.name: ERROR_TOOL_FAILED,
    ERROR_NOT_FOUND.name: ERROR_NOT_FOUND,
}



def get_builtin_template(name: str) -> PromptTemplateConfig | None:
    """Get a built-in template by name."""
    return BUILTIN_TEMPLATES.get(name)


def list_builtin_templates(category: PromptCategory | None = None) -> list[PromptTemplateConfig]:
    """List all built-in templates, optionally filtered by category."""
    templates = list(BUILTIN_TEMPLATES.values())
    if category:
        templates = [t for t in templates if t.category == category]
    return templates
