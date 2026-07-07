# Issue 10: SmartRenderer — Parse agent responses into formatted components

## Goal
Create a component that detects structured data/JSON in agent chat messages and renders them as formatted cards, KPI cells, charts, and tables instead of raw text.

## What to build

Create `apps/blu_v3/src/components/chat/SmartRenderer.tsx`:

```typescript
interface SmartRendererProps {
  content: string
}
```

### Detection logic
The component receives raw text from the agent. It should:
1. Try to parse `{...}` or `[...]` blocks as JSON
2. If valid JSON with known structures, render as formatted components
3. Otherwise, render as plain text (with basic markdown-like formatting)

### JSON structures to handle

#### a) Performance insights (the raw JSON the user showed)
```json
{"performance": {"financeiro": {"receita": "...", "ticket_medio": "...", "status": "normal"}, "comercial": {"pedidos": "...", "clientes": "...", "recorrencia": "..."}}}
```
Render as: grid of KPI cards using `KpiMetricsPanel` or inline styled divs
- Each key (financeiro, comercial) becomes a section
- Each sub-key (receita, ticket_medio) becomes a KPI cell with label + value + status color

#### b) Arrays of objects (tabular data)
```json
[{"nome": "Cliente A", "receita": 12500, "status": "ativo"}, {"nome": "Cliente B", "receita": 8700, "status": "inativo"}]
```
Render as: compact table with styled badges for status

#### c) Objects with numeric values (chart data)
```json
{"mrr": [32000, 35000, 38000, 42000, 45000, 48000], "labels": ["Jan","Fev","Mar","Abr","Mai","Jun"]}
```
Render as: inline `<Sparkline>` or `<LineChart>` (from Charts.tsx)

#### d) Simple key-value objects
```json
{"nome": "João", "cargo": "Analista", "departamento": "Financeiro", "tempo_casa": "3 anos"}
```
Render as: structured card with label:value rows

### Usage
Import and use in `ChatPanel.tsx`:
```tsx
// In MessageBubble component, replace {content} with:
<SmartRenderer content={content} />
```

Also use in the streamBuffer rendering (line ~272):
```tsx
<SmartRenderer content={streamBuffer} />
```

### Styling
- Use the existing Blu design tokens
- Cards inside chat: `background: rgba(255,255,255,0.055)`, `border-radius: 8px`, `padding: 10px`
- KPI cells in chat: compact, smaller font (10px labels, 14px values)
- Tables in chat: compact, `font-size: 11px`, same glass styling
- Charts in chat: max-width 280px

### File
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/chat/SmartRenderer.tsx`
- Modified: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/chat/ChatPanel.tsx`

### Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
