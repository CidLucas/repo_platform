# Issue 4: CSS Tokens Faltantes — Shadows & Radius

## Goal
Add missing CSS design tokens (`--shadow-1`, `--shadow-2`, `--shadow-3`, `--rxl`) to global.css and create a reusable `.shadow-*` utility system. These tokens are referenced by the design system but don't exist in the app.

## What to build

### Add to `:root` in global.css

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/styles/global.css`

Add after existing tokens (around line 36):
```css
  /* resizable right column width */
  --rcol-w: 420px;
  
  /* shadows */
  --shadow-1: 0 2px 14px rgba(0,0,0,.28);
  --shadow-2: 0 4px 22px rgba(0,0,0,.36);
  --shadow-3: 0 12px 40px rgba(0,0,0,.6);
  
  /* extra radius */
  --rxl: 20px;
}
```

### Add panel shadow classes after the existing `.panel` styles

After the `.panel:hover` block (around line 127), add:
```css
/* ── SHADOW UTILITIES ── */
.shadow-1 { box-shadow: var(--shadow-1); }
.shadow-2 { box-shadow: var(--shadow-2); }
.shadow-3 { box-shadow: var(--shadow-3); }
```

### Audit existing inline box-shadow usage
Find files that use inline `boxShadow` or `box-shadow` with hardcoded values and replace them with the CSS variable:

```bash
grep -rn "boxShadow\|box-shadow" apps/blu_v3/src/pages/ apps/blu_v3/src/components/ --include="*.tsx" | grep -v node_modules | grep -v "var(--"
```

Replace any hardcoded shadow that matches `--shadow-1` or `--shadow-2` patterns with `var(--shadow-1)` or `var(--shadow-2)`.

## Files
- `/home/ec2-user/repo_platform/apps/blu_v3/src/styles/global.css` (main change)
- Various `.tsx` files (audit + replace hardcoded shadows)

## Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
