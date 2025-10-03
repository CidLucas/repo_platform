from typing import Dict, Any
from .schemas import SchedulingTool
from virtual_assistant.services.google_calendar_service import GoogleCalendarService
import datetime

def execute_scheduling_action(validated_input: SchedulingTool) -> Dict[str, Any]:
    """
    Subgraph que executa ações na Google Calendar API através do serviço.
    """
    print(f"\n---[Subgraph Agendamento] Iniciando execução real: {validated_input.dict()}---")

    intent = validated_input.intent

    try:
        if not validated_input.google_refresh_token:
            return {"error": "A conta não está conectada ao Google Agenda."}

        service = GoogleCalendarService(refresh_token=validated_input.google_refresh_token)

        if intent == "book":
            if not all([validated_input.service, validated_input.date, validated_input.time]):
                return {"error": "Para agendar, preciso do serviço, data e hora."}

            # A API do Google precisa de data e hora de início e fim.
            # Vamos assumir que os eventos duram 1 hora para este exemplo.
            start_dt = f"{validated_input.date}T{validated_input.time}:00"
            end_hour = int(validated_input.time.split(':')[0]) + 1
            end_dt = f"{validated_input.date}T{end_hour:02d}:{validated_input.time.split(':')[1]}:00"

            result = service.book_event(
                summary=validated_input.service,
                start_time=start_dt,
                end_time=end_dt
            )
            return {"result": f"Agendamento confirmado! Link do evento: {result.get('link')}"}

        elif intent == "cancel":
            if not validated_input.cancellation_id:
                return {"error": "Preciso do ID do evento para cancelar."}

            service.cancel_event(event_id=validated_input.cancellation_id)
            return {"result": "Agendamento cancelado com sucesso."}

        # A intenção 'check_availability' requer uma implementação mais complexa
        # usando a API 'freebusy', omitida aqui por simplicidade.
        else:
            return {"error": "Esta ação de agendamento ainda não é suportada."}

    except Exception as e:
        return {"error": f"Ocorreu um erro ao acessar o Google Agenda: {e}"}

scheduling_subgraph = execute_scheduling_action