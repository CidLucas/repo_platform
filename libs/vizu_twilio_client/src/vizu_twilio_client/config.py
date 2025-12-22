"""Configuration management for Twilio client."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TwilioSettings(BaseSettings):
    """
    Twilio configuration settings.

    All settings can be provided via environment variables or passed directly.
    """

    account_sid: str = Field(
        ..., description="Twilio Account SID (starts with 'AC')"
    )
    auth_token: str = Field(..., description="Twilio Auth Token")

    # Optional settings
    messaging_service_sid: str | None = Field(
        None, description="Twilio Messaging Service SID (starts with 'MG')"
    )
    default_from_number: str | None = Field(
        None, description="Default phone number to send messages from"
    )

    model_config = SettingsConfigDict(
        env_prefix="TWILIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_twilio_settings() -> TwilioSettings:
    """
    Get cached Twilio settings instance.

    Returns:
        Cached TwilioSettings instance
    """
    return TwilioSettings()
