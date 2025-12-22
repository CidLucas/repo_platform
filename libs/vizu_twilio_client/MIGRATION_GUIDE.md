# Migration Guide: Using vizu_twilio_client

This guide helps you migrate from direct Twilio SDK usage to the `vizu_twilio_client` library.

## Installation

1. Add the library to your service's `pyproject.toml`:

```toml
[tool.poetry.dependencies]
vizu-twilio-client = {path = "../../libs/vizu_twilio_client", develop = true}
```

2. Remove direct Twilio dependency (it's now transitive through vizu_twilio_client):

```toml
# Remove this line:
# twilio = "^9.0.0"
```

3. Install dependencies:

```bash
cd your-service
poetry lock
poetry install
```

## Environment Variables

Update your environment variables to use the standardized names:

- `TWILIO_ACCOUNT_SID` - Your Twilio Account SID (required)
- `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token (required)
- `TWILIO_MESSAGING_SERVICE_SID` - Optional messaging service SID
- `TWILIO_DEFAULT_FROM_NUMBER` - Optional default phone number

## Code Migration

### Before (Direct Twilio SDK)

```python
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

class TwilioService:
    def __init__(self, settings: Settings):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def create_conversation(self, group_name: str) -> str | None:
        try:
            conversation = self.client.conversations.v1.conversations.create(
                friendly_name=group_name
            )
            return conversation.sid
        except Exception as e:
            print(f"Error: {e}")
            return None
```

### After (vizu_twilio_client)

```python
from vizu_twilio_client import TwilioClient, TwilioSettings
from vizu_twilio_client.webhook import create_twiml_response

# As a FastAPI dependency
def get_twilio_client(
    settings: TwilioSettings = Depends(TwilioSettings),
) -> TwilioClient:
    return TwilioClient(settings)

# Usage
client = TwilioClient(TwilioSettings())
conversation_sid = client.create_conversation("My Group Chat")
```

## API Mapping

### Conversation Management

| Old Method | New Method |
|------------|------------|
| `client.conversations.v1.conversations.create(...)` | `twilio_client.create_conversation(...)` |
| `client.conversations.v1.conversations(sid).fetch()` | `twilio_client.get_conversation(sid)` |
| `client.conversations.v1.conversations(sid).delete()` | `twilio_client.delete_conversation(sid)` |

### Participant Management

| Old Method | New Method |
|------------|------------|
| `client.conversations.v1.conversations(sid).participants.create(...)` | `twilio_client.add_participant(sid, address, channel)` |
| `client.conversations.v1.conversations(sid).participants(pid).delete()` | `twilio_client.remove_participant(sid, pid)` |
| `client.conversations.v1.conversations(sid).participants.list()` | `twilio_client.list_participants(sid)` |

### Messaging

| Old Method | New Method |
|------------|------------|
| `client.conversations.v1.conversations(sid).messages.create(...)` | `twilio_client.send_conversation_message(sid, body, author)` |
| `client.messages.create(to=..., from_=..., body=...)` | `twilio_client.send_sms(to, body, from_)` |
| WhatsApp prefix handling | Automatic in `twilio_client.send_whatsapp(to, body, from_)` |

### Webhook Handling

| Old Code | New Code |
|----------|----------|
| `from twilio.twiml.messaging_response import MessagingResponse` | `from vizu_twilio_client.webhook import create_twiml_response` |
| `resp = MessagingResponse(); resp.message(text); return str(resp)` | `return create_twiml_response(text)` |

### Phone Number Operations

New functionality not easily available before:

```python
# Search for available numbers
numbers = client.search_available_phone_numbers(
    country_code="US",
    area_code="415",
    sms_enabled=True
)

# Purchase a number
result = client.buy_phone_number(
    phone_number="+14155551234",
    sms_url="https://example.com/webhook"
)

# Update number configuration
client.update_phone_number(
    phone_number_sid="PN123",
    sms_url="https://new-webhook.com"
)

# Release a number
client.release_phone_number("PN123")
```

## Benefits

1. **Consistent Error Handling**: All methods return `None` on error and log exceptions
2. **Simplified API**: Cleaner method signatures with sensible defaults
3. **Type Safety**: Full type hints for better IDE support
4. **Reusability**: Share Twilio logic across all services
5. **Testing**: Built-in mocks and fixtures for testing
6. **Webhook Helpers**: Signature validation and TwiML generation utilities

## Example: atendente_core Migration

See [services/atendente_core/src/atendente_core/services/twilio_group.py](../../services/atendente_core/src/atendente_core/services/twilio_group.py) for a complete migration example.

### Key Changes:

1. **Removed** direct `twilio` dependency from `pyproject.toml`
2. **Added** `vizu-twilio-client` dependency
3. **Replaced** custom `TwilioService` class with `get_twilio_client` dependency
4. **Updated** webhook handling to use `create_twiml_response`
5. **Removed** `TWILIO_AUTH_TOKEN` from service-specific settings

## Testing

The library includes comprehensive tests. To run them:

```bash
cd libs/vizu_twilio_client
poetry install
poetry run pytest
```

Your service can now mock the `TwilioClient` in tests:

```python
from unittest.mock import Mock
import pytest

@pytest.fixture
def mock_twilio_client(monkeypatch):
    mock = Mock()
    mock.create_conversation.return_value = "CH123"
    monkeypatch.setattr("your_module.get_twilio_client", lambda: mock)
    return mock
```

## Support

For issues or questions about the library, check:
- [README.md](./README.md) for usage examples
- [tests/](./tests/) for comprehensive test examples
