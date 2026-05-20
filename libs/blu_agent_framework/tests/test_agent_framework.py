"""
Tests for blu_agent_framework components.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from blu_agent_framework import (
    AgentBuilder,
    AgentConfig,
    AgentState,
    NodeRegistry,
    RedisCheckpointer,
    create_initial_state,
    elicit_node,
    end_node,
    execute_tool_node,
    init_node,
    route_from_elicit,
    route_from_tool,
    should_continue,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_config() -> AgentConfig:
    """Sample agent configuration."""
    return AgentConfig(
        name="test_agent",
        role="Test Agent",
        elicitation_strategy="test_strategy",
        enabled_tools=["tool_a", "tool_b"],
        max_turns=10,
        use_langfuse=False,
        model="test:model",
    )


@pytest.fixture
def sample_state() -> AgentState:
    """Sample agent state."""
    return create_initial_state(
        session_id="session-123",
        client_id="client-456",
        messages=[HumanMessage(content="Hello")],
        system_prompt="You are a test agent.",
        agent_name="test_agent",
        max_turns=10,
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


# ============================================================================
# AgentConfig Tests
# ============================================================================


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_create_config(self, sample_config):
        """Test creating configuration."""
        assert sample_config.name == "test_agent"
        assert sample_config.role == "Test Agent"
        assert sample_config.max_turns == 10
        assert len(sample_config.enabled_tools) == 2

    def test_config_validation_name_required(self):
        """Test that name is required."""
        with pytest.raises(ValueError, match="name"):
            AgentConfig(name="", role="Test")

    def test_config_validation_role_required(self):
        """Test that role is required."""
        with pytest.raises(ValueError, match="role"):
            AgentConfig(name="test", role="")

    def test_config_validation_max_turns(self):
        """Test max_turns validation."""
        with pytest.raises(ValueError, match="max_turns"):
            AgentConfig(name="test", role="Test", max_turns=0)

    def test_with_tools(self, sample_config):
        """Test with_tools returns new config."""
        new_config = sample_config.with_tools(["tool_c"])
        assert new_config.enabled_tools == ["tool_c"]
        assert sample_config.enabled_tools == ["tool_a", "tool_b"]

    def test_with_metadata(self, sample_config):
        """Test with_metadata returns new config."""
        new_config = sample_config.with_metadata(key="value")
        assert new_config.metadata["key"] == "value"
        assert "key" not in sample_config.metadata

    def test_langfuse_session_tags(self, sample_config):
        """Test langfuse session tags generation."""
        tags = sample_config.langfuse_session_tags
        assert tags["agent_name"] == "test_agent"
        assert tags["model"] == "test:model"


# ============================================================================
# AgentState Tests
# ============================================================================


class TestAgentState:
    """Tests for AgentState."""

    def test_create_initial_state(self):
        """Test creating initial state."""
        state = create_initial_state(
            session_id="sess-1",
            client_id="client-1",
        )

        assert state["session_id"] == "sess-1"
        assert state["client_id"] == "client-1"
        assert state["turn_count"] == 0
        assert state["ended"] is False

    def test_initial_state_with_messages(self):
        """Test initial state with messages."""
        messages = [HumanMessage(content="Hi")]
        state = create_initial_state(
            session_id="sess-1",
            client_id="client-1",
            messages=messages,
        )

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Hi"

    def test_initial_state_with_client_context(self):
        """Test initial state with client context."""
        context = {"nome_empresa": "Test Co", "tier": "SME"}
        state = create_initial_state(
            session_id="sess-1",
            client_id="client-1",
            client_context=context,
        )

        assert state["nome_empresa"] == "Test Co"
        assert state["tier"] == "SME"


# ============================================================================
# Node Tests
# ============================================================================


class TestNodes:
    """Tests for graph nodes."""

    @pytest.mark.asyncio
    async def test_init_node_increments_turn(self, sample_state):
        """Test init node increments turn count."""
        result = await init_node(sample_state)
        assert result["turn_count"] == 1

    @pytest.mark.asyncio
    async def test_init_node_ends_on_max_turns(self):
        """Test init node ends when max turns exceeded."""
        state = create_initial_state(
            session_id="sess-1",
            client_id="client-1",
            max_turns=5,
        )
        state["turn_count"] = 5  # Already at max

        result = await init_node(state)
        assert result["ended"] is True
        assert "exceeded" in result["end_reason"]

    @pytest.mark.asyncio
    async def test_elicit_node_processes_response(self, sample_state):
        """Test elicit node processes pending elicitation response."""
        sample_state["pending_elicitation"] = {"type": "confirmation"}
        sample_state["elicitation_response"] = "yes"

        result = await elicit_node(sample_state)

        assert result["pending_elicitation"] is None
        assert result["elicitation_response"] is None
        assert len(result["elicitation_history"]) == 1

    @pytest.mark.asyncio
    async def test_elicit_node_waits_for_response(self, sample_state):
        """Test elicit node waits when pending but no response."""
        sample_state["pending_elicitation"] = {"type": "confirmation"}
        sample_state["elicitation_response"] = None

        result = await elicit_node(sample_state)

        # Should return empty dict (no changes)
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_tool_node_clears_fields(self, sample_state):
        """Placeholder execute_tool_node clears tool fields; validation is in AgentBuilder."""
        sample_state["tool_to_execute"] = "some_tool"
        sample_state["tool_args"] = {"q": "test"}

        result = await execute_tool_node(sample_state)

        assert result["tool_to_execute"] is None
        assert result["tool_args"] is None

    @pytest.mark.asyncio
    async def test_end_node_sets_ended(self, sample_state):
        """Test end node sets ended flag."""
        result = await end_node(sample_state)

        assert result["ended"] is True
        assert "end_reason" in result


# ============================================================================
# Routing Tests
# ============================================================================


class TestRouting:
    """Tests for routing functions."""

    def test_route_from_elicit_to_end(self, sample_state):
        """Test routing to end when ended flag set."""
        sample_state["ended"] = True
        assert route_from_elicit(sample_state) == "end"

    def test_route_from_elicit_needs_elicitation(self, sample_state):
        """Test routing when elicitation pending."""
        sample_state["pending_elicitation"] = {"type": "confirmation"}
        assert route_from_elicit(sample_state) == "needs_elicitation"

    def test_route_from_elicit_needs_tool(self, sample_state):
        """Test routing when tool execution needed."""
        sample_state["tool_to_execute"] = "some_tool"
        assert route_from_elicit(sample_state) == "needs_tool"

    def test_route_from_elicit_ready_to_respond(self, sample_state):
        """Test routing to respond by default."""
        assert route_from_elicit(sample_state) == "ready_to_respond"

    def test_route_from_tool_success(self, sample_state):
        """Test routing on tool success."""
        assert route_from_tool(sample_state) == "success"

    def test_route_from_tool_error(self, sample_state):
        """Test routing on tool error."""
        sample_state["error"] = "Something went wrong"
        assert route_from_tool(sample_state) == "error"

    def test_should_continue_true(self, sample_state):
        """Test should_continue returns continue."""
        assert should_continue(sample_state) == "continue"

    def test_should_continue_ended(self, sample_state):
        """Test should_continue returns end when ended."""
        sample_state["ended"] = True
        assert should_continue(sample_state) == "end"

    def test_should_continue_max_turns(self, sample_state):
        """Test should_continue returns end on max turns."""
        sample_state["turn_count"] = 10
        sample_state["max_turns"] = 10
        assert should_continue(sample_state) == "end"

    def test_should_continue_too_many_errors(self, sample_state):
        """Test should_continue returns end on many errors."""
        sample_state["errors"] = ["e1", "e2", "e3"]
        assert should_continue(sample_state) == "end"


# ============================================================================
# NodeRegistry Tests
# ============================================================================


class TestNodeRegistry:
    """Tests for NodeRegistry."""

    def test_get_builtin_node(self):
        """Test getting built-in node."""
        node = NodeRegistry.get("init")
        assert node is not None
        assert node == init_node

    def test_get_missing_node(self):
        """Test getting non-existent node."""
        node = NodeRegistry.get("nonexistent")
        assert node is None

    def test_register_custom_node(self):
        """Test registering custom node."""

        @NodeRegistry.register("custom_test")
        async def custom_node(state):
            return {"custom": True}

        node = NodeRegistry.get("custom_test")
        assert node is not None

    def test_list_nodes(self):
        """Test listing registered nodes."""
        nodes = NodeRegistry.list_nodes()
        assert "init" in nodes
        assert "elicit" in nodes
        assert "respond" in nodes


# ============================================================================
# ToolResult Tests
# ============================================================================


class TestToolResult:
    """Tests for the ToolResult dataclass (concrete, no network required)."""

    def test_success_result(self):
        from blu_agent_framework.mcp_executor import ToolResult

        r = ToolResult(tool_name="my_tool", success=True, result={"rows": 3})
        assert r.success is True
        assert r.error is None
        assert r.metadata == {}

    def test_failure_result(self):
        from blu_agent_framework.mcp_executor import ToolResult

        r = ToolResult(tool_name="my_tool", success=False, error="timeout")
        assert r.success is False
        assert r.error == "timeout"

    def test_to_dict_roundtrip(self):
        from blu_agent_framework.mcp_executor import ToolResult

        r = ToolResult(
            tool_name="t",
            success=True,
            result="ok",
            execution_time_ms=12.5,
        )
        d = r.to_dict()
        assert d["tool_name"] == "t"
        assert d["success"] is True
        assert d["execution_time_ms"] == 12.5

    def test_to_dict_is_json_serialisable(self):
        import json

        from blu_agent_framework.mcp_executor import ToolResult

        r = ToolResult(tool_name="t", success=True, result={"k": 1})
        json.dumps(r.to_dict())  # must not raise


# ============================================================================
# AgentBuilder Tests
# ============================================================================


class TestAgentBuilder:
    """Tests for AgentBuilder."""

    def test_create_builder(self, sample_config):
        """Test creating builder."""
        builder = AgentBuilder(sample_config)
        assert builder.config == sample_config

    def test_add_node(self, sample_config):
        """Test adding node to builder."""
        builder = AgentBuilder(sample_config)
        builder.add_node("custom", "init")

        assert "custom" in builder._nodes

    def test_add_edge(self, sample_config):
        """Test adding edge to builder."""
        builder = AgentBuilder(sample_config)
        builder.add_edge("a", "b")

        assert len(builder._edges) == 1
        assert builder._edges[0].from_node == "a"
        assert builder._edges[0].to_node == "b"

    def test_add_conditional_edge(self, sample_config):
        """Test adding conditional edge."""
        builder = AgentBuilder(sample_config)

        def router(state):
            return "a"

        builder.add_conditional_edge("start", router, {"a": "node_a", "b": "node_b"})

        assert len(builder._edges) == 1
        assert builder._edges[0].is_conditional is True

    def test_use_default_graph(self, sample_config):
        """Test using default graph structure."""
        builder = AgentBuilder(sample_config)
        builder.use_default_graph()

        assert "init" in builder._nodes
        assert "elicit" in builder._nodes
        assert "execute_tool" in builder._nodes
        assert "respond" in builder._nodes
        assert "end" in builder._nodes

    def test_build_compiles_graph(self, sample_config):
        """Test build returns compiled graph."""
        builder = AgentBuilder(sample_config)
        builder.use_default_graph()
        graph = builder.build()

        assert graph is not None

    def test_fluent_api(self, sample_config, mock_redis):
        """Test fluent API chaining."""
        checkpointer = RedisCheckpointer(mock_redis)
        executor = MagicMock()  # any object — builder just stores the reference

        builder = (
            AgentBuilder(sample_config)
            .with_checkpointer(checkpointer)
            .with_mcp(executor)
            .with_langfuse(session_id="sess", user_id="user")
            .use_default_graph()
        )

        assert builder.checkpointer == checkpointer
        assert builder.mcp_executor == executor
        assert builder._langfuse_session_id == "sess"


# ============================================================================
# RedisCheckpointer Tests
# ============================================================================


class TestRedisCheckpointer:
    """Tests for RedisCheckpointer."""

    def test_make_key(self, mock_redis):
        """Test key generation."""
        checkpointer = RedisCheckpointer(mock_redis)

        key = checkpointer._make_key("thread-1")
        assert key == "blu:checkpoint:thread-1"

        key = checkpointer._make_key("thread-1", "ns-1")
        assert key == "blu:checkpoint:thread-1:ns-1"

    @pytest.mark.asyncio
    async def test_put_and_get(self, mock_redis):
        """Test saving and retrieving checkpoint."""
        import json

        from langchain_core.runnables import RunnableConfig
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata

        checkpointer = RedisCheckpointer(mock_redis)

        config = RunnableConfig(configurable={"thread_id": "thread-1"})
        checkpoint = Checkpoint(
            v=1,
            ts="2025-01-01T00:00:00",
            id="cp-1",
            channel_values={"messages": []},
            channel_versions={},
            versions_seen={},
        )
        metadata = CheckpointMetadata(source="test", step=1, writes={}, parents={})

        # Put checkpoint
        await checkpointer.aput(config, checkpoint, metadata)
        mock_redis.set.assert_called_once()

        # Setup get response
        mock_redis.get = AsyncMock(
            return_value=json.dumps(
                {
                    "v": 1,
                    "ts": "2025-01-01T00:00:00",
                    "id": "cp-1",
                    "channel_values": {"messages": []},
                    "channel_versions": {},
                    "versions_seen": {},
                }
            )
        )

        # Get checkpoint
        result = await checkpointer.aget_tuple(config)
        assert result is not None
        assert result.checkpoint["id"] == "cp-1"


# ============================================================================
# Fan-out (Send-based) Tests
# ============================================================================


class TestFanOut:
    """Tests for Send-based fan-out tool execution."""

    def test_fan_out_no_pending_calls(self, sample_state):
        """Test fan_out_tool_calls returns empty when no pending tool calls."""
        from blu_agent_framework.nodes import fan_out_tool_calls

        sample_state["pending_tool_calls"] = []
        result = fan_out_tool_calls(sample_state)
        assert result == []

    def test_fan_out_dispatches_sends(self, sample_state):
        """Test fan_out_tool_calls returns Send objects for each pending call."""
        from langgraph.types import Send

        from blu_agent_framework.nodes import fan_out_tool_calls

        sample_state["pending_tool_calls"] = [
            {"name": "tool_a", "id": "call-1", "args": {"q": "test1"}},
            {"name": "tool_b", "id": "call-2", "args": {"q": "test2"}},
        ]

        result = fan_out_tool_calls(sample_state)

        assert len(result) == 2
        assert all(isinstance(s, Send) for s in result)
        # Verify Send targets
        assert result[0].node == "execute_single_tool"
        assert result[1].node == "execute_single_tool"
        # Verify each Send has the correct tool_call
        assert result[0].arg["tool_call"]["name"] == "tool_a"
        assert result[1].arg["tool_call"]["name"] == "tool_b"

    def test_fan_out_passes_context(self, sample_state):
        """Test fan_out_tool_calls passes session context in Send state."""
        from blu_agent_framework.nodes import fan_out_tool_calls

        sample_state["pending_tool_calls"] = [
            {"name": "tool_a", "id": "call-1", "args": {}},
        ]
        sample_state["client_id"] = "client-123"
        sample_state["session_id"] = "session-456"
        sample_state["channel"] = "web"

        result = fan_out_tool_calls(sample_state)

        assert len(result) == 1
        send_state = result[0].arg
        assert send_state["client_id"] == "client-123"
        assert send_state["session_id"] == "session-456"
        assert send_state["channel"] == "web"

    @pytest.mark.asyncio
    async def test_execute_single_tool_node_placeholder(self, sample_state):
        """Test execute_single_tool_node returns error when not wired."""
        from blu_agent_framework.nodes import execute_single_tool_node

        state = {"tool_call": {"name": "test_tool", "id": "call-1", "args": {}}}
        result = await execute_single_tool_node(state)

        assert "tool_results" in result
        assert result["tool_results"][0]["tool_name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_collect_tool_results_node(self):
        """Test collect_tool_results_node clears pending and sets last result."""
        from blu_agent_framework.nodes import collect_tool_results_node

        state = create_initial_state(
            session_id="sess-1",
            client_id="client-1",
        )
        state["tool_results"] = [
            {"tool_name": "tool_a", "result": "A", "success": True},
            {"tool_name": "tool_b", "result": "B", "success": True},
        ]
        state["pending_tool_calls"] = [{"name": "tool_a"}, {"name": "tool_b"}]

        result = await collect_tool_results_node(state)

        assert result["pending_tool_calls"] == []
        assert result["last_tool_result"]["tool_name"] == "tool_b"

    def test_tool_call_send_state_import(self):
        """Test ToolCallSendState is importable."""
        from blu_agent_framework import ToolCallSendState

        assert ToolCallSendState is not None

    def test_builder_use_fanout_graph(self, sample_config):
        """Test AgentBuilder.use_fanout_graph builds valid graph."""
        builder = AgentBuilder(sample_config)
        builder.use_fanout_graph()

        assert "init" in builder._nodes
        assert "execute_single_tool" in builder._nodes
        assert "collect_tool_results" in builder._nodes
        assert "respond" in builder._nodes
        assert "end" in builder._nodes
        assert builder._use_fanout is True

    def test_builder_fanout_compiles(self, sample_config):
        """Test AgentBuilder.use_fanout_graph compiles successfully."""
        builder = AgentBuilder(sample_config)
        builder.use_fanout_graph()
        graph = builder.build()

        assert graph is not None


# ============================================================================
# Phase 2: Intent Routing State Fields
# ============================================================================


# ============================================================================
# Phase 3: classify_intent_node
# ============================================================================


class TestClassifyIntentNode:
    """Tests for classify_intent_node."""

    @pytest.fixture
    def base_state(self):
        return create_initial_state(session_id="s", client_id="c")

    def _with_last_message(self, state, msg):
        state["messages"] = [msg]
        return state

    # --- HumanMessage guard ---

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_messages(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        result = await classify_intent_node(base_state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_on_tool_message(self, base_state):
        from langchain_core.messages import ToolMessage

        from blu_agent_framework.nodes import classify_intent_node

        base_state["messages"] = [ToolMessage(content="result", tool_call_id="x")]
        result = await classify_intent_node(base_state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_on_ai_message(self, base_state):
        from langchain_core.messages import AIMessage

        from blu_agent_framework.nodes import classify_intent_node

        base_state["messages"] = [AIMessage(content="here is the answer")]
        result = await classify_intent_node(base_state)
        assert result == {}

    # --- PT-BR keyword detection ---

    @pytest.mark.asyncio
    async def test_rfq_keywords_set_rfq_domain(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        base_state["messages"] = [HumanMessage(content="Preciso fazer uma cotação com meus fornecedores")]
        result = await classify_intent_node(base_state)

        assert result["current_domain"] == "rfq"
        assert "rfq" in result["intent_tags"]
        assert result["current_intent"].startswith("Preciso")

    @pytest.mark.asyncio
    async def test_analytics_keywords_set_analytics_domain(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        base_state["messages"] = [HumanMessage(content="Gere um relatório de análise de vendas")]
        result = await classify_intent_node(base_state)

        assert result["current_domain"] == "analytics"
        assert any(t in result["intent_tags"] for t in ("analytics", "sql", "csv"))

    @pytest.mark.asyncio
    async def test_documents_keywords_set_documents_domain(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        base_state["messages"] = [HumanMessage(content="Extraia os dados desse contrato PDF")]
        result = await classify_intent_node(base_state)

        assert result["current_domain"] == "documents"

    @pytest.mark.asyncio
    async def test_config_keywords_set_config_domain(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        base_state["messages"] = [HumanMessage(content="Como configurar o agente?")]
        result = await classify_intent_node(base_state)

        assert result["current_domain"] == "config"
        assert "config" in result["intent_tags"]

    # --- No-match preserves previous ---

    @pytest.mark.asyncio
    async def test_no_keywords_returns_empty_dict(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        base_state["current_domain"] = "rfq"
        base_state["intent_tags"] = ["rfq"]
        base_state["messages"] = [HumanMessage(content="Oi, tudo bem?")]
        result = await classify_intent_node(base_state)

        assert result == {}  # previous domain preserved by returning {}

    # --- Intent text is capped ---

    @pytest.mark.asyncio
    async def test_intent_text_capped_at_200_chars(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        long_text = "cotação " + "x" * 300
        base_state["messages"] = [HumanMessage(content=long_text)]
        result = await classify_intent_node(base_state)

        assert len(result["current_intent"]) <= 200

    # --- Multi-tag messages ---

    @pytest.mark.asyncio
    async def test_mixed_intent_produces_multiple_tags(self, base_state):
        from blu_agent_framework.nodes import classify_intent_node

        base_state["messages"] = [HumanMessage(content="Análise SQL das cotações rfq dos fornecedores")]
        result = await classify_intent_node(base_state)

        # Should pick up both rfq and analytics-family tags
        assert len(result["intent_tags"]) >= 2


# ============================================================================
# Phase 3: graph structure tests
# ============================================================================


class TestGraphWithClassifyIntent:
    """Verify classify_intent and context_enrichment are wired into both graphs."""

    def test_default_graph_has_classify_intent_node(self, sample_config):
        builder = AgentBuilder(sample_config)
        builder.use_default_graph()
        assert "classify_intent" in builder._nodes
        assert "context_enrichment" in builder._nodes

    def test_fanout_graph_has_classify_intent_node(self, sample_config):
        builder = AgentBuilder(sample_config)
        builder.use_fanout_graph()
        assert "classify_intent" in builder._nodes
        assert "context_enrichment" in builder._nodes

    def test_default_graph_compiles_with_new_nodes(self, sample_config):
        builder = AgentBuilder(sample_config)
        builder.use_default_graph()
        graph = builder.build()
        assert graph is not None

    def test_fanout_graph_compiles_with_new_nodes(self, sample_config):
        builder = AgentBuilder(sample_config)
        builder.use_fanout_graph()
        graph = builder.build()
        assert graph is not None

    def test_classify_intent_registered_in_node_registry(self):
        node = NodeRegistry.get("classify_intent")
        assert node is not None


class TestIntentRoutingStateFields:
    """Tests for the new intent-routing fields added to AgentState."""

    def test_initial_state_has_intent_fields(self):
        state = create_initial_state(session_id="s", client_id="c")
        assert state["current_intent"] is None
        assert state["current_domain"] is None
        assert state["intent_tags"] == []
        assert state["loaded_context_keys"] == []

    def test_intent_tags_is_list_not_set(self):
        """list[str] is JSON-serializable; set[str] would break Redis checkpointing."""
        state = create_initial_state(session_id="s", client_id="c")
        import json
        # must not raise
        json.dumps({"intent_tags": state["intent_tags"]})

    def test_loaded_context_keys_is_list_not_set(self):
        state = create_initial_state(session_id="s", client_id="c")
        import json
        json.dumps({"loaded_context_keys": state["loaded_context_keys"]})


class TestContextEnrichmentNode:
    """Tests for the extended context_enrichment_node."""

    @pytest.mark.asyncio
    async def test_computes_loaded_context_keys_from_non_empty_values(self):
        from blu_agent_framework.nodes import context_enrichment_node

        state = create_initial_state(
            session_id="s",
            client_id="c",
            client_context={
                "nome_empresa": "Acme",
                "cnpj": "",           # empty string → not loaded
                "tier": "SME",
                "segmento": None,     # None → not loaded
                "logo_url": [],       # empty list → not loaded
                "extra": {},          # empty dict → not loaded
                "site": "acme.com",
            },
        )
        result = await context_enrichment_node(state)
        keys = result["loaded_context_keys"]

        assert "nome_empresa" in keys
        assert "tier" in keys
        assert "site" in keys
        # falsy/empty values must be excluded
        assert "cnpj" not in keys
        assert "segmento" not in keys
        assert "logo_url" not in keys
        assert "extra" not in keys

    @pytest.mark.asyncio
    async def test_loaded_context_keys_is_list(self):
        from blu_agent_framework.nodes import context_enrichment_node

        state = create_initial_state(
            session_id="s",
            client_id="c",
            client_context={"nome_empresa": "Test"},
        )
        result = await context_enrichment_node(state)
        assert isinstance(result["loaded_context_keys"], list)

    @pytest.mark.asyncio
    async def test_empty_client_context_gives_empty_keys(self):
        from blu_agent_framework.nodes import context_enrichment_node

        state = create_initial_state(session_id="s", client_id="c")
        result = await context_enrichment_node(state)
        assert result["loaded_context_keys"] == []

    @pytest.mark.asyncio
    async def test_still_sets_metadata_flags(self):
        from blu_agent_framework.nodes import context_enrichment_node

        state = create_initial_state(
            session_id="s",
            client_id="c",
            client_context={
                "tier": "SME",
                "nome_empresa": "Co",
                "available_tools": {
                    "enabled_tool_names": ["executar_rag_cliente", "executar_sql_agent"]
                },
            },
        )
        result = await context_enrichment_node(state)
        meta = result["metadata"]
        assert meta["has_rag"] is True
        assert meta["has_sql"] is True
        assert meta["tier"] == "SME"

    @pytest.mark.asyncio
    async def test_loaded_context_keys_json_serialisable(self):
        """Keys must survive Redis JSON serialisation."""
        import json

        from blu_agent_framework.nodes import context_enrichment_node

        state = create_initial_state(
            session_id="s",
            client_id="c",
            client_context={"nome_empresa": "Co", "tier": "BASIC"},
        )
        result = await context_enrichment_node(state)
        json.dumps(result["loaded_context_keys"])  # must not raise


# ============================================================================
# Phase 3 — Frontdesk Specialist Tests
# ============================================================================


class TestFrontdeskRegistry:
    """Verify frontdesk entry in AgentTypeRegistry."""

    def test_frontdesk_registered(self):
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("frontdesk")
        assert cfg is not None

    def test_frontdesk_slug(self):
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("frontdesk")
        assert cfg.slug == "frontdesk"

    def test_frontdesk_uses_prompt_name(self):
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("frontdesk")
        assert cfg.prompt_name == "agents/frontdesk"
        assert cfg.fragments == []

    def test_frontdesk_enabled_tools(self):
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("frontdesk")
        assert "executar_rag_cliente" in cfg.enabled_tools
        assert "execute_sql" in cfg.enabled_tools

    def test_frontdesk_tier(self):
        from blu_agent_framework.registry import AgentTypeRegistry
        from blu_tool_registry.tool_metadata import TierLevel

        cfg = AgentTypeRegistry.get("frontdesk")
        assert cfg.tier_required == TierLevel.BASIC

    def test_frontdesk_tags(self):
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("frontdesk")
        assert "frontdesk" in cfg.tags
        assert "rag" in cfg.tags
        assert "sql" in cfg.tags

    def test_frontdesk_visible_to_basic_tier(self):
        from blu_agent_framework.registry import AgentTypeRegistry

        configs = AgentTypeRegistry.for_tier("BASIC")
        slugs = [c.slug for c in configs]
        assert "frontdesk" in slugs


class TestSimpleSqlQuerySkill:
    """Verify simple_sql_query entry in SKILL_REGISTRY."""

    def test_skill_registered(self):
        from blu_agent_framework.skills import SKILL_REGISTRY

        assert "simple_sql_query" in SKILL_REGISTRY

    def test_skill_prompt_name(self):
        from blu_agent_framework.skills import SKILL_REGISTRY

        skill = SKILL_REGISTRY["simple_sql_query"]
        assert skill.prompt_name == "skill:simple_sql_query:system"

    def test_skill_required_tools(self):
        from blu_agent_framework.skills import SKILL_REGISTRY

        skill = SKILL_REGISTRY["simple_sql_query"]
        assert skill.required_tool_names == ["execute_sql"]

    def test_skill_max_turns(self):
        from blu_agent_framework.skills import SKILL_REGISTRY

        skill = SKILL_REGISTRY["simple_sql_query"]
        assert skill.max_turns == 2

    def test_skill_on_max_turns(self):
        from blu_agent_framework.skills import SKILL_REGISTRY

        skill = SKILL_REGISTRY["simple_sql_query"]
        assert skill.on_max_turns == "return_partial"

    def test_skill_tags_intersect_frontdesk(self):
        from blu_agent_framework.registry import AgentTypeRegistry
        from blu_agent_framework.skills import SKILL_REGISTRY

        skill = SKILL_REGISTRY["simple_sql_query"]
        cfg = AgentTypeRegistry.get("frontdesk")
        assert set(skill.tags) & set(cfg.tags), "skill tags must intersect frontdesk tags"


class TestFrontdeskPromptTemplates:
    """Verify frontdesk builtin prompt templates exist and are registered."""

    def test_fragment_frontdesk_routing_in_builtins(self):
        from blu_prompt_management.templates import BUILTIN_TEMPLATES

        assert "specialists/frontdesk-routing" in BUILTIN_TEMPLATES

    def test_agents_frontdesk_in_builtins(self):
        from blu_prompt_management.templates import BUILTIN_TEMPLATES

        assert "agents/frontdesk" in BUILTIN_TEMPLATES

    def test_agents_frontdesk_has_required_variables(self):
        from blu_prompt_management.templates import BUILTIN_TEMPLATES

        tpl = BUILTIN_TEMPLATES["agents/frontdesk"]
        assert "nome_empresa" in tpl.required_variables

    def test_fragment_frontdesk_routing_langfuse_managed(self):
        from blu_prompt_management.dynamic_builder import _is_langfuse_managed

        assert _is_langfuse_managed("specialists/frontdesk-routing")

    def test_agents_frontdesk_langfuse_managed(self):
        from blu_prompt_management.dynamic_builder import _is_langfuse_managed

        assert _is_langfuse_managed("agents/frontdesk")


# ============================================================================
# Phase 4 — Universal Specialist Subgraph Tests
# ============================================================================


class TestUseSpecialistGraph:
    """Verify use_specialist_graph() builds and compiles correctly."""

    @pytest.fixture
    def specialist_config(self):
        return AgentConfig(
            name="data-analyst",
            role="data-analyst",
            enabled_tools=["execute_sql"],
            max_turns=4,
            use_langfuse=False,
            model="test:model",
        )

    def test_specialist_graph_nodes(self, specialist_config):
        """Nodes init, classify_skill_intent, run_skill, respond, end are wired."""
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("data-analyst")
        assert cfg is not None

        builder = AgentBuilder(specialist_config)
        builder.use_specialist_graph(cfg)

        assert "init" in builder._nodes
        assert "classify_skill_intent" in builder._nodes
        assert "run_skill" in builder._nodes
        assert "respond" in builder._nodes
        assert "end" in builder._nodes

    def test_specialist_graph_compiles(self, specialist_config):
        """use_specialist_graph() graph must compile without error."""
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("data-analyst")
        builder = AgentBuilder(specialist_config)
        builder.use_specialist_graph(cfg)
        graph = builder.build()

        assert graph is not None

    def test_classify_skill_intent_in_registry(self):
        """classify_skill_intent node is registered in NodeRegistry."""
        node = NodeRegistry.get("classify_skill_intent")
        assert node is not None

    def test_specialist_graph_topology_flag(self, specialist_config):
        """Builder stores specialist cfg when use_specialist_graph() is called."""
        from blu_agent_framework.registry import AgentTypeRegistry

        cfg = AgentTypeRegistry.get("data-analyst")
        builder = AgentBuilder(specialist_config)
        builder.use_specialist_graph(cfg)

        assert builder._specialist_cfg is cfg


class TestClassifySkillIntentTemplate:
    """Verify specialists/classify-skill-intent builtin template and Langfuse management."""

    def test_classify_skill_intent_in_builtins(self):
        from blu_prompt_management.templates import BUILTIN_TEMPLATES

        assert "specialists/classify-skill-intent" in BUILTIN_TEMPLATES

    def test_classify_skill_intent_langfuse_managed(self):
        from blu_prompt_management.dynamic_builder import _is_langfuse_managed

        assert _is_langfuse_managed("specialists/classify-skill-intent")

    def test_classify_skill_intent_has_required_variables(self):
        from blu_prompt_management.templates import BUILTIN_TEMPLATES

        tpl = BUILTIN_TEMPLATES["specialists/classify-skill-intent"]
        assert "skills_description" in tpl.required_variables
        assert "task" in tpl.required_variables


class TestWorkerExecutorSpecialistGraph:
    """Verify supervisor machinery was removed and specialist graph pattern is in place."""

    def test_worker_invoker_removed(self):
        """_WorkerInvoker must no longer exist in supervisor.py."""
        import blu_agent_framework.supervisor as sup

        assert not hasattr(sup, "_WorkerInvoker")

    def test_build_delegation_tools_removed(self):
        """build_delegation_tools must no longer exist in supervisor.py."""
        import blu_agent_framework.supervisor as sup

        assert not hasattr(sup, "build_delegation_tools")

    def test_use_supervisor_graph_removed(self):
        """use_supervisor_graph must no longer exist on AgentBuilder."""
        assert not hasattr(AgentBuilder, "use_supervisor_graph")


class TestRouteAfterClassifySkill:
    """Verify route_after_classify_skill routes correctly."""

    def test_routes_to_run_skill_when_current_skill_set(self):
        from blu_agent_framework.routing import route_after_classify_skill

        state = create_initial_state(session_id="s", client_id="c")
        state["current_skill"] = "simple_sql_query"
        assert route_after_classify_skill(state) == "run_skill"

    def test_routes_to_respond_when_no_skill(self):
        from blu_agent_framework.routing import route_after_classify_skill

        state = create_initial_state(session_id="s", client_id="c")
        state["current_skill"] = None
        assert route_after_classify_skill(state) == "respond"

