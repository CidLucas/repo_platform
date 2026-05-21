# scripts/

Scripts utilitários para manutenção, seeding e auditoria do Blu.
Executar localmente (fora do container) com `poetry run python scripts/<nome>.py` a menos que indicado.

---

## Seeding / Setup

| Script | Uso | Quando executar |
|---|---|---|
| `seed_google_oauth_vault.py` | Popula vault de OAuth Google (Calendar, Drive) | Setup inicial / novas credenciais |
| `seed_platform_knowledge.py` | Insere knowledge base de plataforma no Supabase | Setup inicial / atualização de knowledge |
| `seed_test_suppliers.py` | Cria fornecedores de teste no banco | Ambiente de dev/staging |

## Langfuse / Prompts

| Script | Uso | Quando executar |
|---|---|---|
| `audit_langfuse_prompts.py` | Lista todos os prompts cadastrados no Langfuse, detecta orphans e duplicatas | Revisão de prompts, antes de deletar/migrar |
| `create_analytics_prompts.py` | Cria/atualiza prompts do agente de analytics no Langfuse | Após mudar templates de analytics |
| `create_rfq_prompts.py` | Cria/atualiza prompts do agente RFQ no Langfuse | Após mudar templates de RFQ |

## Dados / Analytics

| Script | Uso | Quando executar |
|---|---|---|
| `bq_export.py` | Exporta dados do BigQuery para arquivo local | Análise offline / debugging de analytics |
| `check_analytics_views.sh` | Verifica se as views analíticas do Supabase estão atualizadas | Após migrations que alteram views |

## Docs

| Script | Uso | Quando executar |
|---|---|---|
| `generate_agent_docs.py` | Gera documentação dos agentes a partir do código | Antes de publicar docs / revisão de arquitetura |

---

> Migrações de schema (Supabase) ficam em `supabase/migrations/` — não use Alembic.
> Para shell de banco local: `make db-shell`
