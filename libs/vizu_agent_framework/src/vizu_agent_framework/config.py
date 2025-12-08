"""
Agent configuration dataclass.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class AgentConfig:
    """
    Configuration for agent creation.

    Attributes:
        name: Unique agent identifier (e.g., "atendente_core", "vendas_agent")
        role: Human-readable role description for system prompts
        elicitation_strategy: Name of elicitation strategy to use
        enabled_tools: List of enabled tool names for this agent
        max_turns: Maximum conversation turns before forced end
        use_langfuse: Whether to enable Langfuse observability
        model: LLM model identifier (e.g., "openai:gpt-4o-mini", "ollama:llama3.2")
        system_prompt: Optional custom system prompt (uses template if None)
        redis_url: Redis URL for checkpointing
        mcp_url: MCP server URL for tool execution
        timeout_seconds: Tool execution timeout
        metadata: Additional metadata for tracing
    """

    name: str
    role: str
    elicitation_strategy: str = "support_triage"
    enabled_tools: List[str] = field(default_factory=list)
    max_turns: int = 20
    use_langfuse: bool = True
    model: str = "openai:gpt-4o-mini"
    system_prompt: Optional[str] = None
    redis_url: str = "redis://localhost:6379"
    mcp_url: str = "http://localhost:8000/mcp/v1"
    timeout_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.name:
            raise ValueError("Agent name is required")
        if not self.role:
            raise ValueError("Agent role is required")
        if self.max_turns < 1:
            raise ValueError("max_turns must be at least 1")

    @property
    def langfuse_session_tags(self) -> Dict[str, str]:
        """Get tags for Langfuse session."""
        return {
            "agent_name": self.name,
            "agent_role": self.role,
            "model": self.model,
            **{k: str(v) for k, v in self.metadata.items()},
        }

    def with_tools(self, tools: List[str]) -> "AgentConfig":
        """Return new config with updated tools."""
        return AgentConfig(
            name=self.name,
            role=self.role,
            elicitation_strategy=self.elicitation_strategy,
            enabled_tools=tools,
            max_turns=self.max_turns,
            use_langfuse=self.use_langfuse,
            model=self.model,
            system_prompt=self.system_prompt,
            redis_url=self.redis_url,
            mcp_url=self.mcp_url,
            timeout_seconds=self.timeout_seconds,
            metadata=self.metadata,
        )

    def with_metadata(self, **kwargs) -> "AgentConfig":
        """Return new config with additional metadata."""
        new_metadata = {**self.metadata, **kwargs}
        return AgentConfig(
            name=self.name,
            role=self.role,
            elicitation_strategy=self.elicitation_strategy,
            enabled_tools=self.enabled_tools,
            max_turns=self.max_turns,
            use_langfuse=self.use_langfuse,
            model=self.model,
            system_prompt=self.system_prompt,
            redis_url=self.redis_url,
            mcp_url=self.mcp_url,
            timeout_seconds=self.timeout_seconds,
            metadata=new_metadata,
        )


# Predefined configurations for common agent types
ATENDENTE_CONFIG = AgentConfig(
    name="atendente_core",
    role="Customer Support Agent",
    elicitation_strategy="support_triage",
    enabled_tools=[],  # Populated from client context
    max_turns=20,
)

VENDAS_CONFIG = AgentConfig(
    name="vendas_agent",
    role="Sales Representative",
    elicitation_strategy="sales_pipeline",
    enabled_tools=[],
    max_turns=15,
)

SUPPORT_CONFIG = AgentConfig(
    name="support_agent",
    role="Technical Support Specialist",
    elicitation_strategy="issue_classification",
    enabled_tools=[],
    max_turns=25,
)

APPOINTMENT_CONFIG = AgentConfig(
    name="appointment_agent",
    role="Appointment Scheduler",
    elicitation_strategy="scheduling",
    enabled_tools=["agendar_consulta"],
    max_turns=10,
)
