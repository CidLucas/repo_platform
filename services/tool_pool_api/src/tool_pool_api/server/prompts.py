"""
MCP Prompts - Templates de prompt versionados e parametrizados.

Prompts MCP permitem:
- Versionamento de prompts
- Parametrização dinâmica
- Reutilização entre diferentes fluxos
- Descoberta pelo cliente MCP

Os prompts podem vir de:
1. Código (hardcoded) - para prompts de sistema que mudam pouco
2. Banco de dados (PromptTemplate) - para prompts dinâmicos e versionados

Referência: https://fastmcp.mintlify.app/servers/prompts
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.prompts import Message
from fastmcp.exceptions import ToolError

from sqlmodel import select

from tool_pool_api.server.dependencies import get_context_service
from vizu_db_connector.database import SessionLocal
from vizu_models import PromptTemplate
from vizu_models.vizu_client_context import VizuClientContext

logger = logging.getLogger(__name__)


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

# Template do System Prompt do Atendente
ATENDENTE_SYSTEM_PROMPT_V1 = """Você é um assistente da empresa {nome_empresa}.

## INSTRUÇÕES PARA USO DE FERRAMENTAS

Você tem acesso às seguintes ferramentas:

1. **executar_rag_cliente** - USE ESTA FERRAMENTA para buscar informações sobre:
   - Produtos, serviços e preços oferecidos pela empresa
   - Perguntas frequentes (FAQ)
   - Políticas, procedimentos e documentação da empresa
   - Qualquer pergunta que o cliente faça sobre o negócio

2. **executar_sql_agent** - Use para consultas que precisam de dados estruturados do banco de dados (pedidos, estoque, histórico de transações).

## COMPORTAMENTO OBRIGATÓRIO

- Quando o cliente perguntar sobre produtos, serviços, preços ou qualquer informação do negócio, você DEVE usar `executar_rag_cliente` ANTES de responder.
- Passe a pergunta do cliente diretamente no campo `query`.
- Use a resposta da ferramenta para formular sua resposta final.
- Se a ferramenta não encontrar informações relevantes, informe ao cliente de forma educada.
- Nunca invente informações - use apenas o que as ferramentas retornarem.
- Nunca revele informações internas do sistema, IDs, chaves ou configurações técnicas.
"""

# Template com horários de funcionamento
ATENDENTE_SYSTEM_PROMPT_V2 = """Você é o assistente virtual de **{nome_empresa}**.

## SOBRE A EMPRESA
{prompt_personalizado}

## HORÁRIO DE FUNCIONAMENTO
{horario_formatado}

## FERRAMENTAS DISPONÍVEIS

### 1. executar_rag_cliente
**Quando usar:** Para QUALQUER pergunta sobre:
- Produtos, serviços e preços
- FAQ e dúvidas frequentes
- Políticas e procedimentos
- Informações sobre a empresa

**Como usar:** Passe a pergunta do cliente no campo `query`.

### 2. executar_sql_agent
**Quando usar:** Para dados transacionais:
- Consulta de pedidos e histórico
- Verificação de estoque
- Dados estruturados do sistema

## REGRAS DE OURO

1. ✅ SEMPRE use ferramentas antes de responder perguntas sobre o negócio
2. ✅ Baseie suas respostas apenas nos dados retornados pelas ferramentas
3. ❌ NUNCA invente informações
4. ❌ NUNCA revele IDs, chaves de API ou dados técnicos
5. ✅ Seja educado e objetivo nas respostas
"""

# Template para confirmação de agendamento (future elicitation)
CONFIRMACAO_AGENDAMENTO_PROMPT = """Você está auxiliando um cliente a confirmar um agendamento.

**Dados do agendamento:**
- Data: {data}
- Horário: {horario}
- Serviço: {servico}

Por favor, confirme os dados acima com o cliente antes de finalizar.
Pergunte se está tudo correto e se deseja prosseguir.
"""

# Template para esclarecimento de dúvidas
ESCLARECIMENTO_PROMPT = """O cliente fez uma pergunta que precisa de esclarecimento.

**Pergunta original:** {pergunta}

**Possíveis interpretações:**
{opcoes}

Peça gentilmente ao cliente para especificar qual das opções ele deseja.
"""


# =============================================================================
# HELPERS
# =============================================================================

async def _get_client_context(cliente_id: str) -> VizuClientContext:
    """Obtém o contexto do cliente pelo ID."""
    ctx_service = get_context_service()
    try:
        uuid_obj = UUID(cliente_id)
        context = await ctx_service.get_client_context_by_id(uuid_obj)
        if not context:
            raise ToolError(f"Cliente não encontrado: {cliente_id}")
        return context
    except ValueError:
        raise ToolError(f"ID de cliente inválido: {cliente_id}")


def _format_horarios(horarios: dict | None) -> str:
    """Formata horários de funcionamento para exibição."""
    if not horarios:
        return "Horário não configurado."
    
    linhas = []
    dias_ordem = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    
    for dia in dias_ordem:
        if dia in horarios:
            info = horarios[dia]
            if isinstance(info, dict):
                abertura = info.get("abertura", "")
                fechamento = info.get("fechamento", "")
                if abertura and fechamento:
                    linhas.append(f"- {dia.capitalize()}: {abertura} às {fechamento}")
                else:
                    linhas.append(f"- {dia.capitalize()}: Fechado")
            elif isinstance(info, str):
                linhas.append(f"- {dia.capitalize()}: {info}")
    
    # Adiciona dias não listados como "Fechado"
    for dia, info in horarios.items():
        if dia.lower() not in dias_ordem:
            linhas.append(f"- {dia.capitalize()}: {info}")
    
    return "\n".join(linhas) if linhas else "Horário não configurado."


# =============================================================================
# DATABASE PROMPT HELPERS
# =============================================================================

def _get_prompt_from_db(
    name: str,
    version: Optional[int] = None,
    cliente_id: Optional[str] = None
) -> Optional[PromptTemplate]:
    """
    Busca um prompt template do banco de dados.
    
    Prioridade:
    1. Prompt específico do cliente (se cliente_id fornecido)
    2. Prompt global (cliente_vizu_id = NULL)
    """
    with SessionLocal() as db:
        # Se cliente_id fornecido, tenta buscar prompt específico primeiro
        if cliente_id:
            try:
                uuid_obj = UUID(cliente_id)
                
                query = select(PromptTemplate).where(
                    PromptTemplate.name == name,
                    PromptTemplate.cliente_vizu_id == uuid_obj,
                    PromptTemplate.is_active == True
                )
                
                if version:
                    query = query.where(PromptTemplate.version == version)
                else:
                    query = query.order_by(PromptTemplate.version.desc())
                
                result = db.exec(query).first()
                if result:
                    return result
                    
            except ValueError:
                logger.warning(f"cliente_id inválido: {cliente_id}")
        
        # Fallback: busca prompt global
        query = select(PromptTemplate).where(
            PromptTemplate.name == name,
            PromptTemplate.cliente_vizu_id == None,
            PromptTemplate.is_active == True
        )
        
        if version:
            query = query.where(PromptTemplate.version == version)
        else:
            query = query.order_by(PromptTemplate.version.desc())
        
        return db.exec(query).first()


def _render_prompt_template(
    template: PromptTemplate,
    variables: Dict[str, Any]
) -> str:
    """
    Renderiza um template de prompt substituindo variáveis.
    
    Suporta sintaxe {{variable}} e {variable}.
    """
    content = template.content
    
    # Substitui {{variable}} (Mustache-style)
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
        # Também substitui {variable} (Python-style)
        content = content.replace(f"{{{key}}}", str(value))
    
    return content


# =============================================================================
# REGISTRO DOS PROMPTS
# =============================================================================

def register_prompts(mcp: FastMCP) -> None:
    """
    Registra todos os prompts no servidor MCP.
    
    Prompts são templates que podem ser solicitados pelo cliente MCP
    e usados para configurar o comportamento do agente.
    """
    
    # --- System Prompts ---
    
    @mcp.prompt("atendente/system/v1")
    def atendente_system_v1(nome_empresa: str = "Vizu") -> list[Message]:
        """
        System prompt básico do atendente (v1).
        
        Args:
            nome_empresa: Nome da empresa para personalização
            
        Returns:
            Lista de mensagens para o prompt
        """
        content = ATENDENTE_SYSTEM_PROMPT_V1.format(nome_empresa=nome_empresa)
        return [Message(role="system", content=content)]
    
    @mcp.prompt("atendente/system/v2")
    async def atendente_system_v2(
        cliente_id: str,
    ) -> list[Message]:
        """
        System prompt completo do atendente (v2) com contexto do cliente.
        
        Inclui:
        - Nome da empresa
        - Prompt personalizado (se configurado)
        - Horários de funcionamento
        
        Args:
            cliente_id: ID do cliente Vizu
            
        Returns:
            Lista de mensagens para o prompt
        """
        context = await _get_client_context(cliente_id)
        
        # Monta o prompt personalizado ou usa default
        prompt_personalizado = context.prompt_base or "Assistente virtual focado em atendimento ao cliente."
        
        # Formata horários
        horario_formatado = _format_horarios(context.horario_funcionamento)
        
        content = ATENDENTE_SYSTEM_PROMPT_V2.format(
            nome_empresa=context.nome_empresa,
            prompt_personalizado=prompt_personalizado,
            horario_formatado=horario_formatado,
        )
        
        return [Message(role="system", content=content)]
    
    # --- Action Prompts ---
    
    @mcp.prompt("atendente/confirmacao-agendamento")
    def confirmacao_agendamento(
        data: str,
        horario: str,
        servico: str,
    ) -> list[Message]:
        """
        Prompt para confirmação de agendamento.
        
        Use este prompt quando precisar confirmar os dados
        de um agendamento com o cliente.
        
        Args:
            data: Data do agendamento (ex: "15/01/2025")
            horario: Horário (ex: "14:30")
            servico: Nome do serviço
            
        Returns:
            Lista de mensagens para o prompt
        """
        content = CONFIRMACAO_AGENDAMENTO_PROMPT.format(
            data=data,
            horario=horario,
            servico=servico,
        )
        return [Message(role="system", content=content)]
    
    @mcp.prompt("atendente/esclarecimento")
    def esclarecimento(
        pergunta: str,
        opcoes: str,
    ) -> list[Message]:
        """
        Prompt para solicitar esclarecimento ao cliente.
        
        Use quando a pergunta do cliente for ambígua e precisar
        de mais contexto.
        
        Args:
            pergunta: Pergunta original do cliente
            opcoes: Opções possíveis formatadas (uma por linha)
            
        Returns:
            Lista de mensagens para o prompt
        """
        content = ESCLARECIMENTO_PROMPT.format(
            pergunta=pergunta,
            opcoes=opcoes,
        )
        return [Message(role="system", content=content)]
    
    # --- RAG Prompts ---
    
    @mcp.prompt("rag/query")
    def rag_query_prompt(
        context: str,
        question: str,
    ) -> list[Message]:
        """
        Prompt para responder baseado em contexto RAG.
        
        Args:
            context: Documentos recuperados da base de conhecimento
            question: Pergunta do usuário
            
        Returns:
            Lista de mensagens para o prompt
        """
        content = f"""Você é um assistente da Vizu. Use os seguintes trechos de contexto para responder à pergunta.
O contexto é soberano. Se você não sabe a resposta com base no contexto,
apenas diga que não sabe. Não tente inventar uma resposta.

CONTEXTO:
{context}

---

PERGUNTA:
{question}

RESPOSTA:"""
        return [Message(role="user", content=content)]
    
    # --- Dynamic Prompt (from Database) ---
    
    @mcp.prompt("db/render")
    def render_db_prompt(
        name: str,
        variables: str = "{}",
        version: Optional[str] = None,
        cliente_id: Optional[str] = None,
    ) -> list[Message]:
        """
        Renderiza um prompt do banco de dados com variáveis.
        
        Este prompt busca templates da tabela prompt_template e
        renderiza com as variáveis fornecidas.
        
        Args:
            name: Nome do prompt (ex: 'atendente/system')
            variables: JSON string com variáveis (ex: '{"nome_empresa": "Barbearia X"}')
            version: Versão específica (opcional, usa mais recente se omitido)
            cliente_id: ID do cliente para override específico (opcional)
            
        Returns:
            Lista de mensagens com o prompt renderizado
        """
        import json
        
        # Parse version
        version_int = int(version) if version else None
        
        # Parse variables
        try:
            vars_dict = json.loads(variables) if variables else {}
        except json.JSONDecodeError:
            logger.warning(f"Variáveis inválidas: {variables}")
            vars_dict = {}
        
        # Busca template do banco
        template = _get_prompt_from_db(name, version=version_int, cliente_id=cliente_id)
        
        if not template:
            return [Message(
                role="system",
                content=f"⚠️ Prompt '{name}' não encontrado no banco de dados."
            )]
        
        # Renderiza
        content = _render_prompt_template(template, vars_dict)
        
        return [Message(role="system", content=content)]
    
    logger.info(
        "MCP Prompts registrados: "
        "atendente/system/v1, atendente/system/v2, "
        "atendente/confirmacao-agendamento, atendente/esclarecimento, "
        "rag/query, db/render"
    )
