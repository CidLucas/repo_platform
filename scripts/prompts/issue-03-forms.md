# Issue 3: Form Inputs com Validação

## Goal
Add CSS classes for form validation states (success/error/warning) to inputs, and create reusable form field components.

## What to build

### 1. CSS (add to global.css)

```css
/* ── INPUT STATES ── */
.input { width: 100%; background: rgba(255,255,255,.055); border: 1px solid var(--gb2); border-radius: var(--r); padding: 10px 13px; font-size: 13px; color: var(--fg); outline: none; transition: border-color .12s, box-shadow .12s; font-family: var(--body); }
.input:hover { border-color: var(--gb); }
.input:focus, .input:focus-within { border-color: var(--ac); box-shadow: 0 0 0 3px var(--adim); }
.input::placeholder { color: var(--mu); }
.input:disabled { opacity: .4; cursor: not-allowed; }

/* Validation states */
.input.success { border-color: var(--ok); }
.input.success:focus { box-shadow: 0 0 0 3px var(--odim); }
.input.error { border-color: var(--urg); }
.input.error:focus { box-shadow: 0 0 0 3px var(--udim); }
.input.warning { border-color: var(--att); }
.input.warning:focus { box-shadow: 0 0 0 3px var(--adm2); }

/* Validation message */
.val-msg { font-size: 10.5px; display: flex; align-items: center; gap: 4px; margin-top: 3px; font-weight: 500; }
.val-msg.success { color: var(--ok); }
.val-msg.error { color: var(--urg); }
.val-msg.warning { color: var(--att); }

/* ── BUTTON SIZES ── */
.btn-sm { padding: 4px 8px; font-size: 10px; border-radius: 4px; }
.btn-lg { padding: 8px 16px; font-size: 14px; border-radius: var(--r); }
```

### 2. Create Field component

Create `apps/blu_v3/src/components/shared/Field.tsx`:

```typescript
interface FieldProps {
  label: string
  error?: string
  warning?: string
  success?: string
  hint?: string
  children: React.ReactNode
  required?: boolean
}
```

Renders: label (uppercase, 9px, muted) + children + validation message + hint.
The children (input/select/textarea) get the `.input` class plus `.success/.error/.warning` based on which prop is set.

### 3. Fix EmptyState.tsx

The current EmptyState.tsx has a type error:
```
Type 'ReactElement<any, any>' is missing the following properties from type 'EmptyStateProps': icon, title, description
```
Fix it so it properly returns JSX with the correct props interface.

## Files
- `/home/ec2-user/repo_platform/apps/blu_v3/src/styles/global.css`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/Field.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/EmptyState.tsx`

## Verification
1. `cd apps/blu_v3 && npx tsc --noEmit` — zero errors in Field.tsx and EmptyState.tsx
2. The EmptyState TS error in AgendaRoom/AgentOpsRoom should be resolved
