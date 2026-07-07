# Issue 6: Toggle Switch + Custom Checkbox/Radio

## Goal
Create reusable Toggle, Checkbox, and Radio components styled for the Blu dark theme. Currently the app uses native `<input type="checkbox">` without custom styling.

## What to build

Create `apps/blu_v3/src/components/shared/Toggle.tsx` and `apps/blu_v3/src/components/shared/Checkbox.tsx`

### 1. Toggle switch (`Toggle.tsx`)

```typescript
interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  id?: string
}
```

Visual:
```
○──────  Off          ●──────  On
```
- Track: `40px x 22px`, `border-radius: 11px`, `background: var(--gb)` when off, `background: var(--ac)` when on
- Knob: `18px x 18px` circle, `background: var(--mu2)` when off, `background: #fff` when on
- Animation: `transition: transform 0.2s, background 0.2s` on knob
- Label text: `font-size: 12px`, `color: var(--mu2)`, gap of `8px` from the toggle
- Disabled state: `opacity: 0.4`, `cursor: not-allowed`
- Focus: `box-shadow: 0 0 0 3px var(--adim)` on the track
- Hover on enabled: subtle brightening of track background

### 2. Custom Checkbox (`Checkbox.tsx`)

```typescript
interface CheckboxProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  indeterminate?: boolean
  id?: string
}
```

Visual:
```
[ ]  Unchecked    [✓]  Checked    [-]  Indeterminate
```
- Box: `20px x 20px`, `border-radius: 4px`, `border: 1.5px solid var(--gb2)`, `background: transparent`
- Checked: `background: var(--ac)`, `border-color: var(--ac)`, white checkmark via CSS `::after` (rotated square, like before)
- Indeterminate: `background: var(--ac)`, short horizontal line instead of check
- Hover: border brightens to `var(--gb)`
- Focus: `box-shadow: 0 0 0 3px var(--adim)`
- Disabled: `opacity: 0.35`
- Label: same as toggle, `font-size: 12px`, `color: var(--mu2)`

### 3. Custom Radio (`Radio.tsx`)

Same pattern but circle (`border-radius: 50%`).
- Selected: inner filled circle `8px` diameter, `background: var(--ac)`
- Group support via `name` prop

### 4. CSS classes (add to global.css)

```css
/* ── TOGGLE ── */
.toggle { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; font-size: 12px; color: var(--mu2); user-select: none; }
.toggle input { position: absolute; opacity: 0; width: 0; height: 0; }
.toggle-track { width: 40px; height: 22px; border-radius: 11px; background: var(--gb); transition: background .2s; position: relative; flex-shrink: 0; }
.toggle-track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: var(--mu2); transition: transform .2s, background .2s; }
.toggle input:checked + .toggle-track { background: var(--ac); }
.toggle input:checked + .toggle-track::after { transform: translateX(18px); background: #fff; }
.toggle input:focus-visible + .toggle-track { box-shadow: 0 0 0 3px var(--adim); }
.toggle.disabled { opacity: .35; cursor: not-allowed; }

/* ── CHECKBOX ── */
.checkbox { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; font-size: 12px; color: var(--mu2); user-select: none; }
.checkbox input { position: absolute; opacity: 0; width: 0; height: 0; }
.checkbox-box { width: 20px; height: 20px; border-radius: 4px; border: 1.5px solid var(--gb2); background: transparent; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: border-color .15s, background .15s; }
.checkbox:hover .checkbox-box { border-color: var(--gb); }
.checkbox input:checked + .checkbox-box { background: var(--ac); border-color: var(--ac); }
.checkbox input:checked + .checkbox-box::after { content: ''; width: 5px; height: 9px; border: solid #fff; border-width: 0 2px 2px 0; transform: rotate(45deg); margin-top: -1px; }
.checkbox input:indeterminate + .checkbox-box { background: var(--ac); border-color: var(--ac); }
.checkbox input:indeterminate + .checkbox-box::after { content: ''; width: 10px; height: 2px; background: #fff; }
.checkbox input:focus-visible + .checkbox-box { box-shadow: 0 0 0 3px var(--adim); }
.checkbox.disabled { opacity: .35; cursor: not-allowed; }

/* ── RADIO ── */
.radio { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; font-size: 12px; color: var(--mu2); user-select: none; }
.radio input { position: absolute; opacity: 0; width: 0; height: 0; }
.radio-circle { width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid var(--gb2); background: transparent; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: border-color .15s; }
.radio:hover .radio-circle { border-color: var(--gb); }
.radio input:checked + .radio-circle { border-color: var(--ac); }
.radio input:checked + .radio-circle::after { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--ac); }
.radio input:focus-visible + .radio-circle { box-shadow: 0 0 0 3px var(--adim); }
.radio.disabled { opacity: .35; cursor: not-allowed; }
```

## Files
- `/home/ec2-user/repo_platform/apps/blu_v3/src/styles/global.css`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/Toggle.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/Checkbox.tsx`
- `/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/Radio.tsx`

## Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
