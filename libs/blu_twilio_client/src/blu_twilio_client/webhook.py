"""Webhook utilities for validating and responding to Twilio requests."""

import hmac
import logging
from hashlib import sha1
from typing import Any
from urllib.parse import urljoin

from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

logger = logging.getLogger(__name__)


def validate_twilio_signature(
    auth_token: str,
    url: str,
    form_data: dict[str, Any] | None = None,
    signature: str | None = None,
) -> bool:
    """
    Validate that a request came from Twilio.

    This implements Twilio's request validation algorithm:
    https://www.twilio.com/docs/usage/security#validating-requests

    Args:
        auth_token: Your Twilio auth token
        url: The full URL of your webhook (including protocol, domain, path, and query params)
        form_data: Dictionary of POST parameters (Form data from the request)
        signature: The X-Twilio-Signature header value

    Returns:
        True if the signature is valid, False otherwise
    """
    if not signature:
        logger.warning("No signature provided for validation")
        return False

    try:
        # Build the signature data string
        data = url
        if form_data:
            # Sort parameters alphabetically and append to URL
            for key in sorted(form_data.keys()):
                data += key + str(form_data[key])

        # Compute HMAC-SHA1 signature
        computed = hmac.new(
            auth_token.encode("utf-8"), data.encode("utf-8"), sha1
        ).digest()

        # Base64 encode the result
        import base64

        computed_signature = base64.b64encode(computed).decode("utf-8")

        # Compare signatures
        is_valid = hmac.compare_digest(signature, computed_signature)

        if not is_valid:
            logger.warning(f"Invalid Twilio signature for URL: {url}")

        return is_valid
    except Exception as e:
        logger.error(f"Error validating Twilio signature: {e}")
        return False


def create_twiml_response(
    message: str | None = None, media_url: list[str] | None = None
) -> str:
    """
    Create a TwiML MessagingResponse XML string.

    Args:
        message: Optional text message to send
        media_url: Optional list of media URLs to include (for MMS)

    Returns:
        TwiML XML string
    """
    response = MessagingResponse()

    if message or media_url:
        msg = response.message(message or "")
        if media_url:
            for url in media_url:
                msg.media(url)

    return str(response)


def create_voice_twiml_response(
    say: str | None = None,
    play: str | None = None,
    redirect: str | None = None,
) -> str:
    """
    Create a TwiML VoiceResponse XML string.

    Args:
        say: Optional text to speak using text-to-speech
        play: Optional audio URL to play
        redirect: Optional URL to redirect the call to

    Returns:
        TwiML XML string
    """
    response = VoiceResponse()

    if say:
        response.say(say)
    if play:
        response.play(play)
    if redirect:
        response.redirect(redirect)

    return str(response)


class TwilioWebhookValidator:
    """
    Context manager for validating Twilio webhook requests.

    Usage:
        validator = TwilioWebhookValidator(auth_token="your_token")

        @app.post("/webhook")
        async def webhook(request: Request):
            if not await validator.validate_request(request):
                raise HTTPException(status_code=403)
            # Process webhook...
    """

    def __init__(self, auth_token: str):
        """
        Initialize the validator.

        Args:
            auth_token: Twilio auth token
        """
        self.auth_token = auth_token

    async def validate_request(self, request: Any) -> bool:
        """
        Validate a FastAPI/Starlette request.

        Args:
            request: FastAPI Request object

        Returns:
            True if valid, False otherwise
        """
        try:
            # Get the signature from headers
            signature = request.headers.get("X-Twilio-Signature")
            if not signature:
                return False

            # Get the full URL
            url = str(request.url)

            # Get form data
            form_data = dict(await request.form())

            return validate_twilio_signature(
                auth_token=self.auth_token,
                url=url,
                form_data=form_data,
                signature=signature,
            )
        except Exception as e:
            logger.error(f"Error validating request: {e}")
            return False


def parse_webhook_data(form_data: dict[str, Any]) -> dict[str, Any]:
    """
    Parse common Twilio webhook form data into a structured format.

    Args:
        form_data: Raw form data from Twilio webhook

    Returns:
        Structured dictionary with parsed webhook data
    """
    return {
        # Message details
        "message_sid": form_data.get("MessageSid"),
        "sms_sid": form_data.get("SmsSid"),
        "body": form_data.get("Body"),
        "num_media": int(form_data.get("NumMedia", 0)),
        # Sender/receiver
        "from": form_data.get("From"),
        "to": form_data.get("To"),
        # Account info
        "account_sid": form_data.get("AccountSid"),
        # Status
        "message_status": form_data.get("MessageStatus"),
        # Location (if available)
        "from_city": form_data.get("FromCity"),
        "from_state": form_data.get("FromState"),
        "from_zip": form_data.get("FromZip"),
        "from_country": form_data.get("FromCountry"),
        # Media URLs (if any)
        "media_urls": [
            form_data.get(f"MediaUrl{i}")
            for i in range(int(form_data.get("NumMedia", 0)))
        ],
        # Raw form data for additional fields
        "raw": form_data,
    }
