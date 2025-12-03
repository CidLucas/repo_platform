Lib: `vizu_db_connector`

O que a lib faz
- Fornece utilitários para conexão e operações com PostgreSQL (SQLModel / Alembic helpers), migrations e helpers de sessão.

Observações técnicas
- Facilita criação de engines, sessions e convenções de naming.
- Contém utilitários para seed data usados por `scripts/run_seeds.py`.

Dependências
- SQLModel / SQLAlchemy
- alembic
- psycopg[binary]

Stack e versões
- PostgreSQL 15+ (dev usa 15-alpine por padrão no compose)
- Python 3.11+

Riscos / recomendações
- Risco: mudanças em SQLModel/SQLAlchemy podem requerer migrar templates Alembic.
- Recomendações:
  - Incluir um comando de smoke test (connect + simple query) no CI.
  - Validar variáveis de conexão em `.env.example` e documentar portas no README.
