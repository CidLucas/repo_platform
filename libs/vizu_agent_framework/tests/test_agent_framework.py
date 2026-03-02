"""
Tests for vizu_agent_framework components.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from vizu_agent_framework import (
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
        cliente_id="client-456",
        messages=[HumanMessage(content="Hello")],
        enabled_tools=["tool_a", "tool_b"],
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
            cliente_id="client-1",
            enabled_tools=["tool_a"],
        )

        assert state["session_id"] == "sess-1"
        assert state["cliente_id"] == "client-1"
        assert state["enabled_tools"] == ["tool_a"]
        assert state["turn_count"] == 0
        assert state["ended"] is False

    def test_initial_state_with_messages(self):
        """Test initial state with messages."""
        messages = [HumanMessage(content="Hi")]
        state = create_initial_state(
            session_id="sess-1",
            cliente_id="client-1",
            messages=messages,
        )

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Hi"

    def test_initial_state_with_client_context(self):
        """Test initial state with client context."""
        context = {"nome_empresa": "Test Co", "tier": "SME"}
        state = create_initial_state(
            session_id="sess-1",
            cliente_id="client-1",
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
            cliente_id="client-1",
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
    async def test_execute_tool_node_validates_enabled(self, sample_state):
        """Test execute tool validates tool is enabled."""
        sample_state["tool_to_execute"] = "disabled_tool"

        result = await execute_tool_node(sample_state)

        assert "error" in result
        assert "not enabled" in result["error"]

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
# MCPToolExecutor Tests
# ============================================================================


class TestMCPToolExecutor:
    """Tests for MCPToolExecutor."""

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful tool execution."""
        from vizu_agent_framework.mcp_executor import MockMCPToolExecutor

        executor = MockMCPToolExecutor(
            {"test_tool": {"success": True, "result": {"data": "value"}}}
        )

        result = await executor.execute(
            tool_name="test_tool",
            tool_args={"arg": "value"},
            context={"cliente_id": "123"},
        )

        assert result.success is True
        assert result.result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """Test failed tool execution."""
        from vizu_agent_framework.mcp_executor import MockMCPToolExecutor

        executor = MockMCPToolExecutor({"failing_tool": {"success": False, "error": "Tool failed"}})

        result = await executor.execute(
            tool_name="failing_tool",
            tool_args={},
            context={},
        )

        assert result.success is False
        assert result.error == "Tool failed"

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        """Test parallel tool execution."""
        from vizu_agent_framework.mcp_executor import MockMCPToolExecutor

        executor = MockMCPToolExecutor(
            {
                "tool_a": {"success": True, "result": "A"},
                "tool_b": {"success": True, "result": "B"},
            }
        )

        results = await executor.execute_parallel(
            tool_calls=[
                {"tool_name": "tool_a", "tool_args": {}},
                {"tool_name": "tool_b", "tool_args": {}},
            ],
            context={},
        )

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_mock_executor_call_history(self):
        """Test mock executor tracks call history."""
        from vizu_agent_framework.mcp_executor import MockMCPToolExecutor

        executor = MockMCPToolExecutor()

        import asyncio

        asyncio.run(executor.execute("tool", {"arg": 1}, {}))
        asyncio.run(executor.execute("tool", {"arg": 2}, {}))

        history = executor.get_calls("tool")
        assert len(history) == 2


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
        from vizu_agent_framework.mcp_executor import MockMCPToolExecutor

        checkpointer = RedisCheckpointer(mock_redis)
        executor = MockMCPToolExecutor()

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
        assert key == "vizu:checkpoint:thread-1"

        key = checkpointer._make_key("thread-1", "ns-1")
        assert key == "vizu:checkpoint:thread-1:ns-1"

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
