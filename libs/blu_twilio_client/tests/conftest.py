"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing."""
    return {
        "MessageSid": "SM123456",
        "SmsSid": "SM123456",
        "Body": "Test message",
        "From": "+1234567890",
        "To": "+0987654321",
        "AccountSid": "AC" + "x" * 32,
        "MessageStatus": "received",
        "NumMedia": "0",
    }


@pytest.fixture
def twilio_credentials():
    """Sample Twilio credentials for testing."""
    return {
        "account_sid": "AC" + "x" * 32,
        "auth_token": "test_auth_token_123456789012345678",
    }
