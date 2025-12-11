from analytics_api.api.endpoints import (  # Garanta que todos estão importados
    dashboard,
    deep_dive,
    rankings,
)
from fastapi import APIRouter

api_router = APIRouter()

# Prefixos podem precisar de ajuste conforme o frontend espera
api_router.include_router(dashboard.router, prefix="/dashboard") # /api/v1/dashboard/home
api_router.include_router(rankings.router, prefix="")  # /api/v1/analytics/clientes/overview
api_router.include_router(deep_dive.router, prefix="")   # /api/v1/analytics/cliente/{nome}
