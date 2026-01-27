import logging

from pythonjsonlogger import jsonlogger


def setup_structured_logging():
    """
    Configura o logger raiz do Python para emitir logs estruturados em JSON.

    Esta função remove handlers existentes, cria um formatador JSON que inclui
    automaticamente os campos de trace e span do OpenTelemetry, e adiciona um
    handler para enviar os logs para a saída padrão.
    """
    logger = logging.getLogger()

    # Remove handlers existentes para evitar duplicação de logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Cria um handler para a saída padrão (console)
    handler = logging.StreamHandler()

    # Cria o formatador JSON
    # Os campos 'trace_id' e 'span_id' são adicionados automaticamente pelo OpenTelemetry
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s %(trace_id)s %(span_id)s'
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Silencia loggers muito verbosos de bibliotecas de terceiros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("langfuse").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
