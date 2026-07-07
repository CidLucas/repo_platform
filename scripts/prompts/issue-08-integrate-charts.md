# Issue 8: Integrate Charts + LoadingState variants into existing pages

## Goal
Replace static text KPIs with SVG charts and use LoadingState variants across existing pages.

## Files to modify

### 1. EstrategiaRoom.tsx — Add Sparkline to KPI cells
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`

Add import:
```typescript
import { Sparkline } from '../../components/shared/Charts'
```

Find the `estrategiaMetrics.map((m) => {` block (around line 1095). Replace the current KPI rendering inside the `.kpi-cell` div with:

```tsx
<div key={m.kpi} className="kpi-cell">
  <div className="kpi-lbl">{m.label}</div>
  <div className="kpi-val" style={{ fontSize: 15 }}>{val}</div>
  {delta != null && (
    <div className="kpi-d" style={{ color: deltaColor }}>{delta} mês</div>
  )}
  <Sparkline data={[30, 45, 38, 52, 48, 61, 55, 68, 72, 65, 78, 84]} width={100} height={24} color={deltaColor} />
</div>
```

### 2. FinanceiroRoom.tsx — Add LineChart for MRR
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/FinanceiroRoom.tsx`

Add import:
```typescript
import { LineChart, BarChart } from '../../components/shared/Charts'
```

Find where KPIs are displayed (search for "KPIs do mês" or "nums-head"). After the KPI row, add a `<LineChart>` showing MRR over 12 months with mock or real data.

### 3. LoadingState variants across pages
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/AgendaRoom.tsx`
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/AgentOpsRoom.tsx`
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`

Replace `<LoadingState message="Carregando…" />` with appropriate variants:
- Sidebar panels → `variant='card'`
- Table/list areas → `variant='row' rows={5}`
- Full page blocks → `variant='card'`

Example: `<LoadingState variant="card" />` or `<LoadingState variant="row" rows={5} />`

## Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
