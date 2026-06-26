import { useState, useRef, useCallback } from 'react'
import { useAppStore } from '../../store/appStore'

const DEFAULT_DOC = `CONTRATO DE PRESTAÇÃO DE SERVIÇOS

Partes:
Contratante: Cliente Central Ltda., CNPJ 12.345.678/0001-90
Contratada: Blu Empresa EIRELI, CNPJ 98.765.432/0001-10

Objeto:
Prestação de serviços de consultoria e gestão operacional pelo período de 12 (doze) meses, com início em 01/06/2026.

Valor:
O valor mensal é de R$ 48.000,00 (quarenta e oito mil reais), com reajuste anual pelo IPCA.

Desconto de Fidelidade:
Em razão do aumento de volume de 40%, aplica-se desconto de fidelidade de 8% sobre a mensalidade base.

Vigência:
Este contrato vigorará por 12 (doze) meses, podendo ser renovado por igual período mediante acordo entre as partes.

Local e data: São Paulo, 06 de maio de 2026.`

interface EditorOverlayProps {
  open: boolean
  docName: string
  onClose: () => void
  initialContent?: string
  onSave?: (text: string) => void
}

function computeDiff(original: string, current: string): { html: string; changes: number } {
  if (current === original) {
    return {
      html: '<p style="color:var(--mu);font-size:12px;margin-top:20px;text-align:center">Sem alterações</p>',
      changes: 0,
    }
  }
  const origLines = original.split('\n')
  const currLines = current.split('\n')
  let html = ''
  let changes = 0
  const maxLen = Math.max(origLines.length, currLines.length)
  for (let i = 0; i < maxLen; i++) {
    const o = origLines[i] ?? ''
    const c = currLines[i] ?? ''
    if (o === c) {
      html += `<div style="padding:1px 0;color:var(--mu2)">${o || '&nbsp;'}</div>`
    } else if (c && !o) {
      html += `<div class="diff-add" style="margin:1px 0">${c}</div>`
      changes++
    } else if (o && !c) {
      html += `<div class="diff-del" style="margin:1px 0">${o}</div>`
      changes++
    } else {
      html += `<div class="diff-del" style="margin:1px 0">${o}</div>`
      html += `<div class="diff-add" style="margin:1px 0">${c}</div>`
      changes++
    }
  }
  return { html, changes }
}

export default function EditorOverlay({ open, docName, onClose, initialContent, onSave }: EditorOverlayProps) {
  const { approve, addToast } = useAppStore()
  const [text, setText] = useState(initialContent ?? DEFAULT_DOC)
  const original = useRef(initialContent ?? DEFAULT_DOC)

  const { html: diffHtml, changes } = computeDiff(original.current, text)
  const status = changes === 0 ? 'Sem alterações' : 'Editando — alterações não salvas'
  const badge = changes === 0 ? '0 alterações' : `${changes} ${changes === 1 ? 'alteração' : 'alterações'}`

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(text)
    } else {
      addToast('ok', 'Salvo', 'Rascunho salvo com sucesso.')
    }
  }, [onSave, text, addToast])

  const handleSign = useCallback(() => {
    approve('dd1', 'Proposta assinada. Cliente Central notificado.')
    onClose()
  }, [approve, onClose])

  return (
    <div className={`ed-overlay${open ? ' open' : ''}`} id="edOverlay">
      <div className="ed-topbar">
        <div className="ed-title" id="edTitle">{docName}</div>
        <button className="btn bs" style={{ fontSize: 11 }} onClick={handleSave}>
          💾 Salvar rascunho
        </button>
        <button className="btn bp" style={{ fontSize: 11 }} onClick={handleSign}>
          ✍️ Assinar e fechar
        </button>
        <button
          className="ibtn"
          onClick={onClose}
          style={{ marginLeft: 4, color: 'var(--mu2)', width: 32, height: 32, fontSize: 14 }}
        >
          ✕
        </button>
      </div>
      <div className="ed-body">
        <div className="ed-pane">
          <div className="ed-pane-hd">✏️ Edição</div>
          <textarea
            className="ed-textarea"
            id="edTextarea"
            spellCheck={false}
            value={text}
            onChange={e => setText(e.target.value)}
          />
        </div>
        <div className="ed-pane">
          <div className="ed-pane-hd">🔍 Revisão de alterações</div>
          <div
            className="ed-content"
            id="edDiff"
            dangerouslySetInnerHTML={{ __html: diffHtml }}
          />
        </div>
      </div>
      <div className="ed-footer">
        <span className="ed-status" id="edStatus">{status}</span>
        <span className="ed-diff-badge" id="edBadge">{badge}</span>
      </div>
    </div>
  )
}
