# Issue 4: @media Print Export Mode

## Goal
Add `@media print` CSS to the app's global stylesheet so that all pages render in white/black mode when printed/exported, turning the dark-themed app into clean, professional documents.

## What to build

Add to the END of `apps/blu_v3/src/styles/global.css`:

```css
/* ── PRINT / EXPORT MODE ── */
@media print {
  html, body {
    background: #fff !important;
    color: #000 !important;
    padding: 0;
    margin: 0;
    font-size: 11pt;
  }
  body::before { display: none !important; } /* remove bg gradients */
  
  /* Reset all CSS variables to white/black */
  body {
    --bg: #fff !important;
    --fg: #000 !important;
    --mu: #666 !important;
    --mu2: #333 !important;
    --glass: #fff !important;
    --gl2: #f5f5f5 !important;
    --gb: #ddd !important;
    --gb2: #bbb !important;
    --ac: #1a237e !important;
    --adim: rgba(26,35,126,0.08) !important;
    --shadow-1: none !important;
    --shadow-2: none !important;
    --shadow-3: none !important;
  }
  
  /* Shell layout */
  .shell { display: block !important; height: auto !important; }
  .topbar { display: none !important; }
  .sidebar { display: none !important; }
  .main { overflow: visible !important; height: auto !important; }
  .home-grid, .room-grid { display: block !important; padding: 0 !important; gap: 0 !important; }
  .rcol { display: block !important; width: 100% !important; }
  .bstrip { display: block !important; }
  
  /* Panels */
  .panel {
    background: #fff !important;
    border: 1px solid #ddd !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    break-inside: avoid;
    page-break-inside: avoid;
    margin-bottom: 12px !important;
  }
  .panel:hover { border-color: #ddd !important; box-shadow: none !important; }
  
  /* Remove glass effects */
  .ich { background: #fff !important; border-color: #ddd !important; box-shadow: none !important; backdrop-filter: none !important; }
  .anl-card { background: #fff !important; border-color: #ddd !important; }
  
  /* KPI cells */
  .kpi-cell { background: #f9f9f9 !important; border-color: #ddd !important; }
  .kpi-val { color: #000 !important; }
  .kpi-d.up { color: #006400 !important; }
  .kpi-d.dn { color: #8b0000 !important; }
  
  /* Badges */
  .bu { background: #fee !important; color: #c00 !important; border: 1px solid #c00 !important; }
  .bw { background: #ffe !important; color: #960 !important; border: 1px solid #960 !important; }
  .bo { background: #efe !important; color: #060 !important; border: 1px solid #060 !important; }
  .tbdg { background: #c00 !important; color: #fff !important; }
  
  /* Buttons */
  .btn { border: 1px solid #999 !important; background: #fff !important; color: #000 !important; }
  .bp { background: #1a237e !important; color: #fff !important; border-color: #1a237e !important; }
  .bs { background: #f5f5f5 !important; border-color: #ddd !important; color: #333 !important; }
  .bg { background: transparent !important; color: #333 !important; }
  .brd { background: #c00 !important; color: #fff !important; }
  
  /* Tabs */
  .rtab.on { border-bottom-color: #000 !important; color: #000 !important; }
  .rtab { color: #666 !important; }
  
  /* Decision cards */
  .dc-row:hover { background: #f5f5f5 !important; }
  
  /* Tables */
  table { border-collapse: collapse !important; }
  th { background: #f5f5f5 !important; color: #000 !important; border-bottom: 2px solid #ccc !important; }
  td { border-bottom: 1px solid #eee !important; }
  
  /* Images, svg */
  svg { max-width: 100% !important; }
  
  /* Hide non-essential */
  .rcol-resize-handle { display: none !important; }
  .rh { display: none !important; }
  .ph-add { display: none !important; }
  .ph-lnk { display: none !important; }
  .ibtn { display: none !important; }
  .av { display: none !important; }
  .toasts { display: none !important; }
  .rdot { display: none !important; }
  .intg-modal { display: none !important; }
  
  /* Ensure tables don't break across pages */
  table, tr, td, th { break-inside: avoid; page-break-inside: avoid; }
  
  /* Page margin */
  @page { margin: 1.5cm; }
  
  /* URLs after links (optional, useful for printed docs) */
  a[href^="http"]::after { content: " (" attr(href) ")"; font-size: 9pt; color: #666; }
}
```

## File
- `/home/ec2-user/repo_platform/apps/blu_v3/src/styles/global.css`

## Verification
1. `cd apps/blu_v3 && npx tsc --noEmit` — zero errors
2. Open any page in the browser, press Ctrl+P → preview shows white/black mode
