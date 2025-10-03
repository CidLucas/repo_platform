# src/atendente_api/main.py

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Importa o roteador que definimos em api/routes.py
from .api.routes import router as api_router

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="Atendente API - Vizu",
    version="1.0.0",
    description="Microserviço responsável pela lógica do Atendente Virtual Inteligente da Vizu.",
)

# Inclui todas as rotas definidas no nosso roteador da API
app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """
    Endpoint raiz para um health check simples.
    """
    return """
    <html>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>Atendente API - Vizu</h1>
            <p>Status: Ativo</p>
            <p>Acesse a documentação em <a href="/docs">/docs</a>.</p>
        </body>
    </html>
    """

# --- Bloco de Execução para Desenvolvimento Local ---
if __name__ == "__main__":
    uvicorn.run(
        "atendente_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )