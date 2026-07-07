# Track Changes no contentEditable — Backspace/Delete vira <del>, texto novo destacado

## Arquivo
`/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`

## O que implementar

### 1. Backspace/Delete → <del> (strikethrough) em vez de remover

No contentEditable, interceptar **beforeinput** via ref para capturar `deleteContentBackward` e `deleteContentForward`:

```typescript
// Adicionar dentro do component, apos a declaracao do editorRef
useEffect(() => {
  const el = editorRef.current
  if (!el) return

  const handler = (e: InputEvent) => {
    if (e.inputType === 'deleteContentBackward' || e.inputType === 'deleteContentForward') {
      e.preventDefault()

      const sel = window.getSelection()
      if (!sel || !sel.rangeCount) return
      const range = sel.getRangeAt(0)

      // Se nao ha selecao, captura 1 caractere na direcao da delecao
      if (range.collapsed) {
        if (e.inputType === 'deleteContentBackward' && range.startOffset > 0) {
          range.setStart(range.startContainer, range.startOffset - 1)
        } else if (e.inputType === 'deleteContentForward') {
          const len = range.startContainer.textContent?.length ?? 0
          if (range.startOffset < len) {
            range.setEnd(range.startContainer, range.startOffset + 1)
          } else { return }
        } else { return }
      }

      const fragment = range.extractContents()
      if (!fragment.textContent) return

      const del = document.createElement('del')
      del.appendChild(fragment)
      range.insertNode(del)

      // Move cursor para depois do <del>
      range.setStartAfter(del)
      range.collapse(true)
      sel.removeAllRanges()
      sel.addRange(range)

      // Forcar sync do state (dispara onInput artificial)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
  }

  el.addEventListener('beforeinput', handler as EventListener)
  return () => el.removeEventListener('beforeinput', handler as EventListener)
}, [editorRef.current]) // ref won't change after mount, deps are fine
```

### 2. Texto adicionado com cor diferente

Adicionar CSS global no contentEditable para `<del>` e `ins`/highlight:

No contentEditable:
```
style={{ outline: 'none', minHeight: '100%', lineHeight: 1.75, fontSize: 13 }}
```

Quando o usuario digita, a `<ins>` tag ou um wrapper colorido aparece. A forma mais limpa: no `onInput`, apos atualizar o state, aplicar estilo incremental:

APOS cada `onInput`, pegar o innerHTML e envolver o NOVO texto (diferenca entre o texto anterior e o atual) em `<span style="background:rgba(16,185,129,.15);color:var(--ok)">`.

Mas isso e complexo e pode causar cursor jumping. ALTERNATIVA MAIS SIMPLES:

**Apenas adicionar CSS para `<del>` no contentEditable:**

```css
/* Adicionar no componente como style tag ou inline */
contentEditable del {
  text-decoration: line-through;
  color: rgba(239,68,68,.7);
  background: rgba(239,68,68,.08);
}
```

E garantir que a funcao `htmlToMarkdown` converta `<del>` de volta para markdown (~~texto~~).

Atualizar `htmlToMarkdown` para:
```
.replace(/<del[^>]*>/gi, '~~')
.replace(/<\/del>/gi, '~~')
```

### 3. htmlToMarkdown: preservar strikethrough

Adicionar no `htmlToMarkdown`, ANTES das outras conversoes de tag:
```
.replace(/<del[^>]*>/gi, '~~')
.replace(/<\/del>/gi, '~~')
```

### 4. renderMarkdownToHtml: suportar ~~strikethrough~~

Adicionar suporte a `~~texto~~` no `renderMarkdownToHtml`:
```
// No final, processar ~~text~~ → <del>text</del>
// Depois de gerar o HTML, aplicar:
html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>')
```

### 5. Estilo visual

Adicionar um `<style>` tag dentro do contentEditable container OU inline no componente:

```typescript
// No mesmo useEffect do beforeinput, adicionar:
const styleEl = document.createElement('style')
styleEl.textContent = `
  del { text-decoration: line-through; color: rgba(239,68,68,.7); background: rgba(239,68,68,.08); border-radius: 2px; }
`
el.parentElement?.insertBefore(styleEl, el)
```

## IMPORTANTE

- Nao usar `dangerouslySetInnerHTML` — continuar usando `ref` para innerHTML
- Nao substituir o innerHTML inteiro no input (senao cursor pula)
- O `beforeinput` handler modifica o DOM incrementalmente, sem re-renderizar o React
- Sync pro state continua via `onInput` handler existente
- Nao remover o tratamento de `onInput` que ja existe

## Verificacao
1. `cd apps/blu_v3 && npx tsc --noEmit` — zero erros em EstrategiaRoom.tsx
2. Backspace em texto → aparece ~~tachado~~ em vez de sumir
3. Delete em texto → aparece ~~tachado~~
4. Selecionar texto + Backspace → selecao inteira fica ~~tachada~~
5. Digitar texto novo → aparece normalmente (sem cor diferente por enquanto, so o ~~tachado~~)
6. Salvar → ~~tachado~~ convertido para ~~texto~~ no markdown
7. Cursor nao pula ao digitar
