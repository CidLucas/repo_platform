# Issue 12: LoadingState variants + Toggle/Checkbox in routine cards + Pagination

## Goal
Replace all raw `<LoadingState message="...">` calls with appropriate variants, use Toggle in routine config, Checkbox in decision cards, and Pagination in lists.

## What to build

### 1. LoadingState variants across pages

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/AgendaRoom.tsx`
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/AgentOpsRoom.tsx`
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`

Replace:
```tsx
<LoadingState message="Carregando agenda…" />
```
With appropriate variant:
```tsx
<LoadingState variant="card" />
```
or for lists/tables:
```tsx
<LoadingState variant="row" rows={5} />
```

### 2. Toggle in RoutineConfigSection

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutineConfigSection.tsx`

Look for the repeating routine items that show a name + time. Add a `<Toggle>` next to each routine:
```tsx
import Toggle from './Toggle'
```
Replace the existing checkbox/toggle with the custom Toggle component.

### 3. Checkbox in RoutineActivationCard (DecisionCard.tsx)

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/DecisionCard.tsx`

In the `RoutineActivationCard` function, replace the step list dots with `<Checkbox>`:
```tsx
import Checkbox from './Checkbox'
```
Replace:
```tsx
<li className={stepCls}>{step.label}</li>
```
With:
```tsx
<li style={{listStyle: 'none', marginBottom: 4}}>
  <Checkbox checked={step.done} label={step.label} disabled />
</li>
```

### 4. Pagination in lists

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/ClientesRoom.tsx`
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/ComprasRoom.tsx`

Add `<Pagination>` component at the bottom of client/supplier lists:
```tsx
import Pagination from '../../components/shared/Pagination'
```
Add state:
```typescript
const [page, setPage] = useState(1)
const pageSize = 20
```
Render at bottom of list:
```tsx
<Pagination
  currentPage={page}
  totalPages={Math.ceil(totalItems / pageSize)}
  totalItems={totalItems}
  pageSize={pageSize}
  onPageChange={setPage}
/>
```

### 5. Charts in FinanceiroRoom

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/FinanceiroRoom.tsx`

Add import:
```typescript
import { LineChart, BarChart } from '../../components/shared/Charts'
```

Find the KPIs section (around "KPIs do mês"). After or within that section, add a small `<LineChart>` showing revenue trend. Place it in a `.panel` div with glass styling.

```tsx
<div className="panel" style={{padding: 16, marginTop: 10}}>
  <div className="ph-ttl" style={{marginBottom: 10}}>Receita - Últimos 12 meses</div>
  <LineChart
    data={[
      {label: 'Jul', value: 32000},
      {label: 'Ago', value: 35000},
      {label: 'Set', value: 38000},
      {label: 'Out', value: 42000},
      {label: 'Nov', value: 45000},
      {label: 'Dez', value: 51000},
      {label: 'Jan', value: 48000},
      {label: 'Fev', value: 52000},
      {label: 'Mar', value: 49000},
      {label: 'Abr', value: 56000},
      {label: 'Mai', value: 61000},
      {label: 'Jun', value: 68000},
    ]}
    width={400}
    height={160}
    color="var(--ac)"
    gradient
    showDots
    showGrid
    formatValue={(v) => `R$ ${(v/1000).toFixed(0)}k`}
  />
</div>
```

### Files to modify
- `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/AgendaRoom.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/AgentOpsRoom.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutineConfigSection.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/DecisionCard.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/ClientesRoom.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/ComprasRoom.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/FinanceiroRoom.tsx`

### Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
