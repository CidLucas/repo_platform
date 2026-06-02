# Test Cases — 0.1 frontdesk — 20260602_0031

**Skill:** frontdesk  
**Expected behavior:** LLM-driven routing via `route_to_specialist` tool to correct specialist agent  
**Client ID:** 6446d4fa-b845-4d1b-b3a3-ceed2dda6d44

---

## Test Cases

| # | Message (PT-BR) | Expected Slug | Phrasing Style |
|---|---|---|---|
| TC1 | "Quero ver o relatório financeiro do mês passado" | financeiro | Formal, explicit financial intent |
| TC2 | "meus clientes tão sumindo, como tô em relação ao churn?" | crm | Informal, implicit CRM/churn intent |
| TC3 | "Preciso agendar uma reunião com o time de vendas para quinta-feira às 15h" | agenda | Formal, explicit scheduling |
| TC4 | "Qual é a tendência de crescimento do faturamento nos últimos 6 meses e o que isso significa pro negócio?" | data-analyst ou strategy | Formal, multi-dimensional analytics |
| TC5 | "quero fazer uma cotação de arroz e feijão com meus fornecedores" | compras | Informal, explicit procurement/RFQ |

---

## Notes
- TC1: Core financial routing — should hit `financeiro` specialist
- TC2: Informal CRM with keyword "churn" — known routing gap per routing-test-results-20260601
- TC3: Agenda scheduling — expected to hit `agenda` slug
- TC4: Multi-dimensional (trend + strategic) — may hit `data-analyst` or `strategy` (synthesis intent)
- TC5: RFQ/compras — informal phrasing, keyword "cotação" + "fornecedores"
