# Onboarding — Mapa de Contexto

> Última atualização: 2026-05-21
> Status: Implementado. Onboarding wizard + provisionamento de tenant ativo.

---

## 1. Fluxo de Alto Nível

```
apps/landing (React SPA)
  → Wizard multi-step (company_profile, brand_voice, team, policies)
  → Supabase Auth (signup)
  → Edge function blu_auth → cria registro em clientes_blu
  → População de onboarding_state (JSONB em clientes_blu)
  → onboarding_completed_at setado ao final
  → Redirect para apps/blu_v3 (/app)
```

---

## 2. Campos Populados no Onboarding

Todos os dados coletados no wizard são persistidos em `clientes_blu`:

| Campo | O que captura |
|---|---|
| `company_profile` | Setor, tamanho, proposta de valor, produtos/serviços, CNPJ |
| `brand_voice` | Tom de voz, vocabulário, exemplos de comunicação |
| `team_structure` | Times, nomes, responsabilidades |
| `policies` | Política de crédito, prazo de pagamento, compliance |
| `onboarding_state` | Estado do wizard (quais steps foram completados) |
| `onboarding_completed_at` | Timestamp de conclusão |
| `cpf_cnpj` | Identificação fiscal da empresa |

---

## 3. Guarda no Frontend (blu_v3)

O app verifica se o onboarding foi completado antes de renderizar:

```typescript
// HomeApp.tsx
const firstRun = !localStorage.getItem('blu_has_data')
// FirstRunOverlay só aparece se firstRun && !hasData
```

- `blu_has_data` é setado no localStorage após primeira ingestão de dados
- O overlay de onboarding NÃO aparece se o usuário já tem dados (mesmo que `onboarding_completed_at` seja null)
- Pop-out é não-bloqueante — usuário pode fechar e voltar depois

---

## 4. Provisionamento de Tenant

Ao criar conta:
1. Supabase Auth cria `auth.users`
2. Edge function `blu_auth` cria `clientes_blu` com `tier = 'free'`
3. `external_user_id` = `auth.users.id` (JWT sub)
4. `collection_rag` = `default_collection` (namespace vetorial no pgvector)
5. Agentes default são habilitados em `client_enabled_agents`

---

## 5. Dados de Desenvolvimento

| Campo | Valor |
|---|---|
| Email | lucascid@poli.ufrj.br |
| external_user_id | 4f3a5908-6d5d-46fb-93b4-4938ef754314 |
| tier | free |
| onboarding_state | `{}` (não completado em dev) |

Para contornar o overlay em dev: setar `blu_has_data = 'true'` no localStorage do browser.

---

## 6. Extensão do Fluxo: HITL Documental

Documentos aprovados durante o onboarding (ou posteriormente) seguem este caminho:

```
Upload (uploaded_files_metadata)
  → OCR/extração de texto
  → client_knowledge_documents (status: pending)
  → approval_request (action_type: document_approval)
  → Usuário aprova na UI
  → Embedding gerado → pgvector
  → client_knowledge_documents (status: active)
  → Disponível para RAG em toda a plataforma
```

Cobertura por tipo de documento rastreada em `knowledge_agent_requirements` (com `coverage_threshold` por `agent_slug`).
