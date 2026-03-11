# Vizu Twilio Client

A comprehensive Twilio client library for managing conversations, participants, phone numbers, and webhooks.

## Features

- **Conversation Management**: Create and manage Twilio conversations
- **Participant Management**: Add participants to conversations (SMS, WhatsApp)
- **Phone Number Operations**: Search and purchase phone numbers
- **Message Sending**: Send messages through conversations or direct SMS/WhatsApp
- **Webhook Utilities**: Helpers for validating and responding to Twilio webhooks

## Installation

```bash
poetry add vizu-twilio-client
```

## Usage

### Basic Setup

```python
from vizu_twilio_client import TwilioClient, TwilioSettings

# Using settings
settings = TwilioSettings(
    account_sid="your_account_sid",
    auth_token="your_auth_token"
)
client = TwilioClient(settings)

# Or direct initialization
client = TwilioClient.from_credentials(
    account_sid="your_account_sid",
    auth_token="your_auth_token"
)
```

### Conversation Management

```python
# Create a conversation
conversation_sid = client.create_conversation(
    friendly_name="Customer Support Group"
)

# Add participants
participant_sid = client.add_participant(
    conversation_sid=conversation_sid,
    address="+1234567890",
    channel="whatsapp"  # or "sms"
)

# Send a message to the conversation
message_sid = client.send_conversation_message(
    conversation_sid=conversation_sid,
    body="Hello from the support team!",
    author="system"
)
```

### Direct Messaging

```python
# Send SMS
message_sid = client.send_sms(
    to="+1234567890",
    from_="+0987654321",
    body="Your verification code is 123456"
)

# Send WhatsApp message
message_sid = client.send_whatsapp(
    to="+1234567890",
    from_="+0987654321",
    body="Hello via WhatsApp!"
)
```

### Phone Number Management

```python
# Search available phone numbers
available_numbers = client.search_available_phone_numbers(
    country_code="US",
    area_code="415",
    sms_enabled=True,
    mms_enabled=True
)

# Purchase a phone number
phone_number = client.buy_phone_number(
    phone_number="+14155551234",
    sms_url="https://your-domain.com/webhook/sms",
    voice_url="https://your-domain.com/webhook/voice"
)
```

### Webhook Handling

```python
from fastapi import Request, Form, Header
from vizu_twilio_client.webhook import (
    validate_twilio_signature,
    create_twiml_response
)

@app.post("/webhook/twilio")
async def handle_twilio_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    signature: str = Header(None, alias="X-Twilio-Signature")
):
    # Validate the request is from Twilio
    is_valid = validate_twilio_signature(
        auth_token=settings.auth_token,
        url=str(request.url),
        form_data=await request.form(),
        signature=signature
    )

    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Process the message
    response_text = f"You said: {Body}"

    # Return TwiML response
    return create_twiml_response(response_text)
```

## Configuration

The library uses Pydantic settings for configuration:

```python
from vizu_twilio_client import TwilioSettings

settings = TwilioSettings(
    account_sid="AC...",           # Required
    auth_token="your_auth_token",  # Required
    messaging_service_sid="MG...", # Optional
    default_from_number="+1..."    # Optional
)
```

Environment variables are also supported:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_MESSAGING_SERVICE_SID`
- `TWILIO_DEFAULT_FROM_NUMBER`

## Error Handling

All methods return `None` on error and log the exception. For production use, consider checking return values:

```python
conversation_sid = client.create_conversation("Support Chat")
if conversation_sid is None:
    # Handle error
    logger.error("Failed to create conversation")
```

## Testing

```bash
poetry install
poetry run pytest
```
