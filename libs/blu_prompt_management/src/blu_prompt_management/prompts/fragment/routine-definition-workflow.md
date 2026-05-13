## Routine Creation

When the user describes a business process to automate:

### Step 1 — Orient
Call `listar_rotinas_personalizadas` to check for existing routines. If a similar one already exists, tell the user and ask if they want to update or create a new one.

### Step 2 — Extract Trigger and Goal
Identify:
- **Trigger**: When should this run? (`trigger_type`: "schedule" for recurring, "event" for condition-based, "document" for upload-triggered, "manual" for on-demand)
- **Goal**: What outcome does the user want?
- **Audience**: Who receives the output?

### Step 3 — Decompose into Steps
Translate into atomic steps using available Layer-3 skills. Each step maps to one skill and one action.

Describe the steps in plain language **before** structuring them: "Vou configurar: (1) Toda segunda às 9h, o Data Analyst consulta clientes com churn > 0.7. (2) O Customer Communication envia WhatsApp para cada um. Faz sentido?"

### Step 4 — Confirm and Create
Only after the user confirms:
1. Call `criar_rotina_personalizada` with the structured routine:
   - `name`: human-readable label
   - `trigger_type`: "schedule" | "event" | "document" | "manual"
   - `description`: plain-language summary of what the routine does
   - `steps`: ordered array — **each step must follow this exact format:**
     ```json
     {"step": 1, "agent": "<Layer-3 skill slug>", "action": "<action_id>", "input": {}}
     ```
     Valid skill slugs: `data-analyst`, `knowledge-assistant`, `report-generator`, `context-gatherer`, `customer-support`, `rfq-agent`
2. After creation, call `enviar_rotina_para_aprovacao` to submit the draft for activation.
3. Confirm to the user: "Rotina criada em rascunho e enviada para aprovação. Você será notificado quando estiver ativa."
