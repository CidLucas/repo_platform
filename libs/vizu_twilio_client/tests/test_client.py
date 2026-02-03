"""Tests for TwilioClient."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from vizu_twilio_client import TwilioClient, TwilioSettings


@pytest.fixture
def mock_twilio_client():
    """Mock Twilio REST client."""
    with patch("vizu_twilio_client.client.Client") as mock:
        yield mock


@pytest.fixture
def twilio_settings():
    """Create test settings."""
    return TwilioSettings(
        account_sid="AC" + "x" * 32, auth_token="test_token_123456789012345678901234"
    )


@pytest.fixture
def client(twilio_settings, mock_twilio_client):
    """Create TwilioClient with mocked Twilio."""
    return TwilioClient(twilio_settings)


class TestTwilioClientInit:
    """Test client initialization."""

    def test_init_with_settings(self, twilio_settings, mock_twilio_client):
        """Test initialization with settings."""
        client = TwilioClient(twilio_settings)
        assert client.settings == twilio_settings
        mock_twilio_client.assert_called_once_with(
            twilio_settings.account_sid, twilio_settings.auth_token
        )

    def test_from_credentials(self, mock_twilio_client):
        """Test creation from credentials."""
        client = TwilioClient.from_credentials(
            account_sid="AC" + "x" * 32, auth_token="test_token"
        )
        assert client.settings.account_sid == "AC" + "x" * 32
        assert client.settings.auth_token == "test_token"


class TestConversationManagement:
    """Test conversation management methods."""

    def test_create_conversation_success(self, client, mock_twilio_client):
        """Test successful conversation creation."""
        mock_conv = Mock()
        mock_conv.sid = "CH123"
        mock_twilio_client.return_value.conversations.v1.conversations.create.return_value = (
            mock_conv
        )

        result = client.create_conversation("Test Chat")

        assert result == "CH123"
        mock_twilio_client.return_value.conversations.v1.conversations.create.assert_called_once_with(
            friendly_name="Test Chat"
        )

    def test_create_conversation_with_unique_name(self, client, mock_twilio_client):
        """Test conversation creation with unique name."""
        mock_conv = Mock()
        mock_conv.sid = "CH123"
        mock_twilio_client.return_value.conversations.v1.conversations.create.return_value = (
            mock_conv
        )

        result = client.create_conversation("Test Chat", unique_name="test-123")

        assert result == "CH123"
        mock_twilio_client.return_value.conversations.v1.conversations.create.assert_called_once_with(
            friendly_name="Test Chat", unique_name="test-123"
        )

    def test_create_conversation_failure(self, client, mock_twilio_client):
        """Test conversation creation failure."""
        mock_twilio_client.return_value.conversations.v1.conversations.create.side_effect = (
            Exception("API Error")
        )

        result = client.create_conversation("Test Chat")

        assert result is None

    def test_get_conversation_success(self, client, mock_twilio_client):
        """Test getting conversation details."""
        mock_conv = Mock()
        mock_conv.sid = "CH123"
        mock_conv.friendly_name = "Test Chat"
        mock_conv.unique_name = "test-123"
        mock_conv.state = "active"
        mock_conv.date_created = "2024-01-01"
        mock_conv.date_updated = "2024-01-02"

        mock_twilio_client.return_value.conversations.v1.conversations.return_value.fetch.return_value = (
            mock_conv
        )

        result = client.get_conversation("CH123")

        assert result["sid"] == "CH123"
        assert result["friendly_name"] == "Test Chat"
        assert result["unique_name"] == "test-123"
        assert result["state"] == "active"

    def test_delete_conversation_success(self, client, mock_twilio_client):
        """Test deleting conversation."""
        result = client.delete_conversation("CH123")

        assert result is True
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.delete.assert_called_once()


class TestParticipantManagement:
    """Test participant management methods."""

    def test_add_participant_sms(self, client, mock_twilio_client):
        """Test adding SMS participant."""
        mock_participant = Mock()
        mock_participant.sid = "MB123"
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.participants.create.return_value = (
            mock_participant
        )

        result = client.add_participant("CH123", "+1234567890", channel="sms")

        assert result == "MB123"
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.participants.create.assert_called_once_with(
            messaging_binding_address="+1234567890"
        )

    def test_add_participant_whatsapp(self, client, mock_twilio_client):
        """Test adding WhatsApp participant."""
        mock_participant = Mock()
        mock_participant.sid = "MB123"
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.participants.create.return_value = (
            mock_participant
        )

        result = client.add_participant("CH123", "+1234567890", channel="whatsapp")

        assert result == "MB123"
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.participants.create.assert_called_once_with(
            messaging_binding_address="whatsapp:+1234567890"
        )

    def test_remove_participant(self, client, mock_twilio_client):
        """Test removing participant."""
        result = client.remove_participant("CH123", "MB123")

        assert result is True
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.participants.return_value.delete.assert_called_once()


class TestMessaging:
    """Test message sending methods."""

    def test_send_conversation_message(self, client, mock_twilio_client):
        """Test sending message to conversation."""
        mock_message = Mock()
        mock_message.sid = "IM123"
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.messages.create.return_value = (
            mock_message
        )

        result = client.send_conversation_message(
            "CH123", "Hello!", author="system"
        )

        assert result == "IM123"
        mock_twilio_client.return_value.conversations.v1.conversations.return_value.messages.create.assert_called_once_with(
            author="system", body="Hello!"
        )

    def test_send_sms(self, client, mock_twilio_client):
        """Test sending SMS."""
        mock_message = Mock()
        mock_message.sid = "SM123"
        mock_twilio_client.return_value.messages.create.return_value = mock_message

        result = client.send_sms(
            to="+1234567890", from_="+0987654321", body="Test SMS"
        )

        assert result == "SM123"
        mock_twilio_client.return_value.messages.create.assert_called_once_with(
            to="+1234567890", from_="+0987654321", body="Test SMS"
        )

    def test_send_sms_with_default_from(self, mock_twilio_client):
        """Test sending SMS with default from number."""
        settings = TwilioSettings(
            account_sid="AC" + "x" * 32,
            auth_token="test_token",
            default_from_number="+0987654321",
        )
        client = TwilioClient(settings)

        mock_message = Mock()
        mock_message.sid = "SM123"
        mock_twilio_client.return_value.messages.create.return_value = mock_message

        result = client.send_sms(to="+1234567890", body="Test SMS")

        assert result == "SM123"
        mock_twilio_client.return_value.messages.create.assert_called_once_with(
            to="+1234567890", from_="+0987654321", body="Test SMS"
        )

    def test_send_whatsapp(self, client, mock_twilio_client):
        """Test sending WhatsApp message."""
        mock_message = Mock()
        mock_message.sid = "SM123"
        mock_twilio_client.return_value.messages.create.return_value = mock_message

        result = client.send_whatsapp(
            to="+1234567890", from_="+0987654321", body="Test WhatsApp"
        )

        assert result == "SM123"
        mock_twilio_client.return_value.messages.create.assert_called_once_with(
            to="whatsapp:+1234567890",
            from_="whatsapp:+0987654321",
            body="Test WhatsApp",
        )


class TestPhoneNumberOperations:
    """Test phone number operations."""

    def test_search_available_phone_numbers(self, client, mock_twilio_client):
        """Test searching for available phone numbers."""
        mock_number = Mock()
        mock_number.phone_number = "+14155551234"
        mock_number.friendly_name = "San Francisco Number"
        mock_number.capabilities = {"sms": True, "mms": True, "voice": False}
        mock_number.locality = "San Francisco"
        mock_number.region = "CA"
        mock_number.postal_code = "94103"

        mock_twilio_client.return_value.available_phone_numbers.return_value.local.list.return_value = [
            mock_number
        ]

        result = client.search_available_phone_numbers(
            country_code="US", area_code="415", sms_enabled=True
        )

        assert len(result) == 1
        assert result[0]["phone_number"] == "+14155551234"
        assert result[0]["capabilities"]["sms"] is True

    def test_buy_phone_number(self, client, mock_twilio_client):
        """Test purchasing a phone number."""
        mock_number = Mock()
        mock_number.sid = "PN123"
        mock_number.phone_number = "+14155551234"
        mock_number.friendly_name = "My Number"
        mock_number.capabilities = {"sms": True, "mms": True, "voice": True}

        mock_twilio_client.return_value.incoming_phone_numbers.create.return_value = (
            mock_number
        )

        result = client.buy_phone_number(
            phone_number="+14155551234",
            friendly_name="My Number",
            sms_url="https://example.com/sms",
        )

        assert result["sid"] == "PN123"
        assert result["phone_number"] == "+14155551234"
        mock_twilio_client.return_value.incoming_phone_numbers.create.assert_called_once_with(
            phone_number="+14155551234",
            friendly_name="My Number",
            sms_url="https://example.com/sms",
        )

    def test_update_phone_number(self, client, mock_twilio_client):
        """Test updating phone number configuration."""
        result = client.update_phone_number(
            "PN123", friendly_name="Updated Name", sms_url="https://new-url.com/sms"
        )

        assert result is True
        mock_twilio_client.return_value.incoming_phone_numbers.return_value.update.assert_called_once_with(
            friendly_name="Updated Name", sms_url="https://new-url.com/sms"
        )

    def test_release_phone_number(self, client, mock_twilio_client):
        """Test releasing a phone number."""
        result = client.release_phone_number("PN123")

        assert result is True
        mock_twilio_client.return_value.incoming_phone_numbers.return_value.delete.assert_called_once()
