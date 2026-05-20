# Blu — Built-in Routines Catalog v2.1
## Routines State Machine Reference

**Document Purpose:** Product & Engineering reference for all built-in recurring routines in the Blu bureau. Each routine runs with minimal configuration and is expressed as logical data steps (not function names), prioritizing deterministic transformations over LLM calls.

**Last Updated:** 2026-05-20

---

## 1. Routines vs. Actions

### What is a Routine?
A **routine** is a recurring, automated process that runs on a schedule or trigger, collects data, performs deterministic transformations, produces an artifact (report, card, alert), and may pause for owner approval. Routines are the bureau's habits — they run whether or not the owner asks.

### What is an Action?
An **action** is a capability the owner invokes on demand by navigating to a room, clicking a button, running a query, or requesting a calculation. Actions are tools in the desk drawers, not scheduled agents.

### Reclassified: Actions (Not Routines)
The following were removed from the routines list because they are on-demand capabilities, not recurring processes:

| Capability | Where It Lives | Why It's an Action |
|------------|----------------|-------------------|
| **Auditoria de Aprovações** | Admin → Auditoria | Searchable, filterable log. Owner queries when needed. |
| **Export de Dados Críticos** | Admin → LGPD | User-triggered data portability export. Required by LGPD. |
| **CAC (Custo de Aquisição)** | Estratégia dashboard | DB calculation fetched on page load. No schedule needed. |
| **Diagnóstico de Integrações** | Admin → Integrações | Deep diagnostic run on demand when owner suspects issues. |

---

## 2. Routine Dependencies & Trigger Architecture

### Principle: Event-Triggered Chains, Not Cron Sequences
Routines that depend on each other should not rely on staggered cron times ("run A at 07:00, run B at 07:15, hope they finish in order"). Instead, the completion of one routine should **trigger** the next routine and pass its output as context.

### The Morning Chain
The morning routines form a single event chain initiated by one cron trigger:

```
[CRON: Daily @ 07:00] 
  → triggers → Sincronização da Manhã
      → on success → triggers → Radar de Prazos (with integration health context)
          → on complete → triggers → Plano do Dia (with health + deadlines context)
```

**Why this matters:** If Sincronização da Manhã detects a bank integration failure, it passes that context to Plano do Dia, which surfaces it in the briefing. If we used separate cron jobs, Plano do Dia might run before Sincronização finishes, or miss the failure context entirely.

### Independent Routines
Routines in other rooms (Financeiro, Compras, Clientes, etc.) run on their own cron triggers and do not participate in the morning chain. They produce artifacts in their own rooms and may surface to Home → Decidir Agora if urgent, but they are not sequentially dependent.

### Friday Exception
On Fridays, the evening chain replaces Digest do Fim de Dia:
```
[CRON: Friday @ 17:00]
  → triggers → Resumo Semanal
      → on complete → no further trigger (replaces Digest)
```

---

## 3. Home (Cross-Agent) Routines

### 3.1 Sincronização da Manhã
| Field | Detail |
|-------|--------|
| **Name** | Sincronização da Manhã |
| **Description** | Validates that all integrations are connected and data is fresh. Flags disconnects or stale data. Triggers the rest of the morning chain upon completion. |
| **Default Trigger** | Cron — Daily @ 07:00 |
| **Next Trigger** | On success → triggers Radar de Prazos |
| **Configuration** | None |
| **Agent Owner** | Gerente (Cross-Agent) |

**Logical Flow:**
1. **Fetch** last successful sync timestamp for each integration (bank, ERP, email, calendar, CRM, SEFAZ).
2. **Compare** timestamps against freshness thresholds (e.g., bank: 2 hours, ERP: 24 hours).
3. **Run** quick latency pings to each API endpoint.
4. **Assemble** health report: per-integration status (healthy / stale / failing) + last sync time + error details if failing.
5. **If** any integration is stale or failing:
   - Assemble alert card naming the integration, issue type, last successful sync time, and business impact (e.g., "bank disconnected — cash flow alerts paused").
   - Push to Home → Urgent.
   - Notify owner: "Blu precisa de atenção: [integration] desconectado."
6. **Trigger** Radar de Prazos, passing the integration health report as context.

---

### 3.2 Radar de Prazos
| Field | Detail |
|-------|--------|
| **Name** | Radar de Prazos |
| **Description** | Scans calendar events, fiscal obligations, contract renewals, and tax deadlines. Categorizes by proximity and feeds into Plano do Dia. Triggered by Sincronização da Manhã completion. |
| **Default Trigger** | Event — triggered by Sincronização da Manhã completion |
| **Next Trigger** | On complete → triggers Plano do Dia |
| **Configuration** | None |
| **Agent Owner** | Gerente (Cross-Agent) |

**Logical Flow:**
1. **Receive** integration health context from Sincronização da Manhã (used to skip checks on failed integrations).
2. **Fetch** calendar events with deadlines (next 15 days).
3. **Fetch** fiscal obligations from CNPJ regime (DAS, ISS, IRPJ, CSLL, etc.).
4. **Fetch** contract end dates from Documentos room (next 30 days).
5. **Deduplicate** items already present in calendar.
6. **Categorize** by proximity:
   - **3 days:** Urgent — requires action today
   - **7 days:** Attention — plan this week
   - **15 days:** FYI — on the horizon
7. **If** any 3-day items exist, push to Home → Decidir Agora.
8. **Push** 7-day and 15-day items to Home → Visão da Semana.
9. **Trigger** Plano do Dia, passing:
   - Deadline radar data (urgent, attention, FYI buckets)
   - Integration health report (from Sincronização)

---

### 3.3 Plano do Dia
| Field | Detail |
|-------|--------|
| **Name** | Plano do Dia |
| **Description** | Aggregates all pending decisions, calendar events, urgent communications, overdue items, integration health, and deadline radar into a single-page morning briefing. Triggered by Radar de Prazos completion. |
| **Default Trigger** | Event — triggered by Radar de Prazos completion |
| **Configuration** | Time of day only (for the initial cron that starts the chain) |
| **Agent Owner** | Gerente (Cross-Agent) |

**Logical Flow:**
1. **Receive** context from Radar de Prazos:
   - Deadline radar data (3/7/15 day buckets)
   - Integration health report
2. **Fetch** pending decisions >24h from all rooms (Financeiro, Compras, Documentos, Clientes).
3. **Fetch** today's calendar events and urgent unread emails (flagged or from known contacts).
4. **Fetch** overdue items (invoices, tasks, follow-ups, unshipped orders).
5. **Score** each item by urgency × business value × deadline proximity using deterministic weights.
6. **Categorize** into buckets:
   - **Decidir Agora:** approvals needed, urgent deadlines today, integration failures
   - **Executar Hoje:** meetings, scheduled tasks, follow-ups
   - **Acompanhar:** FYI alerts, non-urgent deadlines
7. **Assemble** single-page briefing card with top 5 priorities + full scrollable list.
8. **If** Monday, append "Visão da Semana" subsection with week-ahead calendar highlights.
9. **Push** to Home → Plano de Hoje. Optional email digest.

---

### 3.4 Digest do Fim de Dia
| Field | Detail |
|-------|--------|
| **Name** | Digest do Fim de Dia |
| **Description** | Summarizes what was accomplished, what remains pending for tomorrow, and any items that need a quick night decision. |
| **Default Trigger** | Cron — Daily @ 18:00 |
| **Exception** | Suppressed on Fridays (Resumo Semanal takes its place). |
| **Configuration** | Time of day only |
| **Agent Owner** | Gerente (Cross-Agent) |

**Logical Flow:**
1. **Fetch** all decisions approved, rejected, or edited today across all rooms.
2. **Fetch** all automated actions executed by agents today.
3. **Fetch** items still pending (carried to tomorrow).
4. **Fetch** new items created today that need future attention.
5. **Calculate** delta: resolved vs. opened.
6. **Identify** "night decisions" — items that, if approved before morning, would unblock the bureau's first routines (e.g., pending NF emission, urgent purchase order).
7. **Assemble** briefing card:
   - "Hoje no escritório" — what got done
   - "Para amanhã" — carryover items
   - "Decisões noturnas" — only if any exist
8. **Push** to Home → Plano de Hoje (tomorrow preview).
9. **If** night decisions exist, also push to Home → Urgent.

---

### 3.5 Resumo Semanal
| Field | Detail |
|-------|--------|
| **Name** | Resumo Semanal |
| **Description** | Friday recap highlighting decisions made, money moved, customers touched, blockers for next week, and a "what to bring into Monday" preview. Replaces the Friday Digest do Fim de Dia. |
| **Default Trigger** | Cron — Fridays @ 17:00 |
| **Configuration** | Day of week + time |
| **Agent Owner** | Gerente (Cross-Agent) |

**Logical Flow:**
1. **Fetch** weekly decision log (approved, rejected, edited by room).
2. **Fetch** financial movement summary (R$ in, R$ out, cash position change vs. Monday).
3. **Fetch** customer touchpoints (new customers acquired, follow-ups sent, reactivations attempted).
4. **Fetch** inventory events (orders placed, stock alerts triggered).
5. **Fetch** bureau health incidents (integration failures, errors).
6. **Fetch** blockers carried into next week (pending approvals, stalled deals, unresolved stock issues).
7. **Aggregate** by category and compare to prior week (trend arrows using simple week-over-week math).
8. **Identify** top 3 blockers that will hit Monday morning.
9. **Assemble** narrative report card:
   - "Esta semana..." — summary stats
   - "Decisões da semana" — count by room
   - "Movimentação financeira" — in/out/net
   - "Clientes" — new, touched, reactivated
   - "Segunda-feira traz..." — blockers + Monday calendar preview
10. **Push** to Home → Insights. Optional email digest.

---

## 4. Financeiro Routines

### 4.1 Relatório Mensal de Performance
| Field | Detail |
|-------|--------|
| **Name** | Relatório Mensal de Performance |
| **Description** | Generates a comprehensive P&L report comparing current month against last month and same month last year. Includes burn rate, receivables aging, and margin trends. |
| **Default Trigger** | Cron — 1st of month @ 08:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Financeiro |

**Logical Flow:**
1. **Fetch** revenue, COGS, and expenses for: current closed month, last month, same month last year.
2. **Fetch** cash position (start vs. end of month).
3. **Fetch** receivables aging buckets (0-30, 31-60, 61-90, 90+ days).
4. **Fetch** payables summary.
5. **Calculate** P&L, gross margin, net margin for each period.
6. **Calculate** MoM and YoY variances (absolute and %).
7. **Calculate** burn rate: monthly fixed costs ÷ ending cash.
8. **Flag** anomalies with deterministic rules:
   - Margin drop >5% vs. last month
   - Receivables 90+ bucket increase >10%
   - Burn rate >6 months runway
9. **Assemble** visual report card with charts (revenue trend, margin breakdown, aging bar chart) + narrative summary.
10. **Push** to Financeiro → Desk Surface. Notify owner.

---

### 4.2 Alerta de Fluxo de Caixa
| Field | Detail |
|-------|--------|
| **Name** | Alerta de Fluxo de Caixa |
| **Description** | Projects 7-day forward cash flow based on confirmed payables and expected receivables. Warns if projected balance goes below a configurable safety threshold. |
| **Default Trigger** | Cron — Daily @ 07:00 |
| **Configuration** | Minimum safety balance (R$) |
| **Agent Owner** | Financeiro |

**Logical Flow:**
1. **Fetch** current confirmed bank balance.
2. **Fetch** confirmed payables (next 7 days, exact amounts, due dates).
3. **Fetch** expected receivables (next 7 days, amounts weighted by customer payment reliability score based on historical on-time rate).
4. **Project** day-by-day balance by subtracting payables and adding probability-weighted receivables from current balance.
5. **Identify** first day (if any) where projected balance < safety threshold.
6. **If** negative projection detected:
   - Calculate deficit amount and day of risk.
   - Suggest actions: accelerate specific collections, delay non-critical payables, draw on credit line.
   - Assemble alert card.
   - Push to Financeiro → Urgent + Home.
7. **If** healthy, log silently.

---

### 4.3 Conciliação Bancária Sugerida
| Field | Detail |
|-------|--------|
| **Name** | Conciliação Bancária Sugerida |
| **Description** | Matches bank transactions against invoices and receipts. Surfaces unmatched items for owner review and approval. |
| **Default Trigger** | Cron — Mondays @ 09:00 |
| **Configuration** | Day of week |
| **Agent Owner** | Financeiro |

**Logical Flow:**
1. **Fetch** bank transactions (last 7 days).
2. **Fetch** ERP invoices issued and receipts recorded (same period).
3. **Run** deterministic fuzzy match:
   - Exact match: amount + date + counterparty name
   - Near match: amount within 1% + date within 2 days + fuzzy name similarity >85%
   - Group unmatched items.
4. **For** each unmatched bank transaction:
   - Search for best candidate match in ERP with confidence score.
   - If candidate found, present as "suggested match" with evidence.
   - If no candidate, flag as "manual review needed."
5. **Assemble** reconciliation card per unmatched item.
6. **Push** to Financeiro → Urgent.
7. **Await** owner approval per item (confirm match, reject match, mark manual).

---

### 4.4 Cobrança de Inadimplentes
| Field | Detail |
|-------|--------|
| **Name** | Cobrança de Inadimplentes |
| **Description** | Identifies overdue receivables beyond threshold. Drafts personalized cobrança messages, waiting for owner approval before sending. |
| **Default Trigger** | Cron — Wednesdays @ 10:00 |
| **Configuration** | Days overdue threshold (default: 15) |
| **Agent Owner** | Financeiro |

**Logical Flow:**
1. **Fetch** overdue receivables (age > threshold days).
2. **Fetch** customer profile: value tier, communication preference, last interaction, payment history.
3. **Segment** customers deterministically:
   - Chronic late payer (>3 late payments in 6 months) → firm tone
   - First-time late → gentle reminder
   - High-value customer → personalized, relationship-preserving tone
4. **Populate** message template with customer name, invoice numbers, amount, days overdue, and payment link.
5. **Assemble** batch approval card: customer list, message preview, channel (email/WhatsApp), total value at risk.
6. **Push** to Financeiro → Urgent.
7. **Await** owner approval: approve all, edit individual message, reject specific customers, or snooze.
8. **If** approved, send via selected channel and log.

---

### 4.5 Revisão de Margem
| Field | Detail |
|-------|--------|
| **Name** | Revisão de Margem |
| **Description** | Flags products or services with margin compression compared to last quarter. Surfaces probable cause. |
| **Default Trigger** | Cron — 15th of month @ 09:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Financeiro |

**Logical Flow:**
1. **Fetch** product/service margins (current month MTD).
2. **Fetch** product/service margins (last quarter average per SKU).
3. **Fetch** cost components if available.
4. **Calculate** margin delta per SKU: ((current - last quarter) / last quarter) × 100.
5. **Flag** items where:
   - Compression >5%, OR
   - Absolute margin <15%
6. **Determine** probable cause deterministically:
   - If cost increased and price stable → "custo subiu"
   - If price decreased and cost stable → "preço caiu"
   - If both changed → "mix de custo e preço"
   - If mix shift → "mudança no mix de vendas"
7. **Assemble** margin review card: flagged items table with old margin, new margin, delta, probable cause.
8. **Push** to Financeiro → Desk Surface.

---

### 4.6 DAS / Simples Nacional
| Field | Detail |
|-------|--------|
| **Name** | DAS / Simples Nacional |
| **Description** | Reminds owner of DAS generation/payment based on CNPJ fiscal regime. Pre-fills calculation values. |
| **Default Trigger** | Cron — 10th of month @ 08:00 |
| **Configuration** | Fiscal regime (MEI vs. Simples Nacional) |
| **Agent Owner** | Financeiro |

**Logical Flow:**
1. **Fetch** fiscal regime from CNPJ configuration.
2. **Fetch** YTD revenue for aliquota bracket calculation.
3. **Fetch** current month revenue.
4. **Calculate** DAS amount:
   - MEI: fixed value based on regime table
   - Simples Nacional: apply annex/aliquota to monthly revenue based on YTD bracket
5. **Determine** due date (typically 20th for Simples, varying for MEI).
6. **Assemble** payment card: amount due, due date, calculation breakdown, payment method suggestion (boleto, DARF, PIX).
7. **Push** to Financeiro → Urgent.
8. **Await** owner approval to redirect to payment gateway or generate document.

---

## 5. Compras / Estoque Routines

### 5.1 Alerta de Estoque Mínimo
| Field | Detail |
|-------|--------|
| **Name** | Alerta de Estoque Mínimo |
| **Description** | Monitors inventory levels and flags items below reorder point. Auto-learns reorder points from sales velocity if not manually configured. |
| **Default Trigger** | Cron — Daily @ 08:00 |
| **Configuration** | Reorder points per SKU (or auto-learn) |
| **Agent Owner** | Compras |

**Logical Flow:**
1. **Fetch** current inventory levels per SKU.
2. **Fetch** sales velocity (units/day, last 30 days).
3. **Fetch** supplier lead times.
4. **For** each SKU:
   - If manual reorder point configured: compare current stock vs. point.
   - If no manual point: calculate auto reorder point = (velocity × lead time) + safety stock (velocity × 3 days).
5. **Flag** SKUs where current stock < reorder point.
6. **Calculate** suggested reorder quantity = (velocity × 14 days) - current stock (minimum 0).
7. **Assemble** low-stock alert card per flagged SKU: current qty, threshold, suggested order qty, supplier.
8. **Push** to Compras → Urgent.

---

### 5.2 Sugestão de Compra
| Field | Detail |
|-------|--------|
| **Name** | Sugestão de Compra |
| **Description** | Based on sales velocity, stock levels, and lead times, suggests purchase orders to prevent stockouts in the next 2 weeks. |
| **Default Trigger** | Cron — Tuesdays @ 09:00 |
| **Configuration** | Day of week |
| **Agent Owner** | Compras |

**Logical Flow:**
1. **Fetch** sales velocity (last 60 days, trend-adjusted).
2. **Fetch** current stock levels.
3. **Fetch** supplier lead times.
4. **Fetch** open purchase orders (avoid double-ordering).
5. **Predict** stockout date per SKU: current stock ÷ velocity.
6. **Identify** SKUs with predicted stockout within 14 days.
7. **Calculate** order quantity = (velocity × 14 days) + safety stock - current stock - incoming open orders.
8. **Consolidate** items by supplier into draft purchase orders.
9. **Assemble** suggested PO cards per supplier: SKU list, quantities, estimated cost, expected delivery date.
10. **Push** to Compras → Desk Surface.
11. **Await** owner approval: approve PO, edit quantities, reject.

---

### 5.3 Revisão de Fornecedores
| Field | Detail |
|-------|--------|
| **Name** | Revisão de Fornecedores |
| **Description** | Analyzes recent invoices to flag price changes, delivery delays, or payment term shifts. |
| **Default Trigger** | Cron — 1st of month @ 10:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Compras |

**Logical Flow:**
1. **Fetch** purchase invoices (last 90 days).
2. **Fetch** promised delivery dates vs. actual receipt dates.
3. **Fetch** unit prices paid per SKU per supplier over time.
4. **Fetch** payment terms on each invoice.
5. **Calculate** per supplier:
   - Price trend: linear regression on unit price over time. Flag if slope >+5%.
   - Delivery performance: average (actual - promised) days. Flag if >3 days.
   - Terms change: compare current vs. first invoice terms.
6. **Assemble** supplier review card: flagged suppliers with evidence, impact assessment, renegotiation suggestion.
7. **Push** to Compras → Desk Surface.

---

### 5.4 Auditoria de Estoque
| Field | Detail |
|-------|--------|
| **Name** | Auditoria de Estoque |
| **Description** | Cross-checks physical inventory count against system records. Flags discrepancies. |
| **Default Trigger** | Cron — Last day of month @ 09:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Compras |

**Logical Flow:**
1. **Fetch** system inventory records per SKU.
2. **Fetch** physical count data (if entered via integration or manual input).
3. **Calculate** discrepancy per SKU: system qty - physical qty.
4. **Calculate** discrepancy value and %.
5. **Flag** SKUs where discrepancy >2% OR discrepancy value >R$ 500.
6. **Assemble** audit card: discrepancy table with probable causes (theft, recording error, returns not processed, unrecorded breakage).
7. **If** discrepancies found, push to Compras → Urgent.
8. **If** clean, log silently.

---

## 6. Clientes Routines

### 6.1 Follow-up Pós-Venda
| Field | Detail |
|-------|--------|
| **Name** | Follow-up Pós-Venda |
| **Description** | Drafts personalized check-in messages for customers who purchased X days ago. Strengthens relationship and surfaces dissatisfaction early. |
| **Default Trigger** | Cron — Daily @ 10:00 (rolling based on purchase date) |
| **Configuration** | Days after purchase (default: 7) |
| **Agent Owner** | Clientes |

**Logical Flow:**
1. **Fetch** sales where purchase_date = today - X days.
2. **Fetch** customer profile and communication preference.
3. **Fetch** product/service purchased.
4. **Check** if customer already received a follow-up this week (deduplicate).
5. **Select** follow-up template based on product category (physical goods, service, subscription).
6. **Populate** template with customer name, product name, purchase date.
7. **Assemble** batch approval card: customer list, message preview, channel.
8. **Push** to Clientes → Urgent.
9. **Await** owner approval: approve all, edit individual, reject.
10. **If** approved, send via channel and log.

---

### 6.2 Reativação de Clientes Dormidos
| Field | Detail |
|-------|--------|
| **Name** | Reativação de Clientes Dormidos |
| **Description** | Identifies customers with no purchase in 60/90/120 days. Drafts win-back offers waiting for owner approval. |
| **Default Trigger** | Cron — Thursdays @ 11:00 |
| **Configuration** | Inactivity threshold in days (default: 90) |
| **Agent Owner** | Clientes |

**Logical Flow:**
1. **Fetch** customers with last purchase > threshold days.
2. **Fetch** customer value tier (revenue, frequency, lifetime value).
3. **Segment** deterministically:
   - High LTV + 90 days → personal call + exclusive offer
   - Medium LTV + 90 days → discount email
   - Low LTV + 120 days → soft re-engagement or deprioritize
4. **Suggest** win-back action per segment (discount %, bundle, personal call).
5. **Draft** message per customer using template + personalization fields.
6. **Assemble** reactivation batch card: segments, offers, message previews, total customers.
7. **Push** to Clientes → Desk Surface.
8. **Await** owner approval.

---

### 6.3 Aniversário de Cliente VIP
| Field | Detail |
|-------|--------|
| **Name** | Aniversário de Cliente VIP |
| **Description** | Flags birthdays or company anniversaries for high-value customers, suggesting relationship touchpoints. |
| **Default Trigger** | Cron — Daily @ 08:30 |
| **Configuration** | None |
| **Agent Owner** | Clientes |

**Logical Flow:**
1. **Fetch** customer birthdays and company founding dates matching today.
2. **Fetch** VIP flag (top 20% by revenue or manual tag).
3. **Filter** to VIPs only.
4. **Check** if already acknowledged this year (avoid duplicates).
5. **Fetch** last touchpoint date.
6. **Suggest** action based on relationship depth:
   - Top 5% → gift suggestion + personal call
   - Next 15% → personalized message
7. **Assemble** VIP event card: customer name, event type, relationship context, suggested action.
8. **Push** to Clientes → Urgent.

---

### 6.4 NPS / Satisfação Leitura
| Field | Detail |
|-------|--------|
| **Name** | NPS / Satisfação Leitura |
| **Description** | Summarizes survey responses, calculates NPS, extracts themes, and flags urgent complaints using deterministic text processing. |
| **Default Trigger** | Cron — 1st of month @ 09:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Clientes |

**Logical Flow:**
1. **Fetch** survey responses from last month (scores 0-10 + open text).
2. **Calculate** NPS: % promoters (9-10) - % detractors (0-6).
3. **Process** open-ended text deterministically:
   - Keyword frequency count (complaint lexicon, praise lexicon)
   - Rule-based sentiment flag (presence of negative keywords + score 0-6)
4. **Extract** top 3 recurring themes by keyword frequency.
5. **Flag** urgent complaints: score ≤6 AND complaint keywords present.
6. **Assemble** NPS report card: score, trend arrow (vs. last month), top 3 themes, urgent complaints list.
7. **Push** to Clientes → Desk Surface.
8. **If** urgent complaints exist, also push to Home → Urgent.

---

### 6.5 Pipeline de Vendas Review
| Field | Detail |
|-------|--------|
| **Name** | Pipeline de Vendas Review |
| **Description** | Flags stalled deals with no activity >X days. Suggests next actions to reactivate. |
| **Default Trigger** | Cron — Mondays @ 09:00 |
| **Configuration** | Stalled threshold in days (default: 14) |
| **Agent Owner** | Clientes |

**Logical Flow:**
1. **Fetch** active opportunities from CRM.
2. **Fetch** last activity date per opportunity.
3. **Filter** stalled opportunities: last_activity_date > threshold days.
4. **Calculate** total stalled pipeline value.
5. **Suggest** next action per opportunity deterministically:
   - Early stage + no contact → "enviar proposta"
   - Proposal sent + no response → "ligar de follow-up"
   - Negotiation + silence → "oferecer desconto de fechamento"
   - Multiple stalls → "qualificar ou descartar"
6. **Assemble** pipeline review card: stalled deals table with value, days stalled, suggested action.
7. **Push** to Clientes → Urgent.
8. **Await** owner decision per deal: create task, snooze (remind in X days), or disqualify.

---

## 7. Agenda Routines

### 7.1 Preparação de Reunião
| Field | Detail |
|-------|--------|
| **Name** | Preparação de Reunião |
| **Description** | 15 minutes before any calendar event, pulls client history, open invoices, and last touchpoints to assemble a meeting brief. |
| **Default Trigger** | Event — 15 minutes before each calendar event |
| **Configuration** | None |
| **Agent Owner** | Agenda |

**Logical Flow:**
1. **Trigger** on calendar webhook: event starting in 15 minutes.
2. **Fetch** event details: attendees, subject, location.
3. **Match** attendees to CRM customer/prospect records by email domain or name.
4. **Fetch** customer history: last purchases, total revenue, open invoices.
5. **Fetch** last touchpoints (calls, emails, meetings).
6. **Fetch** financial status: payment history, any overdue balance.
7. **Assemble** meeting prep card:
   - Who: name, company, role
   - Context: relationship length, total spent, last interaction
   - Open items: unpaid invoices, pending proposals, support tickets
   - Suggested agenda: based on open items
8. **Push** to Agenda → Desk Surface + mobile notification.
9. **Expire** card 2 hours after event ends.

---

### 7.2 Bloqueio de Foco
| Field | Detail |
|-------|--------|
| **Name** | Bloqueio de Foco |
| **Description** | Suggests 2-hour deep-work blocks in low-meeting days. Respects owner preferences. |
| **Default Trigger** | Cron — Sundays @ 20:00 |
| **Configuration** | Preferred days + time ranges |
| **Agent Owner** | Agenda |

**Logical Flow:**
1. **Fetch** next week's calendar.
2. **Count** meetings per day.
3. **Identify** low-meeting days: <2 meetings.
4. **Find** 2-hour contiguous free slots on those days.
5. **Filter** by owner preferences if configured (e.g., prefer mornings, avoid Fridays).
6. **Assemble** focus block suggestion card: proposed slots with rationale ("Terça-feira tem apenas 1 reunião — bloco sugerido das 9h às 11h").
7. **Push** to Agenda → Desk Surface.
8. **Await** owner approval: accept, decline, or edit time.
9. **If** accepted, create calendar event titled "Foco — não aceitar reuniões."

---

## 8. Documentos Routines

### 8.1 Emissão de Notas Fiscais
| Field | Detail |
|-------|--------|
| **Name** | Emissão de Notas Fiscais |
| **Description** | Auto-drafts NFSe/NFe from approved sales/deliveries. Presents for 1-click owner approval before actual emission. |
| **Default Trigger** | Event — on sale approval OR Cron — Daily @ 14:00 (batch) |
| **Configuration** | Tax regime, default values, batch vs. real-time |
| **Agent Owner** | Documentos |

**Logical Flow:**
1. **Fetch** approved sales/deliveries without issued NF.
2. **Fetch** customer fiscal data: CNPJ/CPF, address, IE, tax regime.
3. **Classify** operation: service vs. goods, interstate vs. local, final consumer vs. business.
4. **Populate** NF fields deterministically:
   - Items, quantities, unit prices
   - Tax calculations: ISS (service), ICMS (goods), IPI, PIS, COFINS based on regime and NCM/CFOP tables
   - Totals, rounding, digitable line
5. **Validate** XML schema against SEFAZ technical specification (deterministic rules, not LLM).
6. **Assemble** NF draft card per document: full preview, tax breakdown, customer info, validation status.
7. **Push** to Documentos → Urgent.
8. **Await** owner approval:
   - **Emit:** submit to SEFAZ, record in ERP, notify customer via email.
   - **Edit:** allow field changes, re-validate, then emit.
   - **Reject:** log reason, return to pending queue for manual handling.

---

### 8.2 Validação de XML / Escrituração
| Field | Detail |
|-------|--------|
| **Name** | Validação de XML / Escrituração |
| **Description** | Checks if all NFs from the period are properly recorded in the ERP/accounting system. |
| **Default Trigger** | Cron — Mondays @ 10:00 |
| **Configuration** | Day of week |
| **Agent Owner** | Documentos |

**Logical Flow:**
1. **Fetch** NFs emitted via SEFAZ (last 7 days) by number and series.
2. **Fetch** NFs recorded in ERP/accounting system (same period).
3. **Cross-reference** both lists by access key (chave de acesso).
4. **Identify** SEFAZ-issued but ERP-missing.
5. **Identify** ERP-recorded but SEFAZ-cancelled or rejected.
6. **Assemble** reconciliation card: missing items list, suggested correction actions (re-import XML, check rejection reason).
7. **If** gaps found, push to Documentos → Urgent.
8. **If** clean, log silently.

---

### 8.3 Revisão de Contratos a Vencer
| Field | Detail |
|-------|--------|
| **Name** | Revisão de Contratos a Vencer |
| **Description** | Flags contract renewals or cancellations coming in 30/60 days. Prevents unintended auto-renewals. |
| **Default Trigger** | Cron — 1st of month @ 09:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Documentos |

**Logical Flow:**
1. **Fetch** active contracts with end dates.
2. **Fetch** auto-renewal clause flags.
3. **Filter** contracts ending within 30 or 60 days.
4. **Flag** auto-renewal contracts as high-risk (unintended renewal possible).
5. **Calculate** financial impact: monthly value × 12 if renewed vs. $0 if terminated.
6. **Assemble** contract review card per contract:
   - Contract name, counterparty, end date
   - Auto-renewal: yes/no
   - Monthly value, annual impact
   - Recommended action: renew, renegotiate, terminate, review terms
7. **Push** to Documentos → Urgent.
8. **Await** owner decision per contract.

---

### 8.4 LGPD — Revisão de Dados Obsoletos
| Field | Detail |
|-------|--------|
| **Name** | LGPD — Revisão de Dados Obsoletos |
| **Description** | Identifies customer records inactive >3 years. Suggests anonymization or deletion. Waits for explicit owner approval. No automated deletion. |
| **Default Trigger** | Cron — Quarterly (1st of Jan/Apr/Jul/Oct) @ 09:00 |
| **Configuration** | None |
| **Agent Owner** | Documentos |

**Logical Flow:**
1. **Fetch** all customer records with last_activity_date >3 years.
2. **Fetch** legal hold flags (active litigation involving record).
3. **Fetch** regulatory retention requirements (e.g., fiscal records must keep for 5 years).
4. **Filter** out records under legal hold or retention period.
5. **Count** eligible records and estimate data volume (rows, storage).
6. **Assess** risk level: high if >100 records, medium if 10-100, low if <10.
7. **Assemble** compliance review card:
   - Count of obsolete records
   - Data volume
   - Risk assessment
   - Suggested batch action: anonymize, delete, or review individually
8. **Push** to Documentos → Desk Surface.
9. **Await** owner approval. No automated deletion under any circumstance.

---

## 9. Estratégia Routines

### 9.1 Padrões Escondidos
| Field | Detail |
|-------|--------|
| **Name** | Padrões Escondidos |
| **Description** | Runs correlation analysis across business data to surface non-obvious causal patterns. |
| **Default Trigger** | Cron — 5th of month @ 09:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Estratégia |

**Logical Flow:**
1. **Fetch** 12-month sales timeseries (daily or weekly).
2. **Fetch** marketing spend timeseries.
3. **Fetch** inventory event log (stockouts, overstock).
4. **Fetch** customer acquisition timeseries.
5. **Run** lagged correlation analysis (Pearson/Spearman) with lags of 1-30 days between variables.
6. **Filter** for correlations with p-value <0.2 (80% confidence) and business relevance.
7. **Exclude** trivial correlations (same-day inventory-sales is expected, not insightful).
8. **Assemble** insight card for each significant pattern:
   - Pattern in plain language (e.g., "Quando estoque de X cai abaixo de 10 unidades, vendas de Y caem 15% com 3 dias de defasagem")
   - Evidence strength (correlation coefficient, sample size)
   - Business implication
   - Suggested experiment to validate
9. **Push** to Estratégia → Desk Surface + Home → Insights.

---

### 9.2 Revisão de Metas vs. Realidade
| Field | Detail |
|-------|--------|
| **Name** | Revisão de Metas vs. Realidade |
| **Description** | Compares trajectory against stated goals. If no goals exist, suggests realistic ones based on history and seasonality. |
| **Default Trigger** | Cron — 1st of month @ 09:00 |
| **Configuration** | Day of month |
| **Agent Owner** | Estratégia |

**Logical Flow:**
1. **Fetch** stated goals (revenue, margin, customer count, etc.) if configured.
2. **Fetch** actuals for the just-closed month.
3. **Fetch** 12-month historical performance.
4. **If** goals exist:
   - Calculate gap: (actual - goal) / goal × 100.
   - Calculate month-to-date run rate and project month-end.
   - Determine status: ahead / on track / behind.
5. **If** no goals exist:
   - Calculate historical average per month.
   - Apply seasonality index (same month last 3 years vs. annual average).
   - Suggest conservative and stretch goals.
6. **Assemble** goals report card: status table, gap analysis, or suggested goals with rationale.
7. **Push** to Estratégia → Desk Surface.

---

### 9.3 Análise de Concorrência / Mercado
| Field | Detail |
|-------|--------|
| **Name** | Análise de Concorrência / Mercado |
| **Description** | If competitor monitoring is configured, summarizes price moves, new entrants, or industry news. |
| **Default Trigger** | Cron — 10th of month @ 09:00 |
| **Configuration** | Sector keywords / competitor list |
| **Agent Owner** | Estratégia |

**Logical Flow:**
1. **Fetch** competitor price data from configured web sources (if any).
2. **Fetch** industry news from configured RSS/feed sources (if any).
3. **Fetch** own current prices for comparable SKUs.
4. **If** no monitoring configured:
   - Assemble "configure monitoring" prompt card.
   - Push to Estratégia → Desk Surface.
   - End routine.
5. **If** data exists:
   - Compare competitor prices to own prices where SKU overlap exists. Flag if competitor < own by >5%.
   - Filter news by relevance to pricing, positioning, or operations.
   - Summarize news by impact level (high/medium/low).
6. **Assemble** market intel card: what changed, why it matters, price comparison table, suggested response.
7. **Push** to Estratégia → Desk Surface.

---

## 10. Zero-Config Starter Pack

The following routines are **enabled by default** for new users with smart presets. The owner can pause, edit cadence, or change thresholds in Config (Under Desk).

| # | Routine | Room | Default Trigger | Config Required |
|---|---------|------|-----------------|-----------------|
| 1 | Sincronização da Manhã | Home | Daily @ 07:00 | None |
| 2 | Plano do Dia | Home | Triggered by Sincronização | Time only (for chain start) |
| 3 | Radar de Prazos | Home | Triggered by Sincronização | None |
| 4 | Digest do Fim de Dia | Home | Daily @ 18:00 | Time only |
| 5 | Resumo Semanal | Home | Fridays @ 17:00 | Day + time |
| 6 | Alerta de Fluxo de Caixa | Financeiro | Daily @ 07:00 | Safety balance (R$) |
| 7 | Conciliação Bancária Sugerida | Financeiro | Mondays @ 09:00 | Day |
| 8 | Relatório Mensal de Performance | Financeiro | 1st @ 08:00 | Day of month |
| 9 | Cobrança de Inadimplentes | Financeiro | Wednesdays @ 10:00 | Days overdue |
| 10 | Alerta de Estoque Mínimo | Compras | Daily @ 08:00 | Reorder points (auto-learn) |
| 11 | Sugestão de Compra | Compras | Tuesdays @ 09:00 | Day |
| 12 | Follow-up Pós-Venda | Clientes | Daily @ 10:00 | Days after purchase |
| 13 | Pipeline de Vendas Review | Clientes | Mondays @ 09:00 | Stalled threshold |
| 14 | Preparação de Reunião | Agenda | 15 min before event | None |
| 15 | Emissão de Notas Fiscais | Documentos | Real-time / Daily @ 14:00 | Regime + mode |

---

## 11. Change Log: v1.0 → v2.0 → v2.1

| Change | Reason |
|--------|--------|
| **Merged** Revisão de Decisões Pendentes into Plano do Dia | Dependency: Plano do Dia should include pending decisions as its primary input. |
| **Eliminated** Revisão de Compromissos da Semana | Duplicate: Plano do Dia on Monday already covers week-ahead calendar. |
| **Eliminated** Revisão de Integrações as standalone | Duplicate: Sincronização da Manhã already covers daily integration health. Deep diagnostic remains an **Action** in Admin. |
| **Reclassified** Auditoria de Aprovações as Action | Not recurring — owner queries searchable log on demand. |
| **Reclassified** Export de Dados Críticos as Action | LGPD requirement — user triggers export from Admin → LGPD. |
| **Reclassified** CAC as Action | DB calculation rendered on Estratégia dashboard, no schedule needed. |
| **Renamed** LGPD routine to "Revisão de Dados Obsoletos" | Clarified it suggests review, never auto-deletes. |
| **Simplified flows** to logical steps | Removed function/skill syntax. Emphasized deterministic data transformations. |
| **Added** event-triggered morning chain v2.1 | Sincronização da Manhã triggers Radar de Prazos, which triggers Plano do Dia. Prevents race conditions and passes context. |
| **Updated** Zero-Config Starter Pack triggers v2.1 | Plano do Dia and Radar de Prazos now show as triggered, not cron-scheduled. |

---

*End of Document*
