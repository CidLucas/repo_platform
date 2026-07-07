# Fix: DecisionCard duplication + Integrate remaining routine components

## Goal
Fix the numbered circle duplication in DecisionCard and integrate Toggle/Checkbox into 4 routine components that were missed.

## What to fix

### 1. DecisionCard.tsx — Remove duplicated numbered circle
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/DecisionCard.tsx`

Lines 96-100 currently render BOTH a numbered circle AND a Checkbox. Remove the numbered circle div:

**Before (lines 96-100):**
```tsx
{steps.map((step, i) => {
  const stepDone = Boolean((step as { done?: boolean }).done)
  const stepLabel = step.label ?? step.skill_slug ?? step.function ?? step.action ?? 'Passo'
  return (
    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 6 }}>
      <div style={{ width: 18, height: 18, borderRadius: 9, background: '#6366f1', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, fontWeight: 700, flexShrink: 0, marginTop: 1 }}>
        {i + 1}
      </div>
      <div style={{ flex: 1 }}>
        <Checkbox
          checked={stepDone}
          disabled
          onChange={() => {}}
          label={stepLabel}
        />
        {step.type && <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 1, marginLeft: 28 }}>{step.type}</div>}
      </div>
    </div>
  )
})}
```

**After:**
```tsx
{steps.map((step, i) => {
  const stepDone = Boolean((step as { done?: boolean }).done)
  const stepLabel = step.label ?? step.skill_slug ?? step.function ?? step.action ?? 'Passo'
  return (
    <div key={i} style={{ marginBottom: 6 }}>
      <Checkbox
        checked={stepDone}
        disabled
        onChange={() => {}}
        label={stepLabel}
      />
      {step.type && <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 1, marginLeft: 28 }}>{step.type}</div>}
    </div>
  )
})}
```

### 2. RoutineExecutionFeed.tsx — Use Checkbox for step status
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutineExecutionFeed.tsx`

Add import: `import Checkbox from './Checkbox'`

Find where execution steps are rendered (likely mapping over steps with text). Replace with Checkbox showing completed/pending state.

### 3. RoutinePreviewCard.tsx — Use Checkbox for steps
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutinePreviewCard.tsx`

Add import: `import Checkbox from './Checkbox'`

Find step rendering and replace with `<Checkbox checked={step.done} disabled label={step.label} />`.

### 4. RoutineStatusWidget.tsx — Use Toggle for active/inactive
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutineStatusWidget.tsx`

Add import: `import Toggle from './Toggle'`

If there's an active/inactive toggle or status display, enhance it with the Toggle component.

### 5. RoutineResultModal.tsx — Use Checkbox for completion
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/RoutineResultModal.tsx`

Add import: `import Checkbox from './Checkbox'`

If there's step completion display, use Checkbox checked={true} disabled for completed steps.

## Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
