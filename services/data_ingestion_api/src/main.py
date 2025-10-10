# data_ingestion_api/src/main.py

from fastapi import FastAPI
from src.routes import router as credential_router
import logging.config

# Padrão Vizu: Configuração de Logs
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'INFO',
        },
    },
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)


# Definição do Aplicativo FastAPI
app = FastAPI(
    title="Vizu Data Ingestion API",
    description="Microserviço responsável por receber credenciais e orquestrar a ingestão de dados.",
    version="0.1.0-alpha",
)

# Registro dos Routers (Implementando Modularização)
app.include_router(credential_router)

# Endpoint básico de saúde (Health Check)
@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Vizu Data Ingestion API is running."}

# O servidor Uvicorn (comando: uvicorn src.main:app) rodará este objeto 'app'