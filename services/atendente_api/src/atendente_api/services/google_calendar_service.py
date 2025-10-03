from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from typing import Dict, Any

from ..config import Settings

class GoogleCalendarService:
    """
    Serviço para interagir com a Google Calendar API usando as credenciais do usuário.
    """
    def __init__(self, refresh_token: str):
        if not refresh_token:
            raise ValueError("Refresh token do Google não fornecido.")

        self.credentials = Credentials.from_authorized_user_info(
            info={
                "refresh_token": refresh_token,
                "client_id": Settings.GOOGLE_CLIENT_ID,
                "client_secret": Settings.GOOGLE_CLIENT_SECRET,
            },
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        self.service: Resource = build("calendar", "v3", credentials=self.credentials)

    def book_event(self, summary: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Cria um evento no calendário."""
        event = {
            'summary': summary,
            'start': {'dateTime': f"{start_time}", 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': f"{end_time}", 'timeZone': 'America/Sao_Paulo'},
        }
        created_event = self.service.events().insert(calendarId='primary', body=event).execute()
        return {"status": "confirmed", "id": created_event['id'], "link": created_event.get('htmlLink')}

    def cancel_event(self, event_id: str) -> Dict[str, Any]:
        """Cancela um evento pelo seu ID."""
        self.service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"status": "cancelled"}

    # Funções para checar disponibilidade (freebusy) podem ser adicionadas aqui