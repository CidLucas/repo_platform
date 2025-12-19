# Vizu Tools Service

Small collection of lightweight utility services for Vizu (monitoring, helpers).

Run locally:

1. Install dependencies (Poetry):

```bash
cd services/tools
poetry install
poetry run uvicorn tools.main:app --reload --host 0.0.0.0 --port 8001
```

Endpoints:
- GET `/monitor-feature?domain=example.com&query=produtos`
- GET `/monitor-keywords?domain=example.com&keywords=one&keywords=two`
- GET `/monitor-company?company=MyCo&domains=...`
