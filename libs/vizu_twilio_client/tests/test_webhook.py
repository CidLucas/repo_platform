"""Tests for webhook utilities."""

import base64
import hmac
from hashlib import sha1

import pytest
from vizu_twilio_client.webhook import (
    create_twiml_response,
    create_voice_twiml_response,
    parse_webhook_data,
    validate_twilio_signature,
)


class TestSignatureValidation:
    """Test Twilio signature validation."""

    def test_validate_signature_success(self):
        """Test valid signature verification."""
        auth_token = "test_auth_token"
        url = "https://example.com/webhook"
        form_data = {"From": "+1234567890", "Body": "Hello"}

        # Compute expected signature
        data = url + "Body" + "Hello" + "From" + "+1234567890"
        expected_sig = base64.b64encode(
            hmac.new(
                auth_token.encode("utf-8"), data.encode("utf-8"), sha1
            ).digest()
        ).decode("utf-8")

        result = validate_twilio_signature(
            auth_token=auth_token,
            url=url,
            form_data=form_data,
            signature=expected_sig,
        )

        assert result is True

    def test_validate_signature_invalid(self):
        """Test invalid signature rejection."""
        result = validate_twilio_signature(
            auth_token="test_auth_token",
            url="https://example.com/webhook",
            form_data={"From": "+1234567890"},
            signature="invalid_signature",
        )

        assert result is False

    def test_validate_signature_no_signature(self):
        """Test missing signature."""
        result = validate_twilio_signature(
            auth_token="test_auth_token",
            url="https://example.com/webhook",
            form_data={},
            signature=None,
        )

        assert result is False

    def test_validate_signature_empty_form_data(self):
        """Test validation with no form data."""
        auth_token = "test_auth_token"
        url = "https://example.com/webhook"

        # Compute signature for URL only
        data = url
        expected_sig = base64.b64encode(
            hmac.new(
                auth_token.encode("utf-8"), data.encode("utf-8"), sha1
            ).digest()
        ).decode("utf-8")

        result = validate_twilio_signature(
            auth_token=auth_token, url=url, form_data=None, signature=expected_sig
        )

        assert result is True


class TestTwiMLResponses:
    """Test TwiML response creation."""

    def test_create_twiml_response_with_message(self):
        """Test creating TwiML response with message."""
        result = create_twiml_response("Hello World")

        assert "<?xml version" in result
        assert "<Response>" in result
        assert "<Message>Hello World</Message>" in result
        assert "</Response>" in result

    def test_create_twiml_response_with_media(self):
        """Test creating TwiML response with media."""
        result = create_twiml_response(
            "Check this out", media_url=["https://example.com/image.jpg"]
        )

        assert "<Message>Check this out" in result
        assert "<Media>https://example.com/image.jpg</Media>" in result

    def test_create_twiml_response_empty(self):
        """Test creating empty TwiML response."""
        result = create_twiml_response()

        assert "<?xml version" in result
        # Empty response is self-closing: <Response />
        assert "Response" in result

    def test_create_voice_twiml_response_say(self):
        """Test creating voice TwiML with Say."""
        result = create_voice_twiml_response(say="Hello, welcome!")

        assert "<?xml version" in result
        assert "<Response>" in result
        assert "<Say>Hello, welcome!</Say>" in result

    def test_create_voice_twiml_response_play(self):
        """Test creating voice TwiML with Play."""
        result = create_voice_twiml_response(
            play="https://example.com/audio.mp3"
        )

        assert "<Play>https://example.com/audio.mp3</Play>" in result

    def test_create_voice_twiml_response_redirect(self):
        """Test creating voice TwiML with Redirect."""
        result = create_voice_twiml_response(
            redirect="https://example.com/next-step"
        )

        assert "<Redirect>https://example.com/next-step</Redirect>" in result


class TestWebhookDataParsing:
    """Test webhook data parsing."""

    def test_parse_webhook_data_complete(self):
        """Test parsing complete webhook data."""
        form_data = {
            "MessageSid": "SM123",
            "SmsSid": "SM123",
            "Body": "Hello World",
            "From": "+1234567890",
            "To": "+0987654321",
            "AccountSid": "AC123",
            "MessageStatus": "received",
            "FromCity": "San Francisco",
            "FromState": "CA",
            "FromZip": "94103",
            "FromCountry": "US",
            "NumMedia": "2",
            "MediaUrl0": "https://example.com/img1.jpg",
            "MediaUrl1": "https://example.com/img2.jpg",
        }

        result = parse_webhook_data(form_data)

        assert result["message_sid"] == "SM123"
        assert result["body"] == "Hello World"
        assert result["from"] == "+1234567890"
        assert result["to"] == "+0987654321"
        assert result["num_media"] == 2
        assert len(result["media_urls"]) == 2
        assert result["from_city"] == "San Francisco"
        assert result["raw"] == form_data

    def test_parse_webhook_data_minimal(self):
        """Test parsing minimal webhook data."""
        form_data = {
            "From": "+1234567890",
            "Body": "Test",
        }

        result = parse_webhook_data(form_data)

        assert result["from"] == "+1234567890"
        assert result["body"] == "Test"
        assert result["num_media"] == 0
        assert result["media_urls"] == []
        assert result["message_sid"] is None

    def test_parse_webhook_data_no_media(self):
        """Test parsing webhook data with no media."""
        form_data = {
            "From": "+1234567890",
            "Body": "Test",
            "NumMedia": "0",
        }

        result = parse_webhook_data(form_data)

        assert result["num_media"] == 0
        assert result["media_urls"] == []
