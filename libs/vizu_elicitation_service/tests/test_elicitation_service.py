"""
Tests for vizu_elicitation_service components.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from vizu_elicitation_service import (
    PendingElicitation,
    ElicitationResult,
    ElicitationRequired,
    ElicitationError,
    ElicitationValidationError,
    ElicitationNotFoundError,
    PendingElicitationStore,
    ElicitationResponseHandler,
    ElicitationManager,
    create_confirmation_elicitation,
    create_selection_elicitation,
    create_text_input_elicitation,
    create_datetime_elicitation,
    format_elicitation_for_llm,
    normalize_confirmation_response,
    validate_elicitation_response,
    build_options_from_list,
)

from vizu_models import ElicitationType, ElicitationOption


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_elicitation() -> PendingElicitation:
    """Sample pending elicitation for tests."""
    return {
        "elicitation_id": str(uuid4()),
        "session_id": "test-session-123",
        "type": ElicitationType.CONFIRMATION.value,
        "message": "Confirmar agendamento?",
        "tool_name": "book_appointment",
        "tool_args": {"date": "2025-01-15", "time": "10:00"},
        "options": [
            {"value": "yes", "label": "Sim"},
            {"value": "no", "label": "Não"},
        ],
        "metadata": {"service": "haircut"},
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.ttl = AsyncMock(return_value=3600)
    redis.expire = AsyncMock(return_value=True)
    return redis


# ============================================================================
# ElicitationRequired Exception Tests
# ============================================================================


class TestElicitationRequired:
    """Tests for ElicitationRequired exception."""

    def test_create_confirmation(self):
        """Test creating confirmation elicitation."""
        exc = create_confirmation_elicitation(
            message="Confirma?",
            tool_name="test_tool",
            tool_args={"arg": "value"},
        )

        assert isinstance(exc, ElicitationRequired)
        assert exc.type == ElicitationType.CONFIRMATION
        assert exc.message == "Confirma?"
        assert exc.tool_name == "test_tool"
        assert exc.tool_args == {"arg": "value"}
        assert len(exc.options) == 2

    def test_create_selection(self):
        """Test creating selection elicitation."""
        options = [
            ElicitationOption(value="a", label="Option A"),
            ElicitationOption(value="b", label="Option B"),
        ]
        exc = create_selection_elicitation(
            message="Choose one",
            options=options,
            tool_name="test_tool",
            tool_args={},
        )

        assert exc.type == ElicitationType.SELECTION
        assert len(exc.options) == 2

    def test_create_text_input(self):
        """Test creating text input elicitation."""
        exc = create_text_input_elicitation(
            message="Enter your name:",
            tool_name="get_name",
            tool_args={},
        )

        assert exc.type == ElicitationType.TEXT_INPUT
        assert exc.options is None or len(exc.options) == 0

    def test_create_datetime(self):
        """Test creating datetime elicitation."""
        exc = create_datetime_elicitation(
            message="Choose a date:",
            tool_name="schedule",
            tool_args={},
        )

        assert exc.type == ElicitationType.DATE_TIME

    def test_to_pending_elicitation(self):
        """Test converting exception to pending elicitation."""
        exc = ElicitationRequired(
            type=ElicitationType.CONFIRMATION,
            message="Test?",
            tool_name="test",
            tool_args={"a": 1},
            options=[ElicitationOption(value="yes", label="Yes")],
            metadata={"key": "value"},
        )

        pending = exc.to_pending_elicitation()

        assert pending["elicitation_id"] == exc.elicitation_id
        assert pending["type"] == ElicitationType.CONFIRMATION.value
        assert pending["message"] == "Test?"
        assert pending["tool_name"] == "test"
        assert pending["tool_args"] == {"a": 1}


# ============================================================================
# PendingElicitationStore Tests
# ============================================================================


class TestPendingElicitationStore:
    """Tests for PendingElicitationStore."""

    @pytest.mark.asyncio
    async def test_save_and_get(self, mock_redis, sample_elicitation):
        """Test saving and retrieving elicitation."""
        store = PendingElicitationStore(redis_client=mock_redis, ttl_seconds=60)

        # Setup mock to return saved data
        mock_redis.get = AsyncMock(return_value=json.dumps(sample_elicitation))

        await store.save("session-1", sample_elicitation)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert "vizu:elicitation:session-1" in call_args[0]

        result = await store.get("session-1")
        assert result is not None
        assert result["session_id"] == sample_elicitation["session_id"]

    @pytest.mark.asyncio
    async def test_get_not_found(self, mock_redis):
        """Test getting non-existent elicitation."""
        store = PendingElicitationStore(redis_client=mock_redis)

        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_raise(self, mock_redis):
        """Test get_or_raise with missing elicitation."""
        store = PendingElicitationStore(redis_client=mock_redis)

        with pytest.raises(ElicitationNotFoundError):
            await store.get_or_raise("nonexistent")

    @pytest.mark.asyncio
    async def test_delete(self, mock_redis):
        """Test deleting elicitation."""
        store = PendingElicitationStore(redis_client=mock_redis)

        result = await store.delete("session-1")
        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists(self, mock_redis):
        """Test checking if elicitation exists."""
        store = PendingElicitationStore(redis_client=mock_redis)

        mock_redis.exists = AsyncMock(return_value=1)
        assert await store.exists("session-1") is True

        mock_redis.exists = AsyncMock(return_value=0)
        assert await store.exists("session-2") is False

    @pytest.mark.asyncio
    async def test_extend_ttl(self, mock_redis):
        """Test extending TTL."""
        store = PendingElicitationStore(redis_client=mock_redis)

        mock_redis.ttl = AsyncMock(return_value=100)

        result = await store.extend_ttl("session-1", 60)
        assert result is True
        mock_redis.expire.assert_called_once()


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_normalize_confirmation_response_true(self):
        """Test normalizing truthy responses."""
        truthy = ["yes", "YES", "sim", "SIM", "y", "Y", "s", "S", "true", "1"]
        for val in truthy:
            assert normalize_confirmation_response(val) is True

        assert normalize_confirmation_response(True) is True

    def test_normalize_confirmation_response_false(self):
        """Test normalizing falsy responses."""
        falsy = ["no", "NO", "não", "nao", "NAO", "n", "N", "false", "0"]
        for val in falsy:
            assert normalize_confirmation_response(val) is False

        assert normalize_confirmation_response(False) is False

    def test_validate_confirmation_response(self, sample_elicitation):
        """Test validation of confirmation responses."""
        is_valid, error = validate_elicitation_response(sample_elicitation, "yes")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_elicitation_response(sample_elicitation, "maybe")
        assert is_valid is False
        assert error is not None

    def test_validate_selection_response(self):
        """Test validation of selection responses."""
        pending: PendingElicitation = {
            "elicitation_id": "1",
            "session_id": "s1",
            "type": ElicitationType.SELECTION.value,
            "message": "Choose",
            "tool_name": "tool",
            "tool_args": {},
            "options": [
                {"value": "opt1", "label": "Option 1"},
                {"value": "opt2", "label": "Option 2"},
            ],
        }

        is_valid, _ = validate_elicitation_response(pending, "opt1")
        assert is_valid is True

        is_valid, _ = validate_elicitation_response(pending, "opt3")
        assert is_valid is False

        # Numeric index
        is_valid, _ = validate_elicitation_response(pending, "1")
        assert is_valid is True

    def test_validate_text_input_response(self):
        """Test validation of text input responses."""
        pending: PendingElicitation = {
            "elicitation_id": "1",
            "session_id": "s1",
            "type": ElicitationType.TEXT_INPUT.value,
            "message": "Enter text",
            "tool_name": "tool",
            "tool_args": {},
        }

        is_valid, _ = validate_elicitation_response(pending, "some text")
        assert is_valid is True

        is_valid, _ = validate_elicitation_response(pending, "   ")
        assert is_valid is False

    def test_build_options_from_list(self):
        """Test building options from string list."""
        items = ["Corte", "Barba", "Combo"]
        descriptions = {"Corte": "Corte de cabelo", "Combo": "Corte + Barba"}

        options = build_options_from_list(items, descriptions)

        assert len(options) == 3
        assert options[0].value == "Corte"
        assert options[0].description == "Corte de cabelo"
        assert options[1].description is None

    def test_format_elicitation_for_llm_confirmation(self, sample_elicitation):
        """Test formatting confirmation for LLM."""
        formatted = format_elicitation_for_llm(sample_elicitation)

        assert "[AGUARDANDO CONFIRMAÇÃO]" in formatted
        assert "Confirmar agendamento?" in formatted
        assert "Sim" in formatted

    def test_format_elicitation_for_llm_selection(self):
        """Test formatting selection for LLM."""
        pending: PendingElicitation = {
            "elicitation_id": "1",
            "session_id": "s1",
            "type": ElicitationType.SELECTION.value,
            "message": "Escolha o serviço",
            "tool_name": "tool",
            "tool_args": {},
            "options": [
                {"value": "corte", "label": "Corte", "description": "Corte básico"},
                {"value": "barba", "label": "Barba"},
            ],
        }

        formatted = format_elicitation_for_llm(pending)

        assert "[AGUARDANDO SELEÇÃO]" in formatted
        assert "Corte" in formatted
        assert "Barba" in formatted


# ============================================================================
# ElicitationResponseHandler Tests
# ============================================================================


class TestElicitationResponseHandler:
    """Tests for ElicitationResponseHandler."""

    def test_process_confirmation(self, sample_elicitation):
        """Test processing confirmation response."""
        handler = ElicitationResponseHandler()

        result = handler.process(sample_elicitation, "yes")

        assert result.success is True
        assert result.response is True  # normalized to boolean
        assert result.tool_name == "book_appointment"

    def test_process_confirmation_declined(self, sample_elicitation):
        """Test processing declined confirmation."""
        handler = ElicitationResponseHandler()

        result = handler.process(sample_elicitation, "no")

        assert result.success is True
        assert result.response is False

    def test_process_selection(self):
        """Test processing selection response."""
        pending: PendingElicitation = {
            "elicitation_id": "1",
            "session_id": "s1",
            "type": ElicitationType.SELECTION.value,
            "message": "Choose",
            "tool_name": "select_service",
            "tool_args": {"user_id": "123"},
            "options": [
                {"value": "corte", "label": "Corte"},
                {"value": "barba", "label": "Barba"},
            ],
        }

        handler = ElicitationResponseHandler()
        result = handler.process(pending, "corte")

        assert result.success is True
        assert result.response == "corte"

    def test_process_text_input(self):
        """Test processing text input response."""
        pending: PendingElicitation = {
            "elicitation_id": "1",
            "session_id": "s1",
            "type": ElicitationType.TEXT_INPUT.value,
            "message": "Enter CPF",
            "tool_name": "validate_cpf",
            "tool_args": {},
        }

        handler = ElicitationResponseHandler()
        result = handler.process(pending, "123.456.789-00")

        assert result.success is True
        assert result.response == "123.456.789-00"

    def test_process_invalid_response(self, sample_elicitation):
        """Test processing invalid response."""
        handler = ElicitationResponseHandler()

        result = handler.process(sample_elicitation, "maybe")

        assert result.success is False
        assert result.error is not None


# ============================================================================
# ElicitationManager Tests
# ============================================================================


class TestElicitationManager:
    """Tests for ElicitationManager."""

    @pytest.fixture
    def manager(self, mock_redis):
        """Create ElicitationManager instance."""
        return ElicitationManager(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_store_pending(self, manager, mock_redis):
        """Test storing elicitation from exception."""
        exc = create_confirmation_elicitation(
            message="Confirm?",
            tool_name="test_tool",
            tool_args={"x": 1},
        )

        elicit_id = await manager.store_pending(session_id="sess-1", elicitation=exc)

        assert elicit_id == exc.elicitation_id
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_pending(self, manager, mock_redis, sample_elicitation):
        """Test checking for pending elicitation."""
        mock_redis.exists = AsyncMock(return_value=0)
        assert await manager.has_pending("sess-1") is False

        mock_redis.exists = AsyncMock(return_value=1)
        assert await manager.has_pending("sess-1") is True

    @pytest.mark.asyncio
    async def test_process_response_success(self, manager, mock_redis, sample_elicitation):
        """Test submitting valid response."""
        mock_redis.get = AsyncMock(return_value=json.dumps(sample_elicitation))

        result = await manager.process_response("sess-1", "yes")

        assert result.success is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_response_no_pending(self, manager, mock_redis):
        """Test submitting response when no pending elicitation."""
        with pytest.raises(ElicitationNotFoundError):
            await manager.process_response("sess-1", "yes")

    @pytest.mark.asyncio
    async def test_clear_pending(self, manager, mock_redis):
        """Test clearing pending elicitation."""
        mock_redis.delete = AsyncMock(return_value=1)

        result = await manager.clear_pending("sess-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_retrieve_pending(self, manager, mock_redis, sample_elicitation):
        """Test getting pending elicitation."""
        mock_redis.get = AsyncMock(return_value=json.dumps(sample_elicitation))

        pending = await manager.retrieve_pending("sess-1")

        assert pending is not None
        assert pending["session_id"] == sample_elicitation["session_id"]
