"""
Twilio service wrapper using vizu_twilio_client library.

This module provides a FastAPI-compatible dependency for Twilio operations,
using the shared vizu_twilio_client library.
"""

from fastapi import Depends
from vizu_twilio_client import TwilioClient, TwilioSettings


def get_twilio_client(
    settings: TwilioSettings = Depends(TwilioSettings),
) -> TwilioClient:
    """
    FastAPI dependency that provides a TwilioClient instance.

    The TwilioSettings will automatically load from environment variables:
    - TWILIO_ACCOUNT_SID
    - TWILIO_AUTH_TOKEN
    - TWILIO_MESSAGING_SERVICE_SID (optional)
    - TWILIO_DEFAULT_FROM_NUMBER (optional)

    Returns:
        Configured TwilioClient instance
    """
    return TwilioClient(settings)
