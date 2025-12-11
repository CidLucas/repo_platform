"""
Tests for vizu_mcp_commons library.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import jwt
import pytest

from vizu_mcp_commons.auth import TokenClaims, TokenValidator
from vizu_mcp_commons.exceptions import (
    MCPAuthError,
    MCPAuthorizationError,
    MCPContextError,
    MCPError,
    MCPTierAccessError,
    MCPToolError,
)
from vizu_mcp_commons.tool_executor import ToolCall, ToolCallBuilder, ToolExecutor, ToolResult


class TestExceptions:
    """Tests for MCP exception classes."""

    def test_mcp_error_base(self):
        """Test base MCPError."""
        error = MCPError("Test error")
        assert error.message == "Test error"
        assert error.code == "MCP_ERROR"
        assert error.status_code == 500

    def test_mcp_error_with_code(self):
        """Test MCPError with custom code."""
        error = MCPError("Test error", code="CUSTOM_CODE")
        assert error.code == "CUSTOM_CODE"

    def test_mcp_error_with_details(self):
        """Test MCPError with details."""
        error = MCPError("Test error", details={"key": "value"})
        assert error.details == {"key": "value"}

    def test_mcp_error_to_dict(self):
        """Test MCPError.to_dict()."""
        error = MCPError("Test error", code="TEST", details={"foo": "bar"})
        result = error.to_dict()
        assert result == {
            "error": True,
            "code": "TEST",
            "message": "Test error",
            "details": {"foo": "bar"},
        }

    def test_mcp_auth_error(self):
        """Test MCPAuthError."""
        error = MCPAuthError()
        assert error.code == "AUTH_ERROR"
        assert error.status_code == 401
        assert "Autenticação" in error.message

    def test_mcp_authorization_error(self):
        """Test MCPAuthorizationError."""
        error = MCPAuthorizationError()
        assert error.code == "AUTHORIZATION_ERROR"
        assert error.status_code == 403

    def test_mcp_tool_error(self):
        """Test MCPToolError."""
        error = MCPToolError("Tool failed", tool_name="my_tool")
        assert error.tool_name == "my_tool"
        assert error.details["tool_name"] == "my_tool"

    def test_mcp_context_error(self):
        """Test MCPContextError."""
        error = MCPContextError()
        assert error.code == "CONTEXT_ERROR"
        assert error.status_code == 404

    def test_mcp_tier_access_error(self):
        """Test MCPTierAccessError."""
        error = MCPTierAccessError(
            required_tier="PROFISSIONAL",
            current_tier="GRATUITO",
        )
        assert error.code == "TIER_ACCESS_ERROR"
        assert error.details["required_tier"] == "PROFISSIONAL"
        assert error.details["current_tier"] == "GRATUITO"


class TestTokenValidator:
    """Tests for TokenValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.secret = "test-secret-key"
        self.validator = TokenValidator(jwt_secret=self.secret)

    def test_validate_valid_token(self):
        """Test validating a valid token."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, self.secret, algorithm="HS256")

        claims = self.validator.validate(token)
        assert claims.sub == "user-123"
        assert claims.email == "test@example.com"

    def test_validate_token_with_bearer_prefix(self):
        """Test validating token with Bearer prefix."""
        payload = {"sub": "user-123"}
        token = jwt.encode(payload, self.secret, algorithm="HS256")

        claims = self.validator.validate(f"Bearer {token}")
        assert claims.sub == "user-123"

    def test_validate_expired_token(self):
        """Test validating an expired token."""
        payload = {
            "sub": "user-123",
            "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, self.secret, algorithm="HS256")

        with pytest.raises(MCPAuthError) as exc_info:
            self.validator.validate(token)
        assert "expirado" in exc_info.value.message.lower()

    def test_validate_invalid_signature(self):
        """Test validating token with wrong secret."""
        payload = {"sub": "user-123"}
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(MCPAuthError) as exc_info:
            self.validator.validate(token)
        assert "assinatura" in exc_info.value.message.lower()

    def test_validate_missing_sub(self):
        """Test validating token without sub claim."""
        payload = {"email": "test@example.com"}
        token = jwt.encode(payload, self.secret, algorithm="HS256")

        with pytest.raises(MCPAuthError) as exc_info:
            self.validator.validate(token)
        assert "sub" in exc_info.value.message.lower()

    def test_validate_with_scopes(self):
        """Test validating token with scopes."""
        payload = {
            "sub": "user-123",
            "scope": "read write admin",
        }
        token = jwt.encode(payload, self.secret, algorithm="HS256")

        claims = self.validator.validate(token)
        assert claims.scopes == ["read", "write", "admin"]

    def test_validate_with_cliente_id(self):
        """Test validating token with cliente_id."""
        cliente_id = uuid4()
        payload = {
            "sub": "user-123",
            "cliente_id": str(cliente_id),
        }
        token = jwt.encode(payload, self.secret, algorithm="HS256")

        claims = self.validator.validate(token)
        assert claims.cliente_id == cliente_id

    def test_validate_empty_token(self):
        """Test validating empty token."""
        with pytest.raises(MCPAuthError):
            self.validator.validate("")

    def test_validate_none_token(self):
        """Test validating None token."""
        with pytest.raises(MCPAuthError):
            self.validator.validate(None)


class TestTokenClaims:
    """Tests for TokenClaims dataclass."""

    def test_is_expired_false(self):
        """Test is_expired when not expired."""
        claims = TokenClaims(
            sub="user-123",
            exp=datetime.now(UTC) + timedelta(hours=1),
        )
        assert claims.is_expired is False

    def test_is_expired_true(self):
        """Test is_expired when expired."""
        claims = TokenClaims(
            sub="user-123",
            exp=datetime.now(UTC) - timedelta(hours=1),
        )
        assert claims.is_expired is True

    def test_is_expired_no_exp(self):
        """Test is_expired when no expiration."""
        claims = TokenClaims(sub="user-123")
        assert claims.is_expired is False

    def test_external_user_id_alias(self):
        """Test external_user_id property."""
        claims = TokenClaims(sub="user-123")
        assert claims.external_user_id == "user-123"


class TestToolExecutor:
    """Tests for ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_context_service = Mock()

    def test_register_tool(self):
        """Test registering a tool."""
        executor = ToolExecutor(
            context_service_factory=lambda: self.mock_context_service,
        )

        async def my_tool(query: str, cliente_id: str = None) -> str:
            return f"Result for {query}"

        executor.register_tool("my_tool", my_tool)
        assert "my_tool" in executor.tool_callables

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        executor = ToolExecutor(
            context_service_factory=lambda: self.mock_context_service,
        )

        async def my_tool(query: str, cliente_id: str = None) -> str:
            return f"Result for {query}"

        executor.register_tool("my_tool", my_tool)

        # Create mock context
        mock_context = Mock()
        mock_context.id = uuid4()
        mock_context.get_enabled_tools_list = Mock(return_value=["my_tool"])
        mock_context.tier = Mock(value="PROFISSIONAL")

        result = await executor.execute_tool(
            tool_name="my_tool",
            args={"query": "test query"},
            cliente_context=mock_context,
            validate_access=False,
        )

        assert result.success is True
        assert result.result == "Result for test query"
        assert result.name == "my_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test execution of non-existent tool."""
        executor = ToolExecutor(
            context_service_factory=lambda: self.mock_context_service,
        )

        mock_context = Mock()
        mock_context.id = uuid4()
        mock_context.get_enabled_tools_list = Mock(return_value=[])

        result = await executor.execute_tool(
            tool_name="nonexistent_tool",
            args={},
            cliente_context=mock_context,
            validate_access=False,
        )

        assert result.success is False
        assert result.error_code == "TOOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        """Test parallel tool execution."""
        executor = ToolExecutor(
            context_service_factory=lambda: self.mock_context_service,
        )

        async def tool1(query: str, cliente_id: str = None) -> str:
            return "Result 1"

        async def tool2(query: str, cliente_id: str = None) -> str:
            return "Result 2"

        executor.register_tool("tool1", tool1)
        executor.register_tool("tool2", tool2)

        mock_context = Mock()
        mock_context.id = uuid4()
        mock_context.get_enabled_tools_list = Mock(return_value=["tool1", "tool2"])

        tool_calls = [
            ToolCall(name="tool1", args={"query": "q1"}, call_id="call1"),
            ToolCall(name="tool2", args={"query": "q2"}, call_id="call2"),
        ]

        results = await executor.execute_parallel(
            tool_calls=tool_calls,
            cliente_context=mock_context,
            validate_access=False,
        )

        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].result == "Result 1"
        assert results[1].result == "Result 2"


class TestToolCallBuilder:
    """Tests for ToolCallBuilder."""

    def test_from_openai_tool_calls(self):
        """Test converting OpenAI tool calls."""
        openai_calls = [
            {
                "id": "call_123",
                "name": "my_tool",
                "arguments": '{"query": "test"}',
            },
        ]

        result = ToolCallBuilder.from_openai_tool_calls(openai_calls)

        assert len(result) == 1
        assert result[0].name == "my_tool"
        assert result[0].args == {"query": "test"}
        assert result[0].call_id == "call_123"

    def test_from_langchain_tool_calls(self):
        """Test converting LangChain tool calls."""
        langchain_calls = [
            {
                "id": "call_456",
                "name": "my_tool",
                "args": {"query": "test"},
            },
        ]

        result = ToolCallBuilder.from_langchain_tool_calls(langchain_calls)

        assert len(result) == 1
        assert result[0].name == "my_tool"
        assert result[0].args == {"query": "test"}
        assert result[0].call_id == "call_456"


class TestToolResult:
    """Tests for ToolResult."""

    def test_to_dict(self):
        """Test ToolResult.to_dict()."""
        result = ToolResult(
            call_id="call_123",
            name="my_tool",
            success=True,
            result="Success!",
            duration_ms=150.5,
        )

        d = result.to_dict()
        assert d["call_id"] == "call_123"
        assert d["name"] == "my_tool"
        assert d["success"] is True
        assert d["result"] == "Success!"
        assert d["duration_ms"] == 150.5

    def test_to_dict_with_error(self):
        """Test ToolResult.to_dict() with error."""
        result = ToolResult(
            call_id="call_123",
            name="my_tool",
            success=False,
            error="Something went wrong",
            error_code="EXECUTION_ERROR",
        )

        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Something went wrong"
        assert d["error_code"] == "EXECUTION_ERROR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
