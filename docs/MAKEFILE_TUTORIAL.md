Tutorial: usar este repo via `Makefile` (Quick-start e troubleshooting)

Contexto
Este monorepo é desenvolvido para rodar via `docker compose` (dev) e contém serviços Python empacotados com Poetry. O `Makefile` expõe targets úteis para desenvolvimento, manutenção e debugging.

Pré-requisitos
- Docker & Docker Compose (versão compatível com Compose v2+)
- Git
- Para rodar localmente sem containers, usar Poetry (3.11+). Recomenda-se evitar rodar scripts que dependem de instalação pip no Python do sistema (macOS) — preferir execução em container.

Comandos essenciais (copiar/colar no zsh)

- Build e levantar infra completa
```bash
make up                # docker compose up --build para todos os serviços
make ps                # mostra os containers em execução
```

- Parar e limpar
```bash
make down              # docker compose down
```

- Logs
```bash
make logs service=atendente_core   # ver logs de um serviço
```

- Rodar migrations / status
```bash
make migrate-status     # mostra status das migrations
make migrate-prod       # (prod) aplicar migrations (use com cuidado)
```

- Testes (por serviço)
```bash
cd services/atendente_core
poetry install
poetry run pytest
```

- Chat (endpoint de desenvolvimento)
```bash
# Quando docker compose está up, atendente_core fica exposto na porta 8003 no host
make chat               # target que chama o endpoint /chat local com uma mensagem de teste
```

- Batch run (gera tráços no Langfuse local)
```bash
# Recomendado: executar via Makefile que roda o script dentro do container
make batch-run
# O target `batch-run` executa `python /app/scripts/batch_run.py` dentro de `vizu_atendente_core` container
```

- Verificação Langfuse (local)
```bash
make langfuse-check     # checa se Langfuse local está acessível em http://host.docker.internal:3000
```

Troubleshooting comum

- Erro PEP-668 / `externally-managed-environment` ao rodar scripts no macOS
  - Causa: script tentou instalar pacotes no Python do sistema.
  - Solução: executar `make batch-run` (o Makefile executa o script dentro do container) ou `docker exec -it <container> python /app/scripts/batch_run.py`.

- Serviço não conecta ao MCP (tool pool)
  - Verifique logs de `tool_pool_api` e `atendente_core`.
  - Verifique variáveis de ambiente `MCP_HOST`/`MCP_PORT` e se o `tool_pool_api` registrou ferramentas em logs (strings com tools carregadas).

- Falha por dependência faltante em runtime (ex.: langchain-ollama)
  - Verifique `pyproject.toml` do serviço e `poetry.lock` do workspace.
  - Rebuild do container: `docker compose up --build tool_pool_api`.

- Verificação de traces no Langfuse
  - Abra `http://localhost:3000` ou `http://host.docker.internal:3000` dependendo do ambiente.
  - Se os traços não aparecerem, confirme `LANGFUSE_HOST` nas variáveis de ambiente dos containers e reinicie.

Boas práticas
- Evitar executar scripts que alteram dependências no Python do sistema — use containers ou ambientes Poetry controlados.
- Rodar `make ps` e `make logs` antes de abrir issues sobre falhas — logs contêm as melhores pistas.
- Documentar mudanças em `docs/` e manter o `CHANGELOG` atualizado por release.
