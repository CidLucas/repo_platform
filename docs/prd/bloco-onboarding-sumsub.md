# PRD: Serviço de Onboarding KYC/KYB/Counterparty — Bloco

**Status:** Rascunho  
**Autor:** Lucas Cruz  
**Data:** 2026-05-25  
**Versão:** 0.2  
**Cliente:** Bloco (cross-border trading)  
**Contexto:** Consultoria externa — serviço independente do Blu

---

## Problema / Oportunidade

A Bloco precisa de um processo de onboarding regulatório para seus clientes (KYC/KYB) e terceiros (Counterparty), usando SumSub como motor de verificação. O fluxo do SumSub SDK é técnico e árido — usuários ficam perdidos sobre quais documentos enviar, o que é aceito e como avançar. Além disso, o estado do onboarding precisa estar acessível para um agente de IA que guia o usuário em tempo real. A plataforma deve suportar múltiplos idiomas (PT-BR no mínimo, com extensibilidade para EN e outros).

---

## Usuário Alvo

- **Primário:** Clientes da Bloco — empresas e pessoas físicas que fazem cross-border trading e precisam passar pelo processo de KYC/KYB antes de operar.
- **Secundário:** Terceiros (Counterparty) — pessoas físicas ou jurídicas que farão negócios com os clientes da Bloco, e precisam de validação básica antes de serem aceitos como contraparte.

---

## Metas

- [ ] Integrar SumSub para os 3 perfis de verificação (KYC, KYB, Counterparty) em até 2 meses
- [ ] Disponibilizar agente de IA que guia o usuário durante o onboarding via widget na plataforma web da Bloco
- [ ] Expor estado do onboarding via API para consumo pelo agente
- [ ] RAG funcional com base de conhecimento sobre documentos aceitos, processo e FAQ (alimentada e mantida pela Bloco)
- [ ] Suporte multi-idioma (PT-BR + EN, extensível)

---

## Non-Goals (fora do escopo)

- Construção do frontend (feito pelo time da Bloco)
- Substituição do SumSub SDK — o agente é complementar, não concorrente
- Acesso direto do agente à API do SumSub
- Integrações com WhatsApp, Telegram ou outros canais (apenas web)
- Automação de aprovação/rejeição — o SumSub é a fonte da verdade
- Penny Drop / Bank Account Verification europeu (fora do escopo BR por ora)

---

## Background e Contexto

O SumSub é uma plataforma de KYC/KYB que expõe:
- **WebSDK 2.0** — widget embeddable no frontend que guia o usuário no upload de documentos e liveness
- **API REST** — criação de applicants, geração de access tokens, upload de documentos, consulta de status
- **Webhooks** — notificações em tempo real de eventos (`applicantReviewed`, etc.) com verificação HMAC via header `X-Payload-Digest`

**Importante:** Webhooks do SumSub **não contêm PII** — apenas IDs e status. Para obter dados do applicant, é necessário chamar `GET /resources/applicants/{applicantId}`.

O serviço a ser construído é uma **API intermediária** (FastAPI) que:
1. Recebe requisições do backend/frontend da Bloco
2. Orquestra chamadas ao SumSub (HMAC-signed)
3. Persiste estado do onboarding para consumo pelo agente
4. Expõe endpoints do agente (chat + contexto)
5. Integra com a biblioteca vetorial da Bloco (RAG)

---

## Premissas

- Backend e frontend da Bloco já existem — a entrega é somente o serviço de onboarding + agente como API
- Stack do serviço: Python + FastAPI (preferência do Lucas; a confirmar com a Bloco)
- SumSub contratado pela Bloco; levels/flows configurados no dashboard deles
- A biblioteca vetorial (RAG) já existe na Bloco — a integração será feita com a API deles
- A base RAG será alimentada e mantida pela própria Bloco
- Compliance regulatório é responsabilidade do SumSub
- Prazo: 2 meses para os 3 perfis + agente completos

---

## Os 3 Perfis de Verificação

### Perfil 1 — KYC (Know Your Customer)
Verificação de pessoa física (cliente da Bloco).

**Fluxo SumSub:**
1. `POST /resources/applicants?levelName={kyc_level}` com `externalUserId` + `fixedInfo` (country: BRA)
2. `POST /resources/accessTokens?userId={externalUserId}&levelName={kyc_level}` → retorna `token` para o WebSDK
3. Usuário completa no WebSDK: upload de doc + selfie/liveness
4. SumSub envia `applicantReviewed` webhook → nosso serviço persiste resultado
5. `GET /resources/applicants/{applicantId}` para buscar dados completos (PII não vem no webhook)

**Documentos aceitos (Brasil):**
- CPF: `TAX_PAYER_NUMBER_DOC` + `country: BRA`
- RG: `ID_CARD` + `country: BRA`
- CNH: `DRIVERS` + `country: BRA`
- Passaporte: `PASSPORT` + `country: BRA`

**Checks incluídos no level (a configurar):** AML Screening, Liveness, Address Verification

---

### Perfil 2 — KYB (Know Your Business)
Verificação de pessoa jurídica (empresa cliente da Bloco).

**Fluxo SumSub:**
1. `POST /resources/applicants?levelName={kyb_level}` com `type: company` + `fixedInfo.companyInfo` (companyName + country: BRA obrigatórios)
2. Auto KYB: Corporate Registry Check (busca CNPJ na Receita Federal) + Corporate AML Screening
3. Full KYB: upload de documentos corporativos + verificação de UBOs/diretores (cada um passa por KYC individual vinculado)
4. Status da empresa sincroniza com status das partes associadas

**Documentos corporativos aceitos:**
- Contrato social / Estatuto
- Comprovante de endereço
- Quadro societário
- Certidão de incorporação

**Partes associadas verificadas:** UBOs, Sócios, Diretores, Representantes legais

---

### Perfil 3 — Counterparty
Validação básica de terceiros (sem liveness, sem upload de documento físico).

**Diferencial:** Usa a verificação nativa do SumSub via CPF/CNPJ diretamente na Receita Federal — sem necessidade de foto ou selfie.

**Para Pessoa Física (CPF):**
- `idDocType: TAX_PAYER_NUMBER_DOC`, `country: BRA`, `number: {CPF}`
- SumSub consulta Receita Federal e retorna:
  - `registrationStatus`: REGULAR | PENDENTE | SUSPENSA | NULA | CANCELADA | TITULAR FALECIDO
  - `dob`: data de nascimento (para verificar maioridade)
  - Violations geradas automaticamente: `DEAD`, `PERSON_IS_MINOR`, `INVALID_DOC_NUMBER`, `INVALID_ID_STATUS`

**Para Pessoa Jurídica (CNPJ):**
- Corporate Registry Check via KYB level simplificado (Auto KYB sem documentos)
- Verifica situação cadastral na Receita Federal

**Adicional — Conta Bancária:**
- Dados bancários coletados via formulário próprio (não via SumSub)
- Validados e armazenados no serviço para repasse ao backend da Bloco

---

## Arquitetura do Serviço

```
Frontend Bloco (WebSDK embutido + widget do agente)
    │
    ├─► POST  /onboarding/init              → Cria applicant + retorna access token para WebSDK
    ├─► GET   /onboarding/status/{id}       → Status atual do onboarding
    ├─► POST  /agent/chat                   → Mensagem → resposta do agente (RAG + contexto)
    └─► GET   /agent/context/{id}           → Contexto do onboarding para o agente

SumSub (externo)
    └─► POST  /webhooks/sumsub              → applicantReviewed + outros eventos
                                              Valida X-Payload-Digest (HMAC SHA256)
                                              Persiste estado internamente
```

---

## Contrato de API

### POST /onboarding/init
```json
Request:
{
  "userId": "string",
  "profileType": "kyc | kyb | counterparty",
  "email": "string (opcional)",
  "name": "string (opcional)",
  "companyName": "string (KYB obrigatório)",
  "taxId": "string (CPF/CNPJ — Counterparty obrigatório)"
}

Response:
{
  "applicantId": "string",
  "accessToken": "string",
  "expiresAt": "datetime"
}
```

### POST /agent/chat
```json
Request:
{
  "applicantId": "string",
  "message": "string",
  "sessionId": "string",
  "language": "pt-BR | en (default: pt-BR)"
}

Response:
{
  "reply": "string",
  "suggestions": ["string"]
}
```

### POST /webhooks/sumsub
```
Header: X-Payload-Digest (HMAC SHA256 do body — validar antes de processar)
Header: X-Payload-Digest-Alg: HMAC_SHA256_HEX

Body (applicantReviewed — GREEN):
{
  "applicantId": "string",
  "externalUserId": "string",
  "type": "applicantReviewed",
  "reviewStatus": "completed",
  "reviewResult": { "reviewAnswer": "GREEN" },
  "levelName": "string",
  "applicantType": "individual | company"
}

Body (applicantReviewed — RED):
{
  ...
  "reviewResult": {
    "reviewAnswer": "RED",
    "rejectLabels": ["BAD_PROOF_OF_IDENTITY"],
    "reviewRejectType": "RETRY | FINAL"
  }
}
```

> ⚠️ PII não vem no webhook. Após receber, chamar `GET /resources/applicants/{applicantId}` para dados completos.

---

## Modelo de Estado do Onboarding (Storage Interno)

```json
{
  "applicantId": "string",
  "externalUserId": "string",
  "profileType": "kyc | kyb | counterparty",
  "reviewStatus": "init | pending | completed | onHold",
  "reviewAnswer": "GREEN | RED | null",
  "rejectLabels": ["string"],
  "reviewRejectType": "RETRY | FINAL | null",
  "stepsCompleted": ["idDoc", "selfie", "aml"],
  "stepsPending": ["address"],
  "levelName": "string",
  "language": "pt-BR",
  "bankAccount": { ... },
  "updatedAt": "datetime"
}
```

---

## Métricas de Sucesso

- [ ] Os 3 perfis de verificação funcionando end-to-end em staging (sandbox SumSub)
- [ ] Agente responde perguntas sobre processo com precisão ≥ 85% (avaliação manual)
- [ ] Webhook recebe e processa eventos com latência < 2s
- [ ] Verificação HMAC funcional (zero webhooks processados sem validação)
- [ ] API documentada (OpenAPI/Swagger) com exemplos para o time da Bloco
- [ ] Suporte PT-BR e EN no agente
- [ ] Entrega em 2 meses

---

## Perguntas Abertas

- [ ] Stack do backend da Bloco? (para definir autenticação entre sistemas)
- [ ] Qual banco de dados/infraestrutura está disponível no ambiente deles?
- [ ] Os levels do SumSub já estão criados no dashboard ou precisamos criar junto?
- [ ] API da biblioteca vetorial da Bloco — como é o contrato de integração?
- [ ] O widget do agente será um componente React entregue por nós ou só a API?
- [ ] Como será feita a autenticação entre o frontend da Bloco e nossa API? (JWT? API Key?)
- [ ] Ambiente de staging/sandbox do SumSub disponível para testes?
- [ ] Para KYB — Auto KYB ou Full KYB? (impacta escopo de documentos e UBOs)
- [ ] Para Counterparty — conta bancária: armazenar onde? Repassar via webhook para o backend deles?
