# Issue 9: Integrate Toggle/Checkbox/Radio/Pagination + use in Routine Cards & Agent Messages

## Goal
Use new components in routine/cards panels and chat messages. Replace native form elements with custom components.

## Files to modify

### 1. RoutineConfigSection.tsx — Use Toggle for routine toggles
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutineConfigSection.tsx`

Add import:
```typescript
import Toggle from './Toggle'
```

Find where routines have on/off toggles (likely `<input type="checkbox">` or similar). Replace with:
```tsx
<Toggle checked={enabled} onChange={(v) => setEnabled(v)} label={routine.name} />
```

### 2. RoutinesPanel.tsx — Use Checkbox for task completion
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutinesPanel.tsx`

Add import:
```typescript
import Checkbox from './Checkbox'
```

Replace native checkboxes with `<Checkbox checked={...} onChange={...} />`.

### 3. AdminScreen.tsx — Use Toggle for config switches
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/AdminScreen.tsx`

Find toggle-like switches in admin settings. Replace with `<Toggle>` component.

### 4. DecisionCard.tsx — Use new components in routine activation cards
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/DecisionCard.tsx`

The RoutineActivationCard already shows steps with status dots. Enhance with:
```tsx
<Checkbox checked={step.done} label={step.label} disabled />
```
for completed steps.

### 5. ChatPanel.tsx — Enhance agent responses with structured components
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/chat/ChatPanel.tsx`

Look for places where the agent returns structured data (approvals, documents, tables). Add inline support:
- Use `<Pagination>` if chat history exceeds a page
- Use `LoadingState variant='row'` for chat loading

### 6. Pagination in existing lists
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/ClientesRoom.tsx`
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/ComprasRoom.tsx`

Add `<Pagination>` at the bottom of client lists and purchase lists.

### 7. BibliotecaRoom.tsx — Use LoadingState variants + Pagination
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`

Replace current LoadingState calls with variants. Add Pagination to document grid.

## Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
