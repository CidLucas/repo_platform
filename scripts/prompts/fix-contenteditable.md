# Fix contentEditable editor: duplication, garbage HTML, and simplify diff behavior

## Context

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`

The contentEditable editor is generating duplicated text and garbage HTML. Root causes:

1. `renderMarkdownToHtml()` uses inline spans with CSS variables like `<span style="color: var(--mu2);">`. When the user edits in contentEditable, these spans persist in the innerHTML, and `htmlToMarkdown()` doesn't clean them properly, causing text duplication and raw HTML tags in the markdown output.

2. `refreshEditorDiff()` on blur replaces the entire innerHTML with diff HTML (line-level diff). When the user then edits this diff HTML and it gets converted back via `htmlToMarkdown`, the result is garbage.

## What to change

### 1. Simplify `renderMarkdownToHtml()`
Remove ALL inline CSS from the generated HTML tags. Use plain semantic HTML tags only:
- `# heading` → `<h1>text</h1>` (no style attr)
- `## heading` → `<h2>text</h2>` (no style attr)
- `- item` → `<ul><li>text</li></ul>` (standard ul/li)
- `plain text` → `<p>text</p>` (no style attr)
- `**bold**` → `<strong>text</strong>`
- `---` → `<hr>`

No spans with color/margin/font-size. Just pure semantic HTML. This makes the round-trip HTML→Markdown clean.

### 2. Fix `htmlToMarkdown()`
Make it strip ALL HTML tags and attributes before converting. Add these regex passes BEFORE the existing ones:
```
.replace(/<span[^>]*>/gi, '')
.replace(/<\/span>/gi, '')
.replace(/<div[^>]*>/gi, '')
.replace(/<\/div>/gi, '\n')
.replace(/ style="[^"]*"/gi, '')  // Strip ALL inline styles
```
Keep the existing conversions for h1→#, h2→##, strong→**bold**, li→- , p→paragraph.

After all conversions, add a final cleanup:
```
.replace(/<[^>]+>/g, '')  // Strip any remaining HTML tags
.replace(/^\s+$/gm, '')   // Strip whitespace-only lines
.replace(/\n{3,}/g, '\n\n')
.trim()
```

### 3. Remove `refreshEditorDiff()` entirely
Delete the `refreshEditorDiff` function and its `useCallback`. The onBlur should NOT replace the innerHTML. The diff visual (strikethrough/colored) should be handled DIFFERENTLY:

Instead of replacing innerHTML with diff HTML:
- When user deletes text (Backspace/Delete): intercept the keystroke and wrap the deleted content in `<del>` tags instead of actually removing it
- When user adds text: just let them type normally (the save diff badge still tracks changes)

BUT this is complex to implement with contentEditable. SIMPLER approach: 
- Remove `refreshEditorDiff` completely
- The editor always shows the formatted markdown (plain semantic HTML)
- The diff tracking badge in the toolbar still shows how many changes were made
- The diff visual is ONLY shown in the existing analytics card area, not in the editor itself

So onBlur does NOTHING to the innerHTML. Just let the user edit normally.

### 4. Remove innerHTML replacement on doc switch

The `useEffect` that sets `editorRef.current.innerHTML` should ONLY set the initial content via the ref when the document changes. It should use the simplified `renderMarkdownToHtml` (plain HTML, no inline styles). Remove the `isDirty ? diff.html : renderMarkdownToHtml(...)` logic — always use `renderMarkdownToHtml`.

```typescript
useEffect(() => {
  if (!editorRef.current || !selectedDocId) return
  if (selectedDocId.startsWith('report-') && reportLoading) return
  editorRef.current.innerHTML = renderMarkdownToHtml(editorContent)
}, [selectedDocId, reportLoading])
```

### 5. onInput should only update state, not touch DOM

The onInput handler should:
1. Get innerHTML from the contentEditable
2. Convert to markdown via the fixed `htmlToMarkdown`
3. Call `setEditorContent(md)` — that's it. No DOM manipulation.

The onBlur should do NOTHING (no refresh, no sync).

## Verification

After changes:
1. `cd apps/blu_v3 && npx tsc --noEmit` — zero errors in EstrategiaRoom.tsx
2. Typing in the editor does NOT cause cursor to jump
3. No text duplication when typing
4. No HTML garbage in the saved markdown content
5. Deleting text removes it cleanly (no duplications)
6. The diff badge in toolbar still tracks changes
