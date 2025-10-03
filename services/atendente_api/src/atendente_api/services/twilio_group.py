
# Arquivo: virtual_assistant/core/twilio_group.py
from twilio.rest import Client
from virtual_assistant.config import settings
from typing import List, Optional

def _get_twilio_client() -> Client:
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def create_conversation(group_name: str) -> Optional[str]:
    try:
        client = _get_twilio_client()
        conversation = client.conversations.v1.conversations.create(friendly_name=group_name)
        print(f"Conversa '{group_name}' criada com sucesso. SID: {conversation.sid}")
        return conversation.sid
    except Exception as e:
        print(f"ERRO ao criar conversa via Twilio: {e}")
        return None

def add_participant_to_conversation(conversation_sid: str, participant_number: str, friendly_name: str = None) -> Optional[str]:
    try:
        client = _get_twilio_client()
        participant = client.conversations.v1.conversations(conversation_sid).participants.create(
            messaging_binding_address=f'whatsapp:{participant_number}'
        )
        print(f"Participante {participant_number} adicionado à conversa {conversation_sid}.")
        return participant.sid
    except Exception as e:
        print(f"ERRO ao adicionar participante {participant_number}: {e}")
        return None

def send_system_message(conversation_sid: str, message_body: str) -> Optional[str]:
    try:
        client = _get_twilio_client()
        message = client.conversations.v1.conversations(conversation_sid).messages.create(
            author='system',
            body=message_body
        )
        print(f"Mensagem de sistema enviada para {conversation_sid}: '{message_body}'")
        return message.sid
    except Exception as e:
        print(f"ERRO ao enviar mensagem de sistema: {e}")
        return None