# Issue 5: Pagination Component

## Goal
Create a reusable Pagination component for the Blu app. Used at the bottom of tables, search results, and lists that span multiple pages.

## What to build

Create `apps/blu_v3/src/components/shared/Pagination.tsx`:

```typescript
interface PaginationProps {
  currentPage: number
  totalPages: number
  totalItems: number
  pageSize: number
  onPageChange: (page: number) => void
  label?: string  // e.g. "Exibindo 1–20 de 97 itens"
}
```

### Visual design
Use the existing Blu design tokens (glassmorphism, dark theme):

```
┌──────────────────────────────────────────────────┐
│  Exibindo 1–20 de 97 itens       ‹ 1 2 3 … 8 ›  │
└──────────────────────────────────────────────────┘
```

- Left side: info text ("Exibindo 1–20 de 97 itens") — `font-size: 11px`, `color: var(--mu)`, `font-family: var(--body)`
- Right side: page buttons
  - Active page: `background: var(--ac)`, `color: #fff`
  - Inactive pages: `background: transparent`, `border: 1px solid var(--gb)`, `color: var(--mu2)`
  - Hover on inactive: `background: var(--glass)`, `border-color: var(--gb2)`
  - Ellipsis when there are too many pages: `...` text, `color: var(--mu)`
  - Prev/Next chevrons: `‹` and `›` buttons (disabled on first/last page)
- Button size: `32x32px`, `border-radius: var(--r)`
- Container: `display: flex`, `justify-content: space-between`, `align-items: center`, `padding: 8px 12px`, `border-top: 1px solid var(--gb)`

### Behavior
- Show at most 5 page buttons at a time: first page, last page, and 3 around current
- Always show first and last page
- Use `...` when there's a gap of 2+ pages
- Prev button (`‹`) disabled when `currentPage === 1`
- Next button (`›`) disabled when `currentPage === totalPages`
- Clicking a page button calls `onPageChange(page)`

## Files
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/Pagination.tsx`

## Verification
1. `cd apps/blu_v3 && npx tsc --noEmit` — zero errors
2. Component renders all states correctly (1 page, many pages, first/last/middle active)
