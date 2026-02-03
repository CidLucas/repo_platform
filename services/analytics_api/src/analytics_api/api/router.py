from analytics_api.api.endpoints import (
    auth,
    dashboard,
    deep_dive,
    indicators,
    ingestion,
    rankings,
)
from fastapi import APIRouter

api_router = APIRouter()

# Prefixos podem precisar de ajuste conforme o frontend espera
api_router.include_router(dashboard.router, prefix="/dashboard")  # /api/dashboard/...
api_router.include_router(rankings.router, prefix="")  # /api/clientes, /api/fornecedores, /api/produtos, /api/pedidos
api_router.include_router(deep_dive.router, prefix="")  # /api/cliente/{nome}, /api/fornecedor/{nome}
api_router.include_router(indicators.router, prefix="", tags=["Indicators"])  # indicators.router already has /indicators prefix
api_router.include_router(auth.router, prefix="")  # /api/auth/google/login etc
api_router.include_router(ingestion.router, prefix="")  # /api/ingest/recompute
