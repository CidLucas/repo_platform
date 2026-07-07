# EstrategiaRoom Redesign

## Goal
Adaptar `apps/blu_v3/src/pages/app/EstrategiaRoom.tsx` para ter o layout/design do arquivo `scripts/prompts/estrategia-room-design.html`.

## What to keep
- All existing imports, API calls, queries, mutations, state variables
- Objetivos tab with ApprovalCard / ApprovalCardDocs (keep as-is)
- Config tab with RoutineConfigSection (keep as-is)
- Analytics card at panel bottom (keep as-is, just minor visual polish)
- Bottom strip with insights (keep as-is)
- Right column CollapsiblePanel for Análises (keep as-is)
- All existing types, helpers (MarkdownReport, renderMarkdownLine, formatCompactBRL, relativeTime)

## What to change

### 1. Documentos tab (tab === 'documentos')
Replace current simple report viewer with full document editor:

**Layout:**
- Outer container: `display:flex; flex:1; overflow:hidden`
- Left sidebar: `width:230px; flex-shrink:0; border-right:1px solid var(--gb); display:flex; flex-direction:column; overflow:hidden`
  - Top: "Novo Documento" button (full width, with onClick from existing `handleStartBlank`)
  - Below: scrollable document list with items showing type icon + name + date
- Right panel: `flex:1; display:flex; flex-direction:column; overflow:hidden`
  - Toolbar row: doc name + view mode buttons (edit/split/preview) + Salvar + Assinar buttons
  - Editor area (flex:1): shows edit pane(s) based on view mode
  - Status bar: shows save status and diff badge

**View modes (editorViewMode state):**
- `'edit'` → only edit pane (textarea)
- `'split'` → edit pane left + preview pane right (split via border-right)
- `'preview'` → only preview pane

**Document list items:**
- Each item shows: type icon (colored box with type letters like MD, DOC, PDF), name, relative date
- Selected item gets highlighted background + left border accent
- Clicking an item loads its content into editor (sets editorContent + originalContent)

**Documents data:**
Use existing data sources:
- `contextReports` for reports (already loaded via contextReportsQ)
- `docTemplates` for templates
- The inline `_getDocs()` mock data from the HTML as fallback
- Each doc has: id, name, type (MD/DOC/PDF), typeColor, date, content (markdown string)

**Diff tracking:**
- On mount and when editorContent changes, compute diff between `originalContent` and current `editorContent`
- Diff badge shows count: "3 alterações" (or "1 alteração" if count === 1)
- Diff preview: when editorViewMode is 'split' or 'preview', show diff in preview pane:
  - Unchanged lines: neutral
  - Added lines: green left border + green background
  - Removed lines: red strikethrough
  - Changed lines: show both (old strikethrough + new green)
- Status bar text: "Alterações não salvas" when dirty, "Sem alterações" when clean

**Save button:**
- Save button onClick sets `originalContent = editorContent` (resets dirty state)
- Also calls existing `saveDocMut.mutate(text)` if `docBeingCreated` is set

**Render markdown preview:**
Reuse the existing `MarkdownReport` component (or inline renderMarkdown logic) for the preview pane.

### 2. Conhecimento tab (tab === 'conhecimento')
Replace the full `<BibliotecaRoom />` import with inline implementation:

**Layout:**
- Outer container: `display:flex; flex:1; overflow:hidden`
- Left sidebar: `width:216px; flex-shrink:0; border-right:1px solid var(--gb); display:flex; flex-direction:column; overflow:hidden`
  - Top header: "Pastas" label
  - Folder tree with items. Each folder: icon + label + count + optional chevron for expandable
  - Folders: "Todos os documentos" (📁), "Estratégia" (🎯) with children "OKRs" (📋), "Planejamento" (📈), "Relatórios" (📊), "Jurídico" (⚖), "Pesquisa" (🔍)
- Right panel: 
  - Top bar: filtered count label + "Adicionar" button
  - Drag-and-drop zone (dashed border, centered text "Arraste arquivos aqui (PDF, DOCX, CSV, XLSX, TXT)")
  - Document card grid: `display:grid; grid-template-columns:repeat(auto-fill,minmax(175px,1fr)); gap:8px`
  - Each card: type icon (top-left), status badge (top-right), name (2-line clamp), folder pill + date, "Abrir no editor" link
  - Empty state: folder icon + "Nenhum documento nesta pasta"

**Folder state:**
- `selectedFolder` state (default: 'all')
- `expandedFolderIds` array for expandable folders
- Clicking a folder with children toggles expand; clicking a leaf folder selects it
- Folder indent: `8 + depth * 14` pixels

**Document data:**
- Use existing `useKnowledgeBase` hook for documents (import at top of file)
- OR use inline mock data matching the HTML's `_getDocs()` pattern
- Filter by folder: if selectedFolder === 'all', show all; else filter by folder property

**Card click:** clicking a card opens that document in the Documentos tab (sets selectedDocId + editorContent + switches tab)

**Drag-and-drop zone:** visual only (no actual DnD implementation needed for now)

### 3. Right column — Add KPIs Estratégicos panel
Add a new panel below the existing "Análises" CollapsiblePanel:

```tsx
<div className="panel" style={{flexShrink: 0}}>
  <div className="ph">
    <span className="ph-ico">📈</span>
    <span className="ph-ttl">KPIs Estratégicos</span>
  </div>
  <div className="pb">
    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6, padding:10}}>
      <div className="kpi-cell">
        <div className="kpi-lbl">MRR</div>
        <div className="kpi-val" style={{fontSize:15}}>R$ 612k</div>
        <div className="kpi-d up">+18% mês</div>
      </div>
      <div className="kpi-cell">
        <div className="kpi-lbl">Churn</div>
        <div className="kpi-val" style={{fontSize:15}}>2.4%</div>
        <div className="kpi-d dn">+0.3pp</div>
      </div>
      <div className="kpi-cell">
        <div className="kpi-lbl">NPS</div>
        <div className="kpi-val" style={{fontSize:15}}>68</div>
        <div className="kpi-d" style={{color:'var(--mu)'}}>estável</div>
      </div>
      <div className="kpi-cell">
        <div className="kpi-lbl">Clientes</div>
        <div className="kpi-val" style={{fontSize:15}}>347</div>
        <div className="kpi-d up">+23 mês</div>
      </div>
    </div>
  </div>
</div>
```

In future, these values should come from `contextMetrics` data. For now use the static values shown above.

### 4. Minor visual polish
- The Documentos tab left sidebar document list should use the same hover/selected patterns as the HTML
- The editor textarea should have proper styling: transparent background, proper font, line-height 1.75, 13px font size
- The toolbar buttons for view mode should toggle between `bp` (active) and `bs` (inactive) classes
- Documents tab left sidebar items should get a `borderLeft: '2px solid var(--ac)'` highlight when selected

## Implementation notes

### Remove these imports if no longer needed
- `BibliotecaRoom` import can be removed from imports at top
- `EditorOverlay` import can be removed (editor is now inline)

### New state variables needed
```typescript
// Document editor state
const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
const [editorContent, setEditorContent] = useState('')
const [originalContent, setOriginalContent] = useState('')
const [editorViewMode, setEditorViewMode] = useState<'edit' | 'split' | 'preview'>('split')

// Conhecimento tab state
const [selectedFolder, setSelectedFolder] = useState('all')
const [expandedFolderIds, setExpandedFolderIds] = useState<string[]>(['estrategia'])
```

### Document data source
Create a helper function `getStrategyDocs()` that returns documents combining:
- `contextReports` data (already loaded)
- The mock data from the HTML's `_getDocs()` method (inline)
- Each doc needs: id, name, type, typeColor, date, content, folder

### Diff computation
Create a `computeDiff` function that compares `originalContent` vs `editorContent` line by line and returns:
- `html`: rendered diff HTML string
- `count`: number of changed lines

### Important: Keep existing Objetivos + Config tabs working
The Objetivos tab (approvals) and Config tab should remain completely unchanged in their logic and rendering.

## Verification
1. Run `cd apps/blu_v3 && npx tsc --noEmit` — should pass
2. Run `npm run build` — should succeed  
3. Verify the component renders without crashes for all 4 tabs
