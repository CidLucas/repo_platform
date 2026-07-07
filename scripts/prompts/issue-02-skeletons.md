# Issue 2: Loading Skeletons — Shimmer Animation

## Goal
Add shimmer loading skeleton components and CSS animations to the Blu app. Skeletons replace content placeholders while data loads, improving perceived performance.

## What to build

### 1. CSS (add to global.css)

Add after the existing animation keyframes:
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.skeleton {
  background: linear-gradient(90deg, var(--gb) 25%, var(--gl2) 50%, var(--gb) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--r);
}

.skeleton-text {
  height: 12px;
  margin-bottom: 6px;
  width: 100%;
}

.skeleton-title {
  height: 18px;
  margin-bottom: 10px;
  width: 60%;
}

.skeleton-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
}

.skeleton-card {
  height: 120px;
  border-radius: var(--rl);
}

.skeleton-row {
  height: 40px;
  margin-bottom: 4px;
}
```

### 2. Update LoadingState.tsx

Path: `apps/blu_v3/src/components/shared/LoadingState.tsx`

Update to support multiple skeleton modes:
```typescript
interface LoadingStateProps {
  message?: string
  variant?: 'spinner' | 'card' | 'text' | 'row' | 'table' | 'chart'
  rows?: number      // number of skeleton rows (for variant='row' or 'table')
}
```

Each variant renders the appropriate skeleton:
- `'spinner'` — existing spinner + message (current behavior)
- `'card'` — single `.skeleton-card` shimmer
- `'text'` — 3 `.skeleton-text` lines + `.skeleton-title`
- `'row'` — N `.skeleton-row` shimmers
- `'table'` — header skeleton + N row skeletons
- `'chart'` — rectangular skeleton with aspect ratio suitable for a chart

### 3. Fix existing component
The current LoadingState.tsx has a type error:
```
Type '({ message }: LoadingStateProps) => LoadingStateProps' is not a valid JSX element type.
```
Fix it so it returns proper JSX (ReactNode), not LoadingStateProps.

## Files to modify
- `/home/ec2-user/repo_platform/apps/blu_v3/src/styles/global.css`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/LoadingState.tsx`

## Verification
1. `cd apps/blu_v3 && npx tsc --noEmit` — zero errors in LoadingState.tsx
2. The LoadingState type error in AgendaRoom and AgentOpsRoom (TS2786) should be resolved
