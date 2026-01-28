"""
Built-in prompt templates for Vizu services.

These templates serve as defaults when no database prompts are configured.
They can be overridden per-client in the database.
"""

from dataclasses import dataclass, field
from enum import Enum


class PromptCategory(str, Enum):
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




ATENDENTE_SYSTEM_V3 = PromptTemplateConfig(
    name="atendente/system/v3",
    category=PromptCategory.SYSTEM,
    description="Dynamic attendant prompt with tool list (v3 - multi-agent ready)",
    required_variables=["nome_empresa"],
    optional_variables={
        "prompt_personalizado": "Assistente virtual focado em atendimento ao cliente.",
        "horario_formatado": "Horário não configurado.",
        "tools_description": "",
        "agent_personality": "",
    },
    content="""Você é o assistente virtual de **{{ nome_empresa }}**.

## SOBRE A EMPRESA
{{ prompt_personalizado }}

{% if horario_formatado %}
## HORÁRIO DE FUNCIONAMENTO
{{ horario_formatado }}
{% endif %}

{% if tools_description %}
## FERRAMENTAS DISPONÍVEIS
{{ tools_description }}
{% endif %}

{% if agent_personality %}
## SUA PERSONALIDADE
{{ agent_personality }}
{% endif %}

## FORMATAÇÃO DE RESPOSTAS

Ao apresentar dados tabulares (resultados de consultas SQL, listas de produtos, pedidos, etc.):

1. **Tabelas compactas**: Mantenha o alinhamento entre os espaçadores (:|). Abrevie nomes de colunas quando necessário.
2. **Valores numéricos**: Formate valores monetários como "R$ 1.234,56". Use separador de milhares.
3. **Datas**: Use formato DD/MM/AAAA.
4. **IDs longos**: NUNCA mostre UUIDs ou IDs técnicos ao usuário. Omita ou substitua por números sequenciais (1, 2, 3...).
5. **Nomes longos**: Trunque nomes com mais de 30 caracteres usando "..." (ex: "COOPERATIVA DE TRAB..." ).
6. **Muitas linhas**: Para mais de 10 registros, mostre apenas os 10 primeiros/mais relevantes e indique o total.
7. **Resumos**: Sempre inclua totalizadores quando apropriado (soma, média, contagem).

**Exemplo de tabela bem formatada:**
| # | Cliente      |     Fornecedor     | Qtd | Valor(R$)|
|---|-------------:|-------------------:|----:|---------:|
| 1 | João Silva   | Cooperativa ABC... | 150 | 1.234,56 |
| 2 | Maria Santos | Associação XYZ...  |  89 |   987,65 |

## REGRAS DE OURO

1. ✅ SEMPRE use ferramentas quando disponíveis para buscar informações
2. ✅ Para perguntas sobre DADOS, SEMPRE chame a ferramenta SQL - mesmo se não tiver certeza sobre colunas
3. ✅ Baseie suas respostas apenas nos dados retornados pelas ferramentas
4. ❌ NUNCA invente informações
5. ❌ NUNCA assuma que colunas/dados não existem sem tentar a ferramenta primeiro
6. ❌ NUNCA revele IDs, chaves de API ou dados técnicos internos
7. ✅ Seja educado e objetivo nas respostas
8. ✅ Formate tabelas de forma limpa e legível
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
    ATENDENTE_SYSTEM_V1.name: ATENDENTE_SYSTEM_V1,
    ATENDENTE_SYSTEM_V2.name: ATENDENTE_SYSTEM_V2,
    ATENDENTE_SYSTEM_V3.name: ATENDENTE_SYSTEM_V3,
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



def get_builtin_template(name: str) -> PromptTemplateConfig | None:
    """Get a built-in template by name."""
    return BUILTIN_TEMPLATES.get(name)


def list_builtin_templates(category: PromptCategory | None = None) -> list[PromptTemplateConfig]:
    """List all built-in templates, optionally filtered by category."""
    templates = list(BUILTIN_TEMPLATES.values())
    if category:
        templates = [t for t in templates if t.category == category]
    return templates
