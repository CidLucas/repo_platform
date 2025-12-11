# src/atendente_api/services/twilio_service.py

from twilio.rest import Client
from typing import Optional
from fastapi import Depends

# Importa a dependência de configurações, seguindo nosso padrão
from ..core.config import get_settings, Settings


class TwilioService:
    """
    Serviço encapsulado para interações proativas com a API REST do Twilio.
    """

    def __init__(self, settings: Settings):
        # As credenciais são recebidas de forma segura, sem import global
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        print("INFO: Cliente TwilioService inicializado.")

    def create_conversation(self, group_name: str) -> Optional[str]:
        try:
            conversation = self.client.conversations.v1.conversations.create(
                friendly_name=group_name
            )
            print(
                f"Conversa '{group_name}' criada com sucesso. SID: {conversation.sid}"
            )
            return conversation.sid
        except Exception as e:
            print(f"ERRO ao criar conversa via Twilio: {e}")
            return None

    def add_participant_to_conversation(
        self, conversation_sid: str, participant_number: str
    ) -> Optional[str]:
        try:
            # O friendly_name pode ser adicionado se necessário, mas não é um parâmetro direto do `create`
            participant = self.client.conversations.v1.conversations(
                conversation_sid
            ).participants.create(
                messaging_binding_address=f"whatsapp:{participant_number}"
            )
            print(
                f"Participante {participant_number} adicionado à conversa {conversation_sid}."
            )
            return participant.sid
        except Exception as e:
            print(f"ERRO ao adicionar participante {participant_number}: {e}")
            return None

    def send_system_message(
        self, conversation_sid: str, message_body: str
    ) -> Optional[str]:
        try:
            message = self.client.conversations.v1.conversations(
                conversation_sid
            ).messages.create(author="system", body=message_body)
            print(
                f"Mensagem de sistema enviada para {conversation_sid}: '{message_body}'"
            )
            return message.sid
        except Exception as e:
            print(f"ERRO ao enviar mensagem de sistema: {e}")
            return None


# --- Função de Dependência para FastAPI ---
def get_twilio_service(settings: Settings = Depends(get_settings)) -> TwilioService:
    """
    Dependência do FastAPI que fornece uma instância do TwilioService.
    """
    return TwilioService(settings)
