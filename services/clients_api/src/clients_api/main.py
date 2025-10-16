# services/clients_api/src/clients_api/main.py (VERSÃO CORRIGIDA)
from fastapi import FastAPI
from .api.router import api_router # <-- CORREÇÃO: Importa o router agregador

app = FastAPI(title="Clients API - Vizu")

# Inclui o router agregador na aplicação, com um prefixo global de versão
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Monitoring"])
def health_check():
    return {"status": "ok"}