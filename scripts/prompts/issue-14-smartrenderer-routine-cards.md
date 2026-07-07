# Fix: Use SmartRenderer in all routine cards for formatted JSON output

## Goal
Replace raw `{renderBody(approval.body)}` and raw JSON text rendering with `<SmartRenderer>` in DecisionCard, RoutineResultModal, and RoutinePreviewCard. This ensures all routine outputs with JSON insights appear as formatted cards, KPI cells, and tables.

## What to fix

### 1. DecisionCard.tsx — Replace renderBody with SmartRenderer
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/DecisionCard.tsx`

**Add import:**
```typescript
import SmartRenderer from '../chat/SmartRenderer'
```

**Line 188**, replace:
```tsx
{approval.body && <div className="db">{renderBody(approval.body)}</div>}
```
With:
```tsx
{approval.body && (
  <div className="db">
    <SmartRenderer content={approval.body} />
  </div>
)}
```

### 2. RoutineResultModal.tsx — Replace raw text with SmartRenderer
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutineResultModal.tsx`

**Add import:**
```typescript
import SmartRenderer from '../chat/SmartRenderer'
```

Find where `result_text` is rendered (likely `{line}` inside a map). Replace with `<SmartRenderer>`:
```tsx
<SmartRenderer content={execution.result_text ?? ''} />
```

Remove the `lines.map` approach — let SmartRenderer handle the split/format.

### 3. RoutineActivationCard in DecisionCard.tsx — Already has Checkbox, ensure body is formatted
The RoutineActivationCard already uses Checkbox for steps. If there's a body/description field being rendered as raw text, wrap it in `<SmartRenderer>`.

### 4. RoutinePreviewCard.tsx — Add SmartRenderer for description
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutinePreviewCard.tsx`

**Add import:**
```typescript
import SmartRenderer from '../chat/SmartRenderer'
```

If there's a description rendered as raw text, wrap it:
```tsx
<SmartRenderer content={description ?? ''} />
```

## Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
