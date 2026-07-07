# Issue 1: SVG Charts Component — Line, Bar, Donut, Sparkline

## Goal
Create reusable SVG chart components for the Blu app at `apps/blu_v3/src/components/shared/Charts.tsx`. These will be used inline in KPIs, financial reports, and dashboards.

## What to build

### 1. CSS tokens (add to global.css)
Add to `apps/blu_v3/src/styles/global.css` inside `:root { }`:
```css
--chart-1: var(--ac);      /* #8C5FDB purple */
--chart-2: var(--ok);      /* #10B981 green */
--chart-3: #3B82F6;        /* blue */
--chart-4: var(--att);     /* #F59E0B amber */
--chart-5: var(--urg);     /* #EF4444 red */
--chart-6: #EC4899;        /* pink */
--chart-7: #14B8A6;        /* teal */
--chart-8: #8B5CF6;        /* violet */
```

### 2. Chart components (`Charts.tsx`)

Create `apps/blu_v3/src/components/shared/Charts.tsx` with these exported components:

#### `LineChart`
```typescript
interface LineChartProps {
  data: { label: string; value: number }[]
  width?: number
  height?: number
  color?: string
  gradient?: boolean
  showDots?: boolean
  showGrid?: boolean
  showLabels?: boolean
  formatValue?: (v: number) => string
}
```
- Renders `<svg>` with: grid lines (dashed), Y-axis labels, line path (stroke), gradient area fill, data point circles, X-axis labels
- Smooth line with `stroke-linecap="round" stroke-linejoin="round"`
- Last data point gets a larger circle (accent color)

#### `BarChart`
```typescript
interface BarChartProps {
  data: { label: string; value: number }[]
  width?: number
  height?: number
  color?: string
  showLabels?: boolean
  maxBars?: number
}
```
- Vertical bars with rounded top (`rx="3"`)
- Consistent spacing between bars
- X-axis labels below
- Y-axis grid lines

#### `DonutChart`
```typescript
interface DonutSegment { label: string; value: number; color: string }
interface DonutChartProps {
  data: DonutSegment[]
  size?: number
  strokeWidth?: number
  showLegend?: boolean
}
```
- SVG circle arcs using `stroke-dasharray`/`stroke-dashoffset`
- Legend below with colored dots + label + percentage
- Center text showing total

#### `Sparkline`
```typescript
interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
  positive?: boolean
}
```
- Tiny inline SVG (default 80x24) with just the line path
- No axes, no labels, no grid
- Optional green/red color based on `positive` flag
- Last point highlighted with a small circle

#### `Gauge`
```typescript
interface GaugeProps {
  value: number
  min?: number
  max?: number
  thresholds?: { low: number; mid: number }
  label?: string
  size?: number
}
```
- Semi-circular arc with 3 color bands (red/yellow/green based on thresholds)
- Value displayed in center
- Min/max labels at arc ends

### 3. Usage pattern

Each component should be a pure function component with no external dependencies (just SVG). All use the CSS variable colors.

Example usage:
```tsx
<LineChart
  data={[
    { label: 'Jan', value: 30000 },
    { label: 'Fev', value: 45000 },
    { label: 'Mar', value: 38000 },
  ]}
  width={400}
  height={200}
  color="var(--ac)"
  gradient
  showDots
  showGrid
  formatValue={(v) => `R$ ${(v/1000).toFixed(0)}k`}
/>
```

### 4. Styling notes
- Use `fill="var(--mu)"` for axis text at font-size 10px
- Use `stroke="var(--gb)" stroke-dasharray="4 4"` for grid lines
- Use class-based approach: `.chart-tooltip`, `.chart-grid`, `.chart-axis`
- For gradient fills, use `<defs><linearGradient>` with `stop-color` using the same color at varying opacities (0.3 → 0.02)

### 5. Verification
1. `cd apps/blu_v3 && npx tsc --noEmit` — zero errors in Charts.tsx
2. Import and use one chart in EstrategiaRoom.tsx to verify it renders without runtime errors

## File
`/home/ec2-user/repo_platform/apps/blu_v3/src/components/shared/Charts.tsx`
