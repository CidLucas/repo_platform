import React, { useState, useEffect, useRef, useCallback } from 'react'
import * as XLSX from 'xlsx'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth, supabase } from '@blu/auth'
import { connectGoogleDrive } from '../../api/agenda'
import { useOnboardingDraft, VERTICAL_MAP, PORTE_MAP, type OnboardingDraft } from '../../hooks/useOnboardingDraft'
import { createCredential, createBigQueryCredentialWithDiscovery, type ConnectorPlatform, type CredentialPayload, type BigQueryCredentials } from '../../api/connectors'
import { useAppStore } from '../../store/appStore'

// Google Picker API — loaded dynamically via <script>, typed here for the builder chain
interface GooglePickerDocsView {
  setIncludeFolders: (v: boolean) => GooglePickerDocsView
  setMimeTypes: (m: string) => GooglePickerDocsView
}
interface GooglePickerBuilder {
  addView: (v: GooglePickerDocsView) => GooglePickerBuilder
  setOAuthToken: (t: string) => GooglePickerBuilder
  setDeveloperKey: (k: string) => GooglePickerBuilder
  setCallback: (cb: (data: { action: string; docs?: { id: string; name: string }[] }) => void) => GooglePickerBuilder
  build: () => { setVisible: (v: boolean) => void }
}
declare global {
  interface Window {
    gapi: { load: (api: string, cb: () => void) => void }
    google: {
      picker: {
        PickerBuilder: new () => GooglePickerBuilder
        DocsView: new () => GooglePickerDocsView
        Action: { PICKED: string; CANCEL: string }
      }
    }
  }
}

const DRIVE_PICKER_MIME_TYPES = [
  'application/vnd.google-apps.spreadsheet',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
  'text/csv',
].join(',')

function loadGapiScript(): Promise<void> {
  if (typeof window.gapi !== 'undefined') return Promise.resolve()
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://apis.google.com/js/api.js'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Falha ao carregar Google API'))
    document.head.appendChild(script)
  })
}

interface PendingCredential {
  platform: ConnectorPlatform
  nomServico: string
  credentials: CredentialPayload
}

type Step = 'auth' | 'info' | 'data' | 'mapping' | 'launch'

type CsvClassification = {
  confirmed: boolean
  schemaType: string
  canceled: boolean
}

const STEP_ORDER: Step[] = ['auth', 'info', 'data', 'mapping', 'launch']
const STEP_LABELS = ['Conta', 'Empresa', 'Dados', 'Mapeamento']

const VERTICALS = ['Comércio', 'Serviços', 'Indústria', 'Saúde', 'Educação', 'Agronegócio', 'Financeiro', 'Outro']
const TEAM_SIZES = ['Só eu', '2–10 pessoas', '10–50 pessoas', '50+ pessoas']

// Canonical field names for manual mapping — must match CANONICAL_SCHEMAS.invoices in match-columns
const CANONICAL_FIELDS = [
  'documento', 'data_competencia_id', 'quantidade', 'valor_unitario', 'valor', 'status',
  'tipo_lancamento', 'categoria', 'subcategoria',
  'cliente_cpf_cnpj', 'cliente_nome', 'cliente_telefone', 'cliente_cidade', 'cliente_uf',
  'fornecedor_cnpj', 'fornecedor_nome', 'fornecedor_telefone', 'fornecedor_cidade', 'fornecedor_uf',
  'produto_sku', 'produto_nome',
]

const VERTICAL_DISPLAY: Record<string, string> = {
  ecommerce: 'Comércio',
  servicos: 'Serviços',
  industria: 'Indústria',
  saude: 'Saúde',
  educacao: 'Educação',
  agro: 'Agronegócio',
  financeiro: 'Financeiro',
  outro: 'Outro',
}

const PORTE_DISPLAY: Record<string, string> = {
  solo: 'Só eu',
  micro: '2–10 pessoas',
  pequena: '10–50 pessoas',
  media: '50+ pessoas',
}

type SystemConfig = {
  id: string
  icon: string
  name: string
  sub: string
  connector: ConnectorPlatform | null
  comingSoon?: boolean
}

const SYSTEMS: SystemConfig[] = [
  { id: 'bigquery',   icon: '📊', name: 'BigQuery',   sub: 'Data warehouse', connector: 'bigquery' },
  { id: 'bling',      icon: '📦', name: 'Bling',      sub: 'ERP / NF-e',     connector: null, comingSoon: true },
  { id: 'omie',       icon: '⚙️', name: 'Omie',       sub: 'ERP',            connector: null, comingSoon: true },
  { id: 'shopify',    icon: '🛍', name: 'Shopify',    sub: 'E-commerce',     connector: 'shopify', comingSoon: true },
  { id: 'vtex',       icon: '🔷', name: 'VTEX',       sub: 'E-commerce',     connector: 'vtex', comingSoon: true },
  { id: 'postgresql', icon: '🐘', name: 'PostgreSQL', sub: 'Banco de dados',  connector: 'postgresql', comingSoon: true },
  { id: 'conta_azul', icon: '📋', name: 'Conta Azul', sub: 'ERP / NF-e',     connector: 'conta_azul', comingSoon: true },
]

// ─── Column mapping types (from match-columns edge function) ──────────────────

type MappingDetail = {
  source_column: string
  canonical_column: string | null
  confidence: number
  auto_matched: boolean
}

type NeedsReviewItem = {
  source: string
  candidates: { canonical: string; confidence: number }[]
}

export type ColumnMappingResult = {
  matched: Record<string, string>
  unmatched: string[]
  confidence_scores: Record<string, number>
  needs_review: NeedsReviewItem[]
  details: MappingDetail[]
}

async function callMatchColumns(sourceColumns: string[], schemaType?: string): Promise<ColumnMappingResult | null> {
  if (sourceColumns.length === 0) return null
  try {
    const { data, error } = await supabase.functions.invoke('match-columns', {
      body: { source_columns: sourceColumns, schema_type: schemaType || 'invoices' },
    })
    if (error) {
      console.warn('[onboarding] match-columns failed:', error.message)
      return null
    }
    return data as ColumnMappingResult
  } catch (e) {
    console.warn('[onboarding] match-columns error:', e)
    return null
  }
}

// Keywords that strongly suggest "main transaction sheet".
// Accent-stripped, lowercase — compared against normalised sheet names.
const TRANSACTION_SHEET_KEYWORDS = [
  'lancamentos', 'lancamento', 'faturamento', 'fatura', 'faturas',
  'transacoes', 'transacao', 'entradas', 'saidas', 'movimentacao',
  'movimentacoes', 'despesas', 'receitas', 'vendas', 'compras',
  'financeiro', 'pagamentos', 'pagamento', 'notas', 'registros',
]

function scoreSheetName(name: string): number {
  const n = name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  return TRANSACTION_SHEET_KEYWORDS.some(kw => n.includes(kw)) ? 1 : 0
}

function parseSpreadsheetHeaders(file: File): Promise<{ headers: string[]; sheetName: string }> {
  const isXlsx = /\.(xlsx|xls)$/i.test(file.name)

  if (isXlsx) {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target?.result as ArrayBuffer)
          const wb = XLSX.read(data, { type: 'array', sheetRows: 12 })
          // Score each sheet: name-keyword match wins; row count breaks ties.
          // sheetRows: 12 caps all large sheets at 12, so name score must be primary.
          const sheetScores = wb.SheetNames.map(name => {
            const rows = XLSX.utils.sheet_to_json<unknown[]>(wb.Sheets[name], { header: 1, defval: '' })
            return { name, score: scoreSheetName(name), rowCount: rows.length }
          })
          sheetScores.sort((a, b) => b.score - a.score || b.rowCount - a.rowCount)
          const bestSheet = sheetScores[0]?.name ?? wb.SheetNames[0]
          const ws = wb.Sheets[bestSheet]
          const rows = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, defval: '' })
          // Find the row with the most non-empty cells in the first 10 rows
          const searchRows = rows.slice(0, 10)
          const headerIdx = searchRows.reduce((bestIdx, row, i) => {
            const count = (row as unknown[]).filter((c) => String(c).trim() !== '').length
            const bestCount = (searchRows[bestIdx] as unknown[]).filter((c) => String(c).trim() !== '').length
            return count > bestCount ? i : bestIdx
          }, 0)
          const headers = ((rows[headerIdx] ?? []) as unknown[]).map((h: unknown) => String(h).trim()).filter(Boolean)
          resolve({ headers, sheetName: bestSheet })
        } catch {
          resolve({ headers: [], sheetName: '' })
        }
      }
      reader.onerror = () => resolve({ headers: [], sheetName: '' })
      reader.readAsArrayBuffer(file)
    })
  }

  // CSV — detect delimiter (semicolon or comma) and strip quotes, skip title row
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string ?? ''
      const lines = text.split(/\r?\n/).filter((l) => l.trim() !== '')
      const candidate = lines.length > 1 ? lines[1] : lines[0] ?? ''
      const delim = candidate.includes(';') ? ';' : ','
      // Find the row with the most non-empty columns in the first 10 lines
      const searchLines = lines.slice(0, 10)
      const headerLineIdx = searchLines.reduce((bestIdx, line, i) => {
        const count = line.split(delim).filter((c) => c.replace(/^"|"$/g, '').trim() !== '').length
        const bestCount = searchLines[bestIdx].split(delim).filter((c) => c.replace(/^"|"$/g, '').trim() !== '').length
        return count > bestCount ? i : bestIdx
      }, 0)
      const headers = (searchLines[headerLineIdx] ?? '').split(delim).map(h => h.replace(/^"|"$/g, '').trim()).filter(Boolean)
      resolve({ headers, sheetName: '' })
    }
    reader.onerror = () => resolve({ headers: [], sheetName: '' })
    reader.readAsText(file)
  })
}

// ─── ScrapeField ─────────────────────────────────────────────────────────────
// Animated typing reveal for website intel results

function ScrapeField({ label, value, delay = 0 }: { label: string; value: string; delay?: number }) {
  const [displayed, setDisplayed] = useState('')
  const [typing, setTyping] = useState(false)

  useEffect(() => {
    if (!value) { setDisplayed(''); return }
    setDisplayed('')
    setTyping(true)
    const startTimer = setTimeout(() => {
      let i = 0
      const interval = setInterval(() => {
        i++
        setDisplayed(value.slice(0, i))
        if (i >= value.length) { clearInterval(interval); setTyping(false) }
      }, 22)
      return () => clearInterval(interval)
    }, delay)
    return () => clearTimeout(startTimer)
  }, [value, delay])

  return (
    <div className="scrape-field">
      <div className="slabel">{label}</div>
      <div className={`svalue${typing ? ' typing' : ''}`}>{displayed || ' '}</div>
    </div>
  )
}

// ─── FlowTop ──────────────────────────────────────────────────────────────────

function FlowTop({ step, onBack }: { step: Step; onBack?: () => void }) {
  const stepIdx = STEP_ORDER.indexOf(step)
  return (
    <div className="flow-top">
      <div className="flow-logo" onClick={onBack} style={{ cursor: onBack ? 'pointer' : 'default' }}>
        <div className="logo-mark">B</div>
        <span>blu</span>
      </div>
      <div className="progress-steps">
        {STEP_LABELS.map((label, i) => {
          const done = stepIdx > i
          const active = stepIdx === i
          return (
            <React.Fragment key={label}>
              {i > 0 && <div className="ps-sep" />}
              <div className={`ps${done ? ' done' : active ? ' active' : ''}`}>
                <div className="ps-num">{done ? '✓' : i + 1}</div>
                {label}
              </div>
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}

// ─── StepAuth ─────────────────────────────────────────────────────────────────

function StepAuth({ onNext, mode }: { onNext: () => void; mode: 'login' | 'signup' }) {
  const { signInWithEmail, signUp } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  async function handleGoogle() {
    setError(null)
    const redirectTo = `${window.location.origin}/onboarding${mode === 'login' ? '?mode=login' : ''}`
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo },
    })
    if (error) setError(error.message)
  }

  async function handleSubmit() {
    setError(null)
    if (mode !== 'login' && password !== passwordConfirm) {
      setError('As senhas não coincidem.')
      return
    }
    setSubmitting(true)
    try {
      if (mode === 'login') {
        const { error } = await signInWithEmail(email, password)
        if (error) { setError(error.message); setSubmitting(false); return }
      } else {
        const { error } = await signUp(email, password)
        if (error) { setError(error.message); setSubmitting(false); return }
        onNext()
      }
    } catch (e: any) {
      setError(e?.message ?? 'Erro inesperado')
      setSubmitting(false)
    }
  }

  const isLogin = mode === 'login'

  return (
    <div className="flow-page on">
      <FlowTop step="auth" />
      <div className="flow-body">
        <div className="flow-card">
          <div className="fc-step">PASSO 1 DE 4</div>
          <div className="fc-h">{isLogin ? 'Bem-vindo de volta' : 'Boas-vindas ao blu'}</div>
          <div className="fc-sub">
            {isLogin
              ? 'Entre na sua conta para acessar o bureau.'
              : 'O seu escritório virtual com IA. Vamos configurar tudo em 3 minutos.'}
          </div>

          <button className="g-btn" onClick={handleGoogle} disabled={submitting}>
            <div className="g-icon" style={{ background: '#fff', color: '#333', fontSize: 11, fontWeight: 800 }}>G</div>
            {isLogin ? 'Entrar com Google' : 'Continuar com Google'}
          </button>

          <div className="auth-divider">— ou —</div>

          <div className="field">
            <label>Email</label>
            <input
              type="email"
              placeholder="carlos@suaempresa.com.br"
              value={email}
              onChange={e => setEmail(e.target.value)}
              disabled={submitting}
            />
          </div>
          <div className="field">
            <label>Senha</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={submitting}
              onKeyDown={e => !isLogin ? undefined : e.key === 'Enter' && handleSubmit()}
            />
          </div>
          {!isLogin && (
            <div className="field">
              <label>Confirmar senha</label>
              <input
                type="password"
                placeholder="••••••••"
                value={passwordConfirm}
                onChange={e => setPasswordConfirm(e.target.value)}
                disabled={submitting}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              />
            </div>
          )}

          {error && (
            <div style={{ fontSize: 12.5, color: 'var(--urg)', marginBottom: 4 }}>{error}</div>
          )}

          <button
            className="btn btn-blue"
            style={{ width: '100%' }}
            onClick={handleSubmit}
            disabled={submitting || !email || !password || (!isLogin && !passwordConfirm)}
          >
            {submitting ? 'Aguarde…' : isLogin ? 'Entrar' : 'Criar conta'}
          </button>

          {isLogin ? (
            <div style={{ textAlign: 'center', marginTop: 14, fontSize: 12.5, color: 'var(--muted)' }}>
              Não tem uma conta?{' '}
              <span
                style={{ color: 'var(--blue3)', cursor: 'pointer' }}
                onClick={() => navigate('/onboarding')}
              >
                Criar conta grátis →
              </span>
            </div>
          ) : (
            <div style={{ textAlign: 'center', marginTop: 14, fontSize: 12.5, color: 'var(--muted)' }}>
              Ao criar conta você concorda com os{' '}
              <a href="/termos" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--blue3)' }}>Termos de Uso</a> e a{' '}
              <a href="/privacidade" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--blue3)' }}>Política de Privacidade</a>.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── StepInfo ─────────────────────────────────────────────────────────────────

interface SiteContext {
  company_name?: string
  cnpj?: string
  vertical?: string
  cnpj?: string
  telefone?: string
  confidence: number
  suggested_agents?: string[]
  telefone?: string
}

function formatCnpj(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(0, 14)
  if (digits.length <= 11) {
    return digits
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d{1,2})$/, '$1-$2')
  }
  return digits
    .replace(/(\d{2})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1/$2')
    .replace(/(\d{4})(\d{1,2})$/, '$1-$2')
}

function deriveVerticalFromCnae(cnae: string): string {
  if (!cnae) return 'other'
  const code = cnae.replace(/\D/g, '').padStart(7, '0')
  const section = code.slice(0, 2)
  // CNAE section → vertical map
  if (['10', '11', '12'].includes(section)) return 'food'
  if (['45', '46', '47'].includes(section)) return 'retail'
  if (['58', '59', '60', '61', '62', '63'].includes(section)) return 'technology'
  if (['41', '42', '43'].includes(section)) return 'construction'
  if (['49', '50', '51', '52', '53'].includes(section)) return 'transport'
  if (['85'].includes(section)) return 'education'
  if (['86'].includes(section)) return 'health'
  if (['24', '25', '26', '27', '28', '29', '30', '31', '32', '33'].includes(section)) return 'industry'
  if (['64', '65', '66'].includes(section)) return 'financial'
  if (['01', '02', '03'].includes(section)) return 'agriculture'
  return 'services'
}

function StepInfo({
  onNext, onBack, saveDraft,
  initialNome, initialEmpresa, initialWebsite, initialVertical, initialPorte,
  initialProdutoServico, initialCnpj, initialTelefone,
}: {
  onNext: () => void
  onBack?: () => void
  saveDraft: (patch: Partial<OnboardingDraft>) => Promise<void>
  initialNome: string
  initialEmpresa: string
  initialWebsite: string
  initialVertical: string
  initialPorte: string
  initialProdutoServico: string
  initialCnpj: string
  initialTelefone: string
}) {
  const [nome, setNome] = useState(initialNome)
  const [empresa, setEmpresa] = useState(initialEmpresa)
  const [cnpj, setCnpj] = useState(initialCnpj)
  const [telefone, setTelefone] = useState(initialTelefone)
  const [website, setWebsite] = useState(initialWebsite)
  const [vertical, setVertical] = useState(initialVertical || '')
  const [teamSize, setTeamSize] = useState(initialPorte || '')
  const [produtoServico, setProdutoServico] = useState(initialProdutoServico || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [detecting, setDetecting] = useState(false)
  const [siteContext, setSiteContext] = useState<SiteContext | null>(null)
  const clearSiteCtx = () => setSiteContext(null)

  // ── CNPJ enrichment states (B-2, B-3, B-4, B-5) ─────────────────────────
  const [enrichedForCnpj, setEnrichedForCnpj] = useState<string>('')
  const [enrichingCnpj, setEnrichingCnpj] = useState(false)
  const [cnpjEnrichData, setCnpjEnrichData] = useState<null | {
    razao_social: string
    cnpj: string
    cnae: string
    cnae_descricao: string
    situacao: string
    uf: string
  }>(null)
  const [rateLimitMsg, setRateLimitMsg] = useState<string | null>(null)

  async function handleWebsiteBlur() {
    const url = website.trim()
    if (!url) return
    setDetecting(true)
    clearSiteCtx()
    try {
      const { data, error } = await supabase.functions.invoke('onboarding-website-intel', {
        body: { website_url: url },
      })
      if (error || !data) return
      const ctx = data as SiteContext
      // Auto-fill company name
      if (ctx.company_name && !empresa.trim()) setEmpresa(ctx.company_name)
      // Auto-fill CNPJ
      if (ctx.cnpj && !cnpj.trim()) {
        setCnpj(ctx.cnpj)
        setCnpj(prev => prev.replace(/\D/g, ""))
      }
      // Auto-fill telefone
      if (ctx.telefone && !telefone.trim()) setTelefone(ctx.telefone)
      // Auto-fill vertical
      const detected = VERTICAL_DISPLAY[ctx.vertical as string]
      if (detected && ctx.confidence >= 0.3) {
        setVertical(detected)
      }
      // Show context card for any confidence level to let user confirm/adjust
      if (ctx.vertical || ctx.company_name || ctx.cnpj || ctx.telefone) setSiteContext(ctx)
    } catch {
      // best-effort, silent
    } finally {
      setDetecting(false)
    }
  }

  async function handleCnpjBlur() {
    setRateLimitMsg(null)
    // B-5: Only dispatch for valid 14-digit CNPJ
    if (cnpj.length !== 14) return
    // B-2: Idempotency — skip if already enriched this CNPJ
    if (cnpj === enrichedForCnpj) return
    setRateLimitMsg(null)
    setEnrichingCnpj(true)
    try {
      const { data, error } = await supabase.functions.invoke('onboarding-cnpj-enrich', {
        body: { cnpj: cnpj },
      })
      if (error) return // silently swallowed (B-5)
      if (data?.error === "rate_limit") {
        setRateLimitMsg('Servico temporariamente indisponivel. Tente novamente em alguns instantes.')
        return
      }
      if (data) {
        setEnrichedForCnpj(cnpj)
        setCnpjEnrichData(data)
        // B-3: Auto-fill company name only if empty
        if (!empresa.trim() && data.razao_social) {
          setEmpresa(data.razao_social)
        }
      }
    } catch {
      // silently swallowed — no alert, no modal, no setError (B-5)
    } finally {
      setEnrichingCnpj(false)
    }
  }

  async function handleNext() {
    if (!empresa.trim()) { setError('Nome da empresa é obrigatório.'); return }
    if (!vertical) { setError('Selecione o setor da empresa.'); return }
    if (!teamSize) { setError('Selecione o tamanho da equipe.'); return }
    setSaving(true)
    setError(null)
    try {
      await saveDraft({
        nome: nome.trim(),
        empresa: empresa.trim(),
        cnpj: cnpj.replace(/\D/g, ''),
        website: website.trim(),
        vertical: VERTICAL_MAP[vertical] ?? null,
        porte: PORTE_MAP[teamSize] ?? teamSize,
        produtoServico: produtoServico.trim(),
      })
      onNext()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flow-page on">
      <FlowTop step="info" onBack={onBack} />
      <div className="flow-body">
        <div className="flow-card">
          <div className="fc-step">PASSO 2 DE 4</div>
          <div className="fc-h">Sobre a sua empresa</div>
          <div className="fc-sub">O blu usa estas informações para calibrar os agentes ao seu negócio.</div>
          <div className="row2">
            <div className="field">
              <label>Seu nome</label>
              <input type="text" placeholder="Carlos Lima" value={nome} onChange={e => setNome(e.target.value)} />
            </div>
            <div className="field">
              <label>Website <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(opcional)</span></label>
              <input
                type="url"
                placeholder="https://suaempresa.com.br"
                value={website}
                onChange={e => { setWebsite(e.target.value); setSiteContext(null) }}
                onBlur={handleWebsiteBlur}
              />
              {detecting && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 8, fontSize: 12.5, color: 'var(--muted2)' }}>
                  <div className="spin-sm" />
                  Seu agente está olhando seu site…
                </div>
              )}
            </div>
          </div>
          <div className="field">
            <label>Nome da empresa *</label>
            <input type="text" placeholder="Distribuidora Alvo" value={empresa} onChange={e => setEmpresa(e.target.value)} />
          </div>
          <div className="field">
            <label>
              CPF / CNPJ da empresa{' '}
              <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(opcional — usado para classificar transações automaticamente)</span>
            </label>
            <input
              type="text"
              placeholder="00.000.000/0001-00"
              value={formatCnpj(cnpj)}
              onChange={e => setCnpj(e.target.value.replace(/\D/g, ''))}
              onBlur={handleCnpjBlur}
              inputMode="numeric"
              maxLength={18}
            />
          </div>

          {/* CNPJ enrichment: loading indicator (B-4) */}
          {enrichingCnpj && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: -8, marginBottom: 8, fontSize: 12.5, color: 'var(--muted2)' }}>
              <div className="spin-sm" />
              Consultando Receita Federal...
            </div>
          )}

          {/* CNPJ enrichment: rate limit message (B-5) */}
          {rateLimitMsg && (
            <div style={{ marginTop: -8, marginBottom: 8, fontSize: 12, color: 'var(--amber, #ca8a04)' }}>
              {rateLimitMsg}
            </div>
          )}

          {/* CNPJ enrichment: Dados da Receita Federal section (B-3, B-4) */}
          {cnpjEnrichData && (
            <div className="scrape-panel" style={{ margin: '0 0 4px' }}>
              <div className="scrape-h">
                <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Dados da Receita Federal
                <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--green, #16a34a)', background: 'rgba(22, 163, 74, 0.1)', padding: '1px 7px', borderRadius: 20, marginLeft: 6 }}>Confirmado pela Receita</span>
              </div>
              <div className="scrape-grid">
                <ScrapeField label="Razão Social" value={cnpjEnrichData.razao_social} delay={0} />
                <ScrapeField label="CNPJ" value={formatCnpj(cnpjEnrichData.cnpj)} delay={100} />
                <ScrapeField label="CNAE" value={`${cnpjEnrichData.cnae} — ${cnpjEnrichData.cnae_descricao}`} delay={200} />
                {cnpjEnrichData.situacao && (
                  <ScrapeField label="Situação" value={cnpjEnrichData.situacao} delay={300} />
                )}
                {cnpjEnrichData.uf && (
                  <ScrapeField label="UF" value={cnpjEnrichData.uf} delay={300} />
                )}
              </div>
              <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-ghost"
                  style={{ fontSize: 12, padding: '4px 10px' }}
                  onClick={() => {
                    setCnpjEnrichData(null)
                    // Optionally clear auto-filled empresa if user didn't type it
                  }}
                >
                  Limpar dados da Receita
                </button>
              </div>
            </div>
          )}

          {/* Scrape panel: shown after website-intel returns results */}
          {siteContext && (
            <div className="scrape-panel" style={{ margin: '0 0 4px' }}>
              <div className="scrape-h">
                <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Encontrei sua empresa. Já anotei.
                {siteContext.confidence >= 0.7 ? (
                  <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--green, #16a34a)', background: 'rgba(22, 163, 74, 0.1)', padding: '1px 7px', borderRadius: 20, marginLeft: 2 }}>Confiança alta</span>
                ) : siteContext.confidence >= 0.3 ? (
                  <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--amber, #ca8a04)', background: 'rgba(202, 138, 4, 0.1)', padding: '1px 7px', borderRadius: 20, marginLeft: 2 }}>Confiança média</span>
                ) : null}
              </div>

              {siteContext.confidence < 0.5 && (
                <div className="scrape-warn">
                  Confiança baixa — revise os campos abaixo
                </div>
              )}

              <div className="scrape-grid">
                {siteContext.company_name && (
                  <ScrapeField label="Empresa" value={siteContext.company_name} delay={0} />
                )}
                {siteContext.vertical && (
                  <ScrapeField
                    label="Setor detectado"
                    value={VERTICAL_DISPLAY[siteContext.vertical] ?? siteContext.vertical}
                    delay={250}
                  />
                )}
                {siteContext.cnpj && (
                  <div key="cnpj" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ScrapeField label="CNPJ" value={formatCnpj(siteContext.cnpj)} delay={250} />
                    {siteContext.confidence >= 0.7 ? (
                      <span style={{ color: '#16a34a', background: '#dcfce7', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança alta</span>
                    ) : siteContext.confidence >= 0.3 ? (
                      <span style={{ color: '#ca8a04', background: '#fef9c3', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança média</span>
                    ) : null}
                  </div>
                )}
                {siteContext.telefone && (
                  <div key="telefone" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ScrapeField label="Telefone" value={siteContext.telefone} delay={500} />
                    {siteContext.confidence >= 0.7 ? (
                      <span style={{ color: '#16a34a', background: '#dcfce7', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança alta</span>
                    ) : siteContext.confidence >= 0.3 ? (
                      <span style={{ color: '#ca8a04', background: '#fef9c3', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança média</span>
                    ) : null}
                  </div>
                )}
                {siteContext.suggested_agents && siteContext.suggested_agents.length > 0 && (
                  <ScrapeField
                    label="Agentes sugeridos"
                    value={siteContext.suggested_agents.slice(0, 3).join(', ')}
                    delay={500}
                  />
                )}
                {siteContext.cnpj && (
                  <div key="cnpj" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ScrapeField label="CNPJ" value={formatCnpj(siteContext.cnpj)} delay={250} />
                    {siteContext.confidence >= 0.7 ? (
                      <span style={{ color: '#16a34a', background: '#dcfce7', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança alta</span>
                    ) : siteContext.confidence >= 0.3 ? (
                      <span style={{ color: '#ca8a04', background: '#fef9c3', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança média</span>
                    ) : null}
                  </div>
                )}
                {siteContext.telefone && (
                  <div key="telefone" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ScrapeField label="Telefone" value={siteContext.telefone} delay={500} />
                    {siteContext.confidence >= 0.7 ? (
                      <span style={{ color: '#16a34a', background: '#dcfce7', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança alta</span>
                    ) : siteContext.confidence >= 0.3 ? (
                      <span style={{ color: '#ca8a04', background: '#fef9c3', padding: '1px 7px', borderRadius: 20, fontSize: 10.5, fontWeight: 600 }}>Confiança média</span>
                    ) : null}
                  </div>
                )}
              </div>

              {/* Contextual questions — feed saveDraft via produtoServico */}
              <div style={{ borderTop: '1px solid var(--gb)', paddingTop: 14, marginTop: 4 }}>
                <div style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 10 }}>
                  Uma pergunta para calibrar seus agentes:
                </div>
                <div className="field" style={{ marginBottom: 0 }}>
                  <label style={{ fontSize: 12 }}>Principal produto ou serviço</label>
                  <input
                    type="text"
                    placeholder="ex: Software de gestão, Móveis planejados, Consultoria"
                    value={produtoServico}
                    onChange={e => setProdutoServico(e.target.value)}
                    style={{ marginTop: 4 }}
                  />
                </div>
              </div>
            </div>
          )}

          <div className="field">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              Setor *
              {siteContext && siteContext.confidence >= 0.7 ? (
                <span style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--green, #16a34a)', background: 'rgba(22, 163, 74, 0.1)', padding: '1px 7px', borderRadius: 20 }}>detectado automaticamente</span>
              ) : siteContext && siteContext.confidence >= 0.3 ? (
                <span style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--amber, #ca8a04)', background: 'rgba(202, 138, 4, 0.1)', padding: '1px 7px', borderRadius: 20 }}>detectado — confiança média</span>
              ) : null}
            </label>
            <div className="radio-pills">
              {VERTICALS.map(v => (
                <div key={v} className={`rp${vertical === v ? ' on' : ''}`} onClick={() => setVertical(v)}>{v}</div>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Tamanho da equipe *</label>
            <div className="radio-pills">
              {TEAM_SIZES.map(t => (
                <div key={t} className={`rp${teamSize === t ? ' on' : ''}`} onClick={() => setTeamSize(t)}>{t}</div>
              ))}
            </div>
          </div>
          {error && <div style={{ fontSize: 12.5, color: 'var(--urg)', marginBottom: 4 }}>{error}</div>}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            {onBack && <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>}
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleNext} disabled={saving}>
              {saving ? 'Salvando…' : 'Continuar →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── CredentialForm ───────────────────────────────────────────────────────────
// Collects connector credentials locally — no DB call here.
// Actual credential creation happens in StepLaunch after bootstrap creates
// the clientes_blu row and returns a client_id.

type FormData = Record<string, string>

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="field">
      <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {label}
        {children}
        {hint && <span style={{ fontSize: 11, color: 'var(--mu)', fontWeight: 400 }}>{hint}</span>}
      </label>
    </div>
  )
}

function FInput({ placeholder, type = 'text', value, onChange, mono }: {
  placeholder?: string; type?: string; value: string
  onChange: (v: string) => void; mono?: boolean
}) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
      style={mono ? { fontFamily: 'var(--mono)', fontSize: 11 } : undefined}
    />
  )
}

function FTextarea({ placeholder, value, onChange, rows = 4 }: {
  placeholder?: string; value: string; onChange: (v: string) => void; rows?: number
}) {
  return (
    <textarea
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
      rows={rows}
      style={{
        width: '100%', background: 'var(--glass)', border: '1px solid var(--gb)',
        borderRadius: 'var(--r)', color: 'var(--fg)', fontSize: 11,
        fontFamily: 'var(--mono)', padding: '8px 10px', resize: 'vertical',
        outline: 'none', boxSizing: 'border-box',
      }}
    />
  )
}

function FSelect({ label, value, onChange, children }: {
  label: string; value: string; onChange: (v: string) => void; children: React.ReactNode
}) {
  return (
    <div className="field">
      <label>
        {label}
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{ marginTop: 4, width: '100%', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', color: 'var(--fg)', padding: '7px 10px', fontSize: 12.5 }}
        >
          {children}
        </select>
      </label>
    </div>
  )
}

function renderConnectorFields(id: string, data: FormData, set: (k: string, v: string) => void) {
  switch (id) {
    case 'shopify':
      return (
        <>
          <Field label="Nome da loja" hint="Subdomínio da sua loja (ex: minha-loja.myshopify.com)">
            <FInput placeholder="minha-loja" value={data.shop_name ?? ''} onChange={v => set('shop_name', v)} />
          </Field>
          <Field label="Access Token" hint="Token de acesso da Admin API do Shopify.">
            <FInput type="password" placeholder="shpat_…" value={data.access_token ?? ''} onChange={v => set('access_token', v)} />
          </Field>
          <FSelect label="Versão da API" value={data.api_version ?? '2024-01'} onChange={v => set('api_version', v)}>
            <option value="2024-01">2024-01 (Recomendado)</option>
            <option value="2023-10">2023-10</option>
          </FSelect>
        </>
      )

    case 'bigquery':
      return (
        <>
          <Field
            label="Service Account JSON"
            hint="Cole o conteúdo do arquivo JSON da Service Account (contém project_id)."
          >
            <FTextarea
              placeholder={'{"type": "service_account", "project_id": "...", ...}'}
              value={data.service_account_json ?? ''}
              onChange={v => set('service_account_json', v)}
              rows={5}
            />
          </Field>
          <div className="row2">
            <Field label="Dataset ID">
              <FInput placeholder="meu_dataset" value={data.dataset_id ?? ''} onChange={v => set('dataset_id', v)} />
            </Field>
            <Field label="Nome da tabela" hint="Tabela que deseja sincronizar.">
              <FInput placeholder="minha_tabela" value={data.table_name ?? ''} onChange={v => set('table_name', v)} />
            </Field>
          </div>
          <FSelect label="Região dos dados" value={data.location ?? 'southamerica-east1'} onChange={v => set('location', v)}>
            <option value="southamerica-east1">South America — São Paulo</option>
            <option value="US">United States (US)</option>
            <option value="EU">European Union (EU)</option>
            <option value="us-east1">US East (us-east1)</option>
            <option value="us-west1">US West (us-west1)</option>
            <option value="asia-northeast1">Asia Northeast — Tokyo</option>
          </FSelect>
        </>
      )

    case 'postgresql':
      return (
        <>
          <div className="row2">
            <Field label="Host">
              <FInput placeholder="db.exemplo.com" value={data.host ?? ''} onChange={v => set('host', v)} />
            </Field>
            <Field label="Porta">
              <FInput placeholder="5432" value={data.port ?? '5432'} onChange={v => set('port', v)} />
            </Field>
          </div>
          <Field label="Banco de dados">
            <FInput placeholder="meu_banco" value={data.database ?? ''} onChange={v => set('database', v)} />
          </Field>
          <div className="row2">
            <Field label="Usuário">
              <FInput placeholder="postgres" value={data.user ?? ''} onChange={v => set('user', v)} />
            </Field>
            <Field label="Senha">
              <FInput type="password" placeholder="••••••••" value={data.password ?? ''} onChange={v => set('password', v)} />
            </Field>
          </div>
        </>
      )

    case 'vtex':
      return (
        <>
          <Field label="Nome da conta">
            <FInput placeholder="minhaloja" value={data.account_name ?? ''} onChange={v => set('account_name', v)} />
          </Field>
          <Field label="App Key">
            <FInput placeholder="vtexappkey_…" value={data.app_key ?? ''} onChange={v => set('app_key', v)} />
          </Field>
          <Field label="App Token">
            <FInput type="password" placeholder="…" value={data.app_token ?? ''} onChange={v => set('app_token', v)} />
          </Field>
          <FSelect label="Ambiente" value={data.environment ?? 'vtexcommercestable'} onChange={v => set('environment', v)}>
            <option value="vtexcommercestable">Produção (stable)</option>
            <option value="vtexcommercebeta">Beta</option>
          </FSelect>
        </>
      )

    case 'conta_azul':
      return (
        <>
          <Field label="E-mail do Conta Azul" hint="O e-mail que você usa para entrar no Conta Azul.">
            <FInput placeholder="voce@empresa.com.br" value={data.username ?? ''} onChange={v => set('username', v)} />
          </Field>
          <Field label="Senha do Conta Azul">
            <FInput type="password" placeholder="••••••••" value={data.password ?? ''} onChange={v => set('password', v)} />
          </Field>
        </>
      )

    default:
      return <p style={{ fontSize: 12.5, color: 'var(--mu)' }}>Configuração para este conector em breve.</p>
  }
}

function buildCredentialPayload(id: string, data: FormData): CredentialPayload | null {
  switch (id) {
    case 'shopify':
      if (!data.shop_name || !data.access_token) return null
      return { shop_name: data.shop_name, access_token: data.access_token }
    case 'bigquery': {
      if (!data.service_account_json) return null
      let sa: Record<string, unknown> = {}
      try { sa = JSON.parse(data.service_account_json) } catch { return null }
      return {
        project_id: (sa.project_id as string) ?? '',
        dataset_id: data.dataset_id ?? '',
        table_name: data.table_name ?? '',
        location: data.location ?? 'southamerica-east1',
        service_account_json: sa,
      }
    }
    case 'postgresql':
      if (!data.host || !data.database || !data.user) return null
      return { host: data.host, port: parseInt(data.port ?? '5432', 10), database: data.database, user: data.user, password: data.password ?? '' }
    case 'vtex':
      if (!data.account_name || !data.app_key || !data.app_token) return null
      return { account_name: data.account_name, app_key: data.app_key, app_token: data.app_token }
    case 'conta_azul':
      if (!data.username || !data.password) return null
      return { username: data.username, password: data.password }
    default:
      return null
  }
}

function CredentialForm({
  system, onSuccess, onCancel,
}: {
  system: SystemConfig
  onSuccess: (platform: ConnectorPlatform, nomServico: string, credentials: CredentialPayload) => void
  onCancel: () => void
}) {
  const [data, setData] = useState<FormData>({})
  const [error, setError] = useState<string | null>(null)
  const set = (k: string, v: string) => setData(prev => ({ ...prev, [k]: v }))

  function handleConnect() {
    setError(null)
    if (!system.connector) return
    const payload = buildCredentialPayload(system.id, data)
    if (!payload) { setError('Preencha todos os campos obrigatórios.'); return }
    onSuccess(system.connector, `${system.name} — ${system.id}`, payload)
  }

  return (
    <div>
      {renderConnectorFields(system.id, data, set)}
      {error && <div style={{ fontSize: 12.5, color: 'var(--urg)', margin: '8px 0 4px' }}>{error}</div>}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
        <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleConnect}>
          Conectar {system.name}
        </button>
      </div>
    </div>
  )
}

// ─── StepData ─────────────────────────────────────────────────────────────────

function StepData({
  onNext, onBack, onSkip, saveDraft, onMappingReady, onCredentialCollected, onCsvFileReady, onDriveFileReady,
}: {
  onNext: (mappingResult?: ColumnMappingResult | null) => void
  onBack: () => void
  onSkip: () => void
  saveDraft: (patch: Partial<OnboardingDraft>) => Promise<void>
  onMappingReady: (result: ColumnMappingResult | null) => void
  onCredentialCollected: (platform: ConnectorPlatform, nomServico: string, credentials: CredentialPayload) => void
  onCsvFileReady: (file: File | null, sheetName?: string, schemaType?: string) => void
  onDriveFileReady: (fileId: string) => void
}) {
  const [connected, setConnected] = useState<Record<string, boolean>>({})
  const [interested, setInterested] = useState<Record<string, boolean>>({})
  const [openForm, setOpenForm] = useState<string | null>(null)
  const [csvUploaded, setCsvUploaded] = useState(false)
  const [csvHeaders, setCsvHeaders] = useState<string[]>([])
  const [csvFileName, setCsvFileName] = useState<string>('')
  const [csvClassification, setCsvClassification] = useState<CsvClassification | null>(null)
  const [showClassificationModal, setShowClassificationModal] = useState(false)
  const csvRef = useRef<HTMLInputElement>(null)
  const csvFileRef = useRef<File | null>(null)
  const [driveOpen, setDriveOpen] = useState(false)
  const [driveUrl, setDriveUrl] = useState('')
  const [driveConnected, setDriveConnected] = useState(false)
  const [driveFileLabel, setDriveFileLabel] = useState('')
  const [driveError, setDriveError] = useState<string | null>(null)
  const [pickerLoading, setPickerLoading] = useState(false)

  function extractDriveFileId(urlOrId: string): string | null {
    const dMatch = urlOrId.match(/\/d\/([a-zA-Z0-9_-]{25,})/)
    if (dMatch) return dMatch[1]
    const idMatch = urlOrId.match(/[?&]id=([a-zA-Z0-9_-]{25,})/)
    if (idMatch) return idMatch[1]
    if (/^[a-zA-Z0-9_-]{25,44}$/.test(urlOrId.trim())) return urlOrId.trim()
    return null
  }

  function handleDriveUrlSubmit() {
    const fileId = extractDriveFileId(driveUrl.trim())
    if (!fileId) {
      setDriveError('URL inválida. Cole o link de compartilhamento do Google Sheets ou Drive.')
      return
    }
    setDriveError(null)
    setDriveConnected(true)
    setDriveFileLabel(driveUrl.includes('docs.google.com') ? 'Planilha do Google Drive' : `Drive: ${fileId.slice(0, 16)}…`)
    setDriveOpen(false)
    onDriveFileReady(fileId)
  }

  async function handleOpenPicker() {
    setPickerLoading(true)
    setDriveError(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const accessToken = session?.provider_token

      if (!accessToken) {
        setDriveError('Sessão Google não encontrada. Cole o link do arquivo abaixo ou conecte o Google Drive na página Admin → Integrações.')
        setPickerLoading(false)
        return
      }

      // Test if the token actually has Drive scope before opening Picker.
      // Regular Google sign-in only grants openid+email+profile — no Drive scope → Picker 403.
      const scopeTest = await fetch('https://www.googleapis.com/drive/v3/about?fields=user', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (!scopeTest.ok) {
        // Token lacks Drive scope — redirect to OAuth with drive.readonly.
        // The auth step will detect onboarding_returning_to_data on return
        // and route back to this step instead of navigating to /app.
        localStorage.setItem('onboarding_returning_to_data', '1')
        await connectGoogleDrive(window.location.href)
        return
      }

      await loadGapiScript()

      await new Promise<void>((resolve) => window.gapi.load('picker', resolve))

      const apiKey = import.meta.env.VITE_GOOGLE_PICKER_API_KEY ?? ''

      await new Promise<void>((resolve) => {
        const view = new window.google.picker.DocsView()
          .setIncludeFolders(false)
          .setMimeTypes(DRIVE_PICKER_MIME_TYPES)

        const picker = new window.google.picker.PickerBuilder()
          .addView(view)
          .setOAuthToken(accessToken)
          .setDeveloperKey(apiKey)
          .setCallback((data) => {
            if (data.action === window.google.picker.Action.PICKED && data.docs?.[0]) {
              const { id, name } = data.docs[0]
              setDriveConnected(true)
              setDriveFileLabel(name)
              setDriveOpen(false)
              setDriveError(null)
              onDriveFileReady(id)
              resolve()
            } else if (data.action === window.google.picker.Action.CANCEL) {
              resolve()
            }
          })
          .build()

        picker.setVisible(true)
      })
    } catch (e) {
      console.warn('[drive-picker]', e)
      setDriveError('Falha ao abrir o Drive. Tente colar o link manualmente.')
    } finally {
      setPickerLoading(false)
    }
  }

  function handleTileClick(system: SystemConfig) {
    if (connected[system.id]) return
    if (system.comingSoon) {
      setInterested(prev => ({ ...prev, [system.id]: !prev[system.id] }))
      return
    }
    setOpenForm(prev => prev === system.id ? null : system.id)
  }

  function handleConnectSuccess(systemId: string, platform: ConnectorPlatform, nomServico: string, credentials: CredentialPayload) {
    setConnected(prev => ({ ...prev, [systemId]: true }))
    setOpenForm(null)
    onCredentialCollected(platform, nomServico, credentials)
  }

  async function handleCsvChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    // Only set file info, not csvUploaded — modal will confirm
    setCsvFileName(file.name)
    const { headers, sheetName } = await parseSpreadsheetHeaders(file)
    setCsvHeaders(headers)
    // Store file ref for later use
    csvFileRef.current = file
    setShowClassificationModal(true)
  }

  async function handleNext() {
    const systems = [
      ...Object.keys(connected).filter(k => connected[k]),
      ...Object.keys(interested).filter(k => interested[k]),
    ]
    await saveDraft({ systems, csvUploaded })
    // Match CSV columns if uploaded; BQ columns are discovered in StepLaunch
    const schemaType = csvClassification?.schemaType || 'invoices'
    const mappingResult = csvHeaders.length > 0 ? await callMatchColumns(csvHeaders, schemaType) : null
    onMappingReady(mappingResult)
    onNext(mappingResult)
  }

  const selectedSystem = SYSTEMS.find(s => s.id === openForm)

  return (
    <div className="flow-page on">
      <FlowTop step="data" onBack={onBack} />
      <div className="flow-body">
        <div className="flow-card" style={{ maxWidth: 600 }}>
          <div className="fc-step">PASSO 3 DE 4</div>
          <div className="fc-h">Conecte seus dados</div>
          <div className="fc-sub">O blu aprende sobre seu negócio a partir dos seus dados. Escolha de onde vêm.</div>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 10 }}>Sistemas</div>
          <div className="dsrc-grid">
            {SYSTEMS.filter(s => !s.comingSoon).map(s => (
              <div
                key={s.id}
                className={`dsrc${connected[s.id] ? ' connected' : ''}${openForm === s.id ? ' active' : ''}`}
                onClick={() => handleTileClick(s)}
                style={{ position: 'relative', cursor: connected[s.id] ? 'default' : 'pointer' }}
              >
                <span className="dsrc-icon">{s.icon}</span>
                <div className="dsrc-name">{s.name}</div>
                <div className="dsrc-sub">
                  {connected[s.id] ? '✓ Conectado' : s.sub}
                </div>
              </div>
            ))}
          </div>

          {openForm && selectedSystem && !selectedSystem.comingSoon && (
            <div style={{ marginTop: 16, padding: 16, background: 'var(--surface)', border: '1px solid var(--gb)', borderRadius: 'var(--rl)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Conectar {selectedSystem.name}</div>
              <CredentialForm
                  system={selectedSystem}
                  onSuccess={(platform, nomServico, credentials) =>
                    handleConnectSuccess(selectedSystem.id, platform, nomServico, credentials)
                  }
                  onCancel={() => setOpenForm(null)}
                />
            </div>
          )}

          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', margin: '18px 0 10px' }}>Arquivos</div>
          <div className="dsrc-grid">
            <div
              className={`dsrc${csvUploaded ? ' connected' : ''}`}
              onClick={() => csvRef.current?.click()}
              style={{ cursor: 'pointer' }}
            >
              <span className="dsrc-icon">📄</span>
              <div className="dsrc-name">Planilha</div>
              <div className="dsrc-sub">
                {csvUploaded
                  ? `✓ ${csvFileName}${csvHeaders.length > 0 ? ` · ${csvHeaders.length} colunas` : ''}`
                  : 'CSV · XLSX · XLS'}
              </div>
            </div>
            <div
              className={`dsrc${driveConnected ? ' connected' : ''}${driveOpen ? ' active' : ''}`}
              onClick={() => { if (!driveConnected) setDriveOpen(prev => !prev) }}
              style={{ cursor: driveConnected ? 'default' : 'pointer' }}
            >
              <span className="dsrc-icon">🗂</span>
              <div className="dsrc-name">Google Drive</div>
              <div className="dsrc-sub">
                {driveConnected
                  ? `✓ ${driveFileLabel || 'Arquivo pronto'}`
                  : 'Sheets · Excel'}
              </div>
            </div>
          </div>
          {driveOpen && (
            <div style={{ marginTop: 16, padding: 16, background: 'var(--surface)', border: '1px solid var(--gb)', borderRadius: 'var(--rl)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Conectar Google Drive</div>

              {/* Primary action: open the file picker */}
              <button
                className="btn btn-primary"
                style={{ width: '100%', marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                onClick={handleOpenPicker}
                disabled={pickerLoading}
              >
                {pickerLoading ? 'Abrindo Drive…' : '📂 Navegar no Drive'}
              </button>

              {/* Divider */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <div style={{ flex: 1, height: 1, background: 'var(--gb)' }} />
                <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>ou cole o link</span>
                <div style={{ flex: 1, height: 1, background: 'var(--gb)' }} />
              </div>

              <input
                type="url"
                placeholder="https://docs.google.com/spreadsheets/d/…"
                value={driveUrl}
                onChange={e => { setDriveUrl(e.target.value); setDriveError(null) }}
                style={{ width: '100%', boxSizing: 'border-box', padding: '8px 10px', borderRadius: 'var(--rl)', border: '1px solid var(--gb)', background: 'var(--surface2)', color: 'var(--fg)', fontSize: 13, marginBottom: 8 }}
              />
              {driveError && <div style={{ fontSize: 12, color: 'var(--urg)', marginBottom: 8 }}>{driveError}</div>}
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-ghost" onClick={() => { setDriveOpen(false); setDriveError(null) }}>Cancelar</button>
                <button
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  disabled={!driveUrl.trim()}
                  onClick={handleDriveUrlSubmit}
                >
                  Confirmar arquivo
                </button>
              </div>
            </div>
          )}
          {csvHeaders.length > 0 && showClassificationModal && (
            <div style={{ marginTop: 16, padding: 16, background: 'var(--surface)', border: '1px solid var(--gb)', borderRadius: 'var(--rl)' }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>
                Qual o tipo de dados desta planilha?
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
                Detectamos {csvHeaders.length} colunas. Selecione o tipo que melhor descreve esta planilha.
              </div>
              {(showSchemaTypeRadios || !csvClassification?.schemaType) && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', cursor: 'pointer', fontSize: 13 }}>
                    <input type="radio" name="csvSchemaType" value="invoices" checked={(csvClassification?.schemaType ?? 'invoices') === 'invoices'} onChange={() => setCsvClassification({ confirmed: false, schemaType: 'invoices', canceled: false })} />
                    <span><strong>Notas Fiscais / Faturamento</strong> — invoices, NF-e, NFC-e, recibos de venda.</span>
                  </label>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', cursor: 'pointer', fontSize: 13 }}>
                    <input type="radio" name="csvSchemaType" value="fato_transacoes" checked={csvClassification?.schemaType === 'fato_transacoes'} onChange={() => setCsvClassification({ confirmed: false, schemaType: 'fato_transacoes', canceled: false })} />
                    <span><strong>Transacoes Financeiras</strong> — fato_transacoes, lancamentos, receitas, despesas.</span>
                  </label>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', cursor: 'pointer', fontSize: 13 }}>
                    <input type="radio" name="csvSchemaType" value="dim_clientes" checked={csvClassification?.schemaType === 'dim_clientes'} onChange={() => setCsvClassification({ confirmed: false, schemaType: 'dim_clientes', canceled: false })} />
                    <span><strong>Clientes</strong> — dim_clientes, cadastro de clientes.</span>
                  </label>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', cursor: 'pointer', fontSize: 13 }}>
                    <input type="radio" name="csvSchemaType" value="dim_inventory" checked={csvClassification?.schemaType === 'dim_inventory'} onChange={() => setCsvClassification({ confirmed: false, schemaType: 'dim_inventory', canceled: false })} />
                    <span><strong>Estoque / Produtos</strong> — dim_inventory, SKU, produtos, catalogo.</span>
                  </label>
                </div>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary" onClick={() => {
                  const schemaType = csvClassification?.schemaType || 'invoices'
                  setCsvUploaded(true)
                  setCsvClassification({ confirmed: true, schemaType, canceled: false })
                  setShowClassificationModal(false)
                  setShowSchemaTypeRadios(false)
                  const file = csvFileRef.current
                  if (file) onCsvFileReady(file, undefined, schemaType)
                }}>Confirmar</button>
                {!showSchemaTypeRadios && (
                  <button className="btn btn-ghost" onClick={() => setShowSchemaTypeRadios(true)}>Alterar tipo</button>
                )}
                <button className="btn btn-ghost" onClick={() => {
                  setCsvFileName('')
                  setCsvHeaders([])
                  setCsvUploaded(false)
                  setCsvClassification(null)
                  setShowClassificationModal(false)
                  csvFileRef.current = null
                  onCsvFileReady(null)
                }}>Cancelar</button>
              </div>
              {csvClassification && !csvClassification.confirmed && (
                <div className="field">
                  <label>schemaType:</label>
                  <select value={csvClassification.schemaType} onChange={e => {
                    setCsvClassification(prev => prev ? { ...prev, schemaType: e.target.value } : { confirmed: false, schemaType: e.target.value, canceled: false })
                    if (e.target.value !== '') {
                      setCsvUploaded(true)
                      setCsvClassification({ confirmed: true, schemaType: e.target.value, canceled: false })
                      setShowClassificationModal(false)
                      const file = csvFileRef.current
                      if (file) onCsvFileReady(file, undefined, e.target.value)
                    }
                  }}>
                    <option value="">Selecione…</option>
                    <option value="invoices">invoices</option>
                    <option value="receipts">receipts</option>
                    <option value="bank_statements">bank_statements</option>
                    <option value="outros">outros</option>
                    <option value="Nao sei">Nao sei (sugere via LLM)</option>
                  </select>
                </div>
              )}
            </div>
          )}
          <input
            ref={csvRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            style={{ display: 'none' }}
            onChange={handleCsvChange}
          />

          <div style={{ display: 'flex', gap: 8, marginTop: 22 }}>
            <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleNext}>Continuar → Mapear colunas</button>
          </div>
          <div style={{ textAlign: 'center', marginTop: 12, fontSize: 12, color: 'var(--muted)' }}>
            Prefere começar sem dados? <span style={{ color: 'var(--blue3)', cursor: 'pointer' }} onClick={onSkip}>Pular por agora →</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── StepMapping ──────────────────────────────────────────────────────────────

function StepMapping({
  onNext, onBack, saveDraft, mappingResult, credentialId, clientId, csvSourceId, onConfirmedMapping,
}: {
  onNext: () => void
  onBack?: () => void
  saveDraft: (patch: Partial<OnboardingDraft>) => Promise<void>
  mappingResult: ColumnMappingResult | null
  credentialId: number | null
  clientId: string | null
  csvSourceId: string | null
  onConfirmedMapping?: (mapping: Record<string, string>) => void
}) {
  const [openGroup, setOpenGroup] = useState<'auto' | 'warn' | 'unknown' | null>(() => {
    if ((mappingResult?.needs_review?.length ?? 0) > 0) return 'warn'
    if (Object.keys(mappingResult?.matched ?? {}).length > 0) return 'auto'
    return null
  })
  // Pre-populate warn selections with each row's top candidate so they're included
  // even if the user never opens the warn group.
  const [warnSelections, setWarnSelections] = useState<Record<string, string>>(() =>
    Object.fromEntries((mappingResult?.needs_review ?? []).map(r => [r.source, r.candidates[0]?.canonical ?? '']))
  )
  const [unknownSelections, setUnknownSelections] = useState<Record<string, string>>({})
  const [confirming, setConfirming] = useState(false)

  async function handleConfirm() {
    setConfirming(true)
    try {
      await saveDraft({ mapping_confirmed: true })

      // Fire ETL job — non-blocking, navigate immediately
      // Backend expects { source_column: canonical_field } — same as match-columns output
      // run_etl_job does: SELECT source_col AS canonical FROM fdw.table
      const autoMatched: Record<string, string> = { ...mappingResult?.matched ?? {} }
      // warnSelections state: { source_col: canonical } — already correct
      const warnMapped: Record<string, string> = {}
      for (const [src, canonical] of Object.entries(warnSelections)) {
        if (canonical && canonical !== 'ignorar') warnMapped[src] = canonical
      }
      // unknownSelections state: { source_col: canonical } — already correct
      const manualMapped = Object.fromEntries(
        Object.entries(unknownSelections)
          .filter(([, v]) => v && v !== 'ignorar')
      )
      const column_mapping = { ...autoMatched, ...warnMapped, ...manualMapped }

      // Post-launch (BQ/Drive): clientId is available → run ETL now.
      // Pre-launch (CSV): clientId is null → pass mapping upstream for StepLaunch to use.
      if (clientId) {
        if (csvSourceId) {
          supabase.functions
            .invoke('run-csv-etl', {
              body: { client_id: clientId, source_id: csvSourceId, column_mapping },
            })
            .then(({ error }) => {
              if (error) {
                console.error('[onboarding] run-csv-etl:', error)
                useAppStore.getState().addToast('no', 'Erro ao importar planilha', 'Os dados não foram carregados. Acesse Configurações > Fontes para tentar novamente.')
              }
            })
            .catch((e: unknown) => {
              console.error('[onboarding] run-csv-etl:', e)
              useAppStore.getState().addToast('no', 'Erro ao importar planilha', 'Os dados não foram carregados. Acesse Configurações > Fontes para tentar novamente.')
            })
        } else if (credentialId) {
          supabase.functions
            .invoke('run-sync-etl', {
              body: { client_id: clientId, credential_id: credentialId, column_mapping },
            })
            .then(({ error }) => {
              if (error) {
                console.error('[onboarding] run-sync-etl:', error)
                useAppStore.getState().addToast('no', 'Erro ao sincronizar dados', 'A sincronização falhou. Acesse Configurações > Fontes para tentar novamente.')
              }
            })
            .catch((e: unknown) => {
              console.error('[onboarding] run-sync-etl:', e)
              useAppStore.getState().addToast('no', 'Erro ao sincronizar dados', 'A sincronização falhou. Acesse Configurações > Fontes para tentar novamente.')
            })
        }
      } else {
        onConfirmedMapping?.(column_mapping)
      }

      onNext()
    } finally {
      setConfirming(false)
    }
  }

  const toggle = (g: 'auto' | 'warn' | 'unknown') => setOpenGroup(prev => prev === g ? null : g)

  // Derive rows from real mapping result, or fall back to empty state
  const autoRows = Object.entries(mappingResult?.matched ?? {}).map(([source, canonical]) => ({
    source_column: source,
    canonical_column: canonical as string,
    confidence: mappingResult?.confidence_scores?.[source] ?? 0,
    auto_matched: true,
  }))
  const warnRows = (mappingResult?.needs_review ?? [])
  const unknownCols = mappingResult?.unmatched ?? []

  const hasData = mappingResult !== null

  return (
    <div className="flow-page map-page on">
      <FlowTop step="mapping" onBack={onBack} />
      <div className="map-body">
        <div className="map-step">PASSO 4 DE 4</div>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-.03em', marginBottom: 7 }}>Confirmar mapeamento de colunas</div>
        <div style={{ fontSize: 14, color: 'var(--muted2)', marginBottom: 20 }}>
          {hasData
            ? 'Verificamos sua base e mapeamos automaticamente a maioria dos campos. Revise os que precisam de atenção.'
            : 'Nenhum arquivo conectado. Você pode confirmar e continuar, ou voltar para conectar uma fonte de dados.'}
        </div>
        <div className="map-summary">
          {hasData ? (
            <>
              <div className="ms-chip ms-ok">✓ {autoRows.length} mapeados</div>
              {warnRows.length > 0 && <div className="ms-chip ms-warn">⚠ {warnRows.length} {warnRows.length === 1 ? 'pendente' : 'pendentes'}</div>}
              {unknownCols.length > 0 && <div className="ms-chip ms-err">✗ {unknownCols.length} não reconhecido{unknownCols.length !== 1 ? 's' : ''}</div>}
            </>
          ) : (
            <div className="ms-chip" style={{ color: 'var(--mu)' }}>Sem dados para mapear</div>
          )}
          <div className="ms-sep" />
        </div>

        {hasData && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--gb)', borderRadius: 'var(--rl)', overflow: 'hidden', backdropFilter: 'blur(12px)' }}>
            <table className="map-table">
              <thead>
                <tr>
                  <th style={{ width: '22%' }}>Sua coluna</th>
                  <th style={{ width: '6%', textAlign: 'center' }}>→</th>
                  <th style={{ width: '24%' }}>Campo blu</th>
                  <th style={{ width: '16%' }}>Confiança</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {/* Auto group */}
                {autoRows.length > 0 && (
                  <tr className="map-group-hd" onClick={() => toggle('auto')}>
                    <td colSpan={6} className="map-section-hd">
                      <span className="mg-chevron" style={{ transform: openGroup === 'auto' ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                      <span>✅ Mapeados automaticamente</span>
                      <span className="mg-badge ok">{autoRows.length} campos</span>
                      <div className="map-section-line" />
                    </td>
                  </tr>
                )}
                {openGroup === 'auto' && autoRows.map(r => (
                  <tr key={r.source_column} className="map-row">
                    <td>{r.source_column}</td>
                    <td className="map-arrow">→</td>
                    <td className="map-target">{r.canonical_column}</td>
                    <td>
                      <div className="conf-bar">
                        <div className="cb-track"><div className="cb-fill cb-high" style={{ width: `${Math.round(r.confidence * 100)}%` }} /></div>
                        <span style={{ color: 'var(--ok)' }}>{Math.round(r.confidence * 100)}%</span>
                      </div>
                    </td>
                    <td className="map-status stat-ok">✓ Mapeado</td>
                    <td></td>
                  </tr>
                ))}

                {/* Warn group */}
                {warnRows.length > 0 && (
                  <tr className="map-group-hd" onClick={() => toggle('warn')}>
                    <td colSpan={6} className="map-section-hd">
                      <span className="mg-chevron" style={{ transform: openGroup === 'warn' ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                      <span>⚠ Precisam de confirmação</span>
                      <span className="mg-badge warn">{warnRows.length} campos</span>
                      <div className="map-section-line" />
                    </td>
                  </tr>
                )}
                {openGroup === 'warn' && warnRows.map(r => {
                  const pct = Math.round((mappingResult?.confidence_scores[r.source] ?? 0) * 100)
                  return (
                    <tr key={r.source} className="map-row">
                      <td>{r.source}</td>
                      <td className="map-arrow">→</td>
                      <td>
                        <select
                          className="map-select"
                          value={warnSelections[r.source] ?? r.candidates[0]?.canonical ?? ''}
                          onChange={e => setWarnSelections(p => ({ ...p, [r.source]: e.target.value }))}
                        >
                          <option value="">Selecionar campo…</option>
                          {r.candidates.map(c => <option key={c.canonical} value={c.canonical}>{c.canonical}</option>)}
                          <option value="ignorar">— Ignorar esta coluna</option>
                        </select>
                      </td>
                      <td>
                        <div className="conf-bar">
                          <div className="cb-track"><div className="cb-fill cb-mid" style={{ width: `${pct}%` }} /></div>
                          <span style={{ color: 'var(--warn)' }}>{pct}%</span>
                        </div>
                      </td>
                      <td className="map-status stat-warn">⚠ Confirmar</td>
                      <td></td>
                    </tr>
                  )
                })}

                {/* Unknown group */}
                {unknownCols.length > 0 && (
                  <tr className="map-group-hd" onClick={() => toggle('unknown')}>
                    <td colSpan={6} className="map-section-hd">
                      <span className="mg-chevron" style={{ transform: openGroup === 'unknown' ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                      <span>✗ Não reconhecido</span>
                      <span className="mg-badge err">{unknownCols.length} campo{unknownCols.length !== 1 ? 's' : ''}</span>
                      <div className="map-section-line" />
                    </td>
                  </tr>
                )}
                {openGroup === 'unknown' && unknownCols.map(col => {
                  const sel = unknownSelections[col] ?? ''
                  const isMapped = sel && sel !== 'ignorar'
                  const isIgnored = sel === 'ignorar'
                  return (
                    <tr key={col} className="map-row">
                      <td>{col}</td>
                      <td className="map-arrow" style={{ color: isMapped ? 'var(--ok)' : 'var(--urg)' }}>
                        {isMapped ? '→' : '✗'}
                      </td>
                      <td>
                        <select
                          className="map-select"
                          value={sel}
                          onChange={e => setUnknownSelections(p => ({ ...p, [col]: e.target.value }))}
                        >
                          <option value="">Mapear manualmente…</option>
                          {CANONICAL_FIELDS.map(f => <option key={f} value={f}>{f}</option>)}
                          <option value="ignorar">— Ignorar esta coluna</option>
                        </select>
                      </td>
                      <td>
                        <div className="conf-bar">
                          <div className="cb-track">
                            <div className="cb-fill" style={{ width: '0%', background: 'var(--urg)' }} />
                          </div>
                          <span style={{ color: 'var(--urg)' }}>—</span>
                        </div>
                      </td>
                      <td className="map-status" style={{ color: isMapped ? 'var(--ok)' : isIgnored ? 'var(--muted)' : 'var(--urg)' }}>
                        {isMapped ? '✓ Mapeado' : isIgnored ? '— Ignorado' : '✗ Desconhecido'}
                      </td>
                      <td></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, paddingBottom: 28 }}>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>
            Documentação do esquema — em breve
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {onBack && <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>}
            <button className="btn btn-primary" onClick={handleConfirm} disabled={confirming}>
              {confirming ? 'Confirmando…' : 'Confirmar mapeamento →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── StepLaunch ───────────────────────────────────────────────────────────────

function StepLaunch({ bootstrap, pendingCredentials, onDone, website, csvFile, csvSheetName, csvSchemaType, driveFileId, confirmedColumnMapping }: {
  bootstrap: () => Promise<{ client_id: string; agents: number; routines: number; prompts_seeded: number }>
  pendingCredentials: PendingCredential[]
  onDone: (mappingResult: ColumnMappingResult | null, credentialId: number | null, clientId: string, csvSourceId: string | null) => void
  website?: string
  csvFile?: File | null
  csvSheetName?: string
  csvSchemaType?: string
  driveFileId?: string | null
  confirmedColumnMapping?: Record<string, string>
}) {
  const [attempt, setAttempt] = useState(0)
  const [progress, setProgress] = useState(0)
  const [logs, setLogs] = useState<string[]>([])
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bqMappingResult, setBqMappingResult] = useState<ColumnMappingResult | null>(null)
  const [bqCredentialId, setBqCredentialId] = useState<number | null>(null)
  const [resolvedClientId, setResolvedClientId] = useState<string>('')
  const [csvSourceId, setCsvSourceId] = useState<string | null>(null)
  const rafRef = useRef<number>(0)
  const lastAttemptFired = useRef(-1)
  // Cancellation guard lives in a ref so it survives React StrictMode's
  // intentional double-mount in dev. Without this, the first mount's cleanup
  // flips a local `cancelledRef.current` to true, the re-mount short-circuits via
  // lastAttemptFired, and the in-flight bootstrap()/.then never runs — tela
  // fica presa em "Iniciando seu bureau".
  const cancelledRef = useRef(false)

  useEffect(() => {
    if (lastAttemptFired.current === attempt) {
      // Re-mount under StrictMode (or any re-run with same attempt): keep the
      // in-flight bootstrap alive — don't cancel it.
      cancelledRef.current = false
      return
    }
    lastAttemptFired.current = attempt
    cancelledRef.current = false
    setProgress(0)
    setLogs([])
    setDone(false)
    setError(null)

    const LOG_STEPS = [
      '▸ Configurando agentes…',
      '▸ Provisionando rotinas…',
      '▸ Importando dados…',
      '▸ Detectando padrões iniciais…',
    ]
    const timers: ReturnType<typeof setTimeout>[] = []
    LOG_STEPS.forEach((line, i) => {
      timers.push(setTimeout(() => {
        if (!cancelledRef.current) setLogs(prev => [...prev, line])
      }, (i + 1) * 900))
    })

    // Animate to 85% while RPC runs
    const totalMs = 5000
    const start = Date.now()
    const tick = () => {
      if (cancelledRef.current) return
      const pct = Math.min(85, ((Date.now() - start) / totalMs) * 85)
      setProgress(pct)
      if (pct < 85) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)

    bootstrap()
      .then(async (result) => {
        if (cancelledRef.current) return
        cancelAnimationFrame(rafRef.current)
        setResolvedClientId(result.client_id)

        if (website) {
          setLogs(prev => [...prev, '▸ Analisando site da empresa em segundo plano…'])
        }

        // Create credentials now that client_id exists.
        // For BigQuery: use the blocking variant that discovers columns via
        // discover-bigquery-columns (the same edge function used in blu_app).
        let bqColumns: string[] = []
        let discoveredCredentialId: number | null = null
        for (const pc of pendingCredentials) {
          try {
            if (pc.platform === 'bigquery') {
              const { columns, credentialId } = await createBigQueryCredentialWithDiscovery(
                result.client_id,
                pc.nomServico,
                pc.credentials as BigQueryCredentials,
              )
              bqColumns = columns
              discoveredCredentialId = credentialId
              if (!cancelledRef.current) setLogs(prev => [...prev, `▸ ${pc.nomServico} conectado — ${columns.length} colunas descobertas.`])
            } else {
              await createCredential(result.client_id, pc.platform, pc.nomServico, pc.credentials)
              if (!cancelledRef.current) setLogs(prev => [...prev, `▸ ${pc.nomServico} conectado.`])
            }
          } catch (e) {
            if (!cancelledRef.current) setLogs(prev => [...prev, `⚠ Falha ao conectar ${pc.nomServico}.`])
            console.warn('[onboarding] credential creation failed:', e)
          }
        }

        // Run match-columns on BQ columns if discovered (overwrites any CSV mapping)
        if (bqColumns.length > 0) {
          try {
            const bqMapping = await callMatchColumns(bqColumns)
            if (!cancelledRef.current && bqMapping) {
              setBqMappingResult(bqMapping)
              setBqCredentialId(discoveredCredentialId)
              setLogs(prev => [...prev, `▸ Mapeamento de colunas concluído.`])
            }
          } catch (e) {
            console.warn('[onboarding] match-columns failed:', e)
          }
        }

        // Upload CSV file if one was selected
        let uploadedSourceId: string | null = null
        if (csvFile && result.client_id) {
          setLogs(prev => [...prev, '▸ Enviando planilha…'])
          try {
            const form = new FormData()
            form.append('file', csvFile)
            form.append('client_id', result.client_id)
            form.append('schema_type', csvSchemaType || 'invoices')
            if (csvSheetName) form.append('sheet_name', csvSheetName)
            const { data: uploadData, error: uploadErr } = await supabase.functions.invoke('upload-csv-source', {
              body: form,
            })
            if (!uploadErr && uploadData?.source_id) {
              if (!cancelledRef.current) {
                uploadedSourceId = uploadData.source_id
                setCsvSourceId(uploadData.source_id)
                setLogs(prev => [...prev, `▸ Planilha carregada — ${uploadData.columns?.length ?? 0} colunas.`])
                // Fire ETL with the mapping confirmed in StepMapping (non-blocking)
                if (confirmedColumnMapping && Object.keys(confirmedColumnMapping).length > 0) {
                  supabase.functions.invoke('run-csv-etl', {
                    body: { client_id: result.client_id, source_id: uploadData.source_id, column_mapping: confirmedColumnMapping },
                  }).catch((e: unknown) => console.warn('[onboarding] run-csv-etl:', e))
                }
              }
            } else {
              if (!cancelledRef.current) setLogs(prev => [...prev, '⚠ Falha ao enviar planilha. Você pode reconectar depois.'])
            }
          } catch (e) {
            if (!cancelledRef.current) setLogs(prev => [...prev, '⚠ Falha ao enviar planilha. Você pode reconectar depois.'])
            console.warn('[onboarding] upload-csv-source:', e)
          }
        }

        // Import Google Drive file if one was linked in StepData (CSV takes precedence)
        if (driveFileId && result.client_id && !uploadedSourceId) {
          setLogs(prev => [...prev, '▸ Importando arquivo do Google Drive…'])
          try {
            // The Drive token capture via AuthContext fires before the profile exists,
            // so it fails silently. Re-attempt capture now that the profile is created.
            const { data: { session: currentSession } } = await supabase.auth.getSession()
            if (currentSession?.provider_refresh_token) {
              await supabase.functions.invoke('onboarding-capture-drive-token', {
                body: {
                  provider_refresh_token: currentSession.provider_refresh_token,
                  provider_token: currentSession.provider_token ?? '',
                  account_email: currentSession.user?.email ?? '',
                  scopes: [
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/calendar.readonly',
                  ],
                },
              })
            }
          } catch {
            // Ignore — token may already be stored, or no Google session available
          }
          try {
            const { data: driveData, error: driveErr } = await supabase.functions.invoke('upload-drive-source', {
              body: { client_id: result.client_id, drive_file_id: driveFileId, schema_type: csvSchemaType || 'invoices' },
            })
            if (!driveErr && driveData?.source_id) {
              if (!cancelledRef.current) {
                const driveMappingResult: ColumnMappingResult = {
                  matched: driveData.matched ?? {},
                  unmatched: driveData.unmatched ?? [],
                  needs_review: driveData.needs_review ?? [],
                  confidence_scores: driveData.confidence_scores ?? {},
                  details: driveData.details ?? [],
                }
                setCsvSourceId(driveData.source_id)
                setBqMappingResult(driveMappingResult)
                setLogs(prev => [...prev, `▸ Drive importado — ${driveData.columns?.length ?? 0} colunas.`])
              }
            } else {
              if (!cancelledRef.current) setLogs(prev => [...prev, '⚠ Falha ao importar do Drive. Você pode reconectar depois.'])
            }
          } catch (e) {
            if (!cancelledRef.current) setLogs(prev => [...prev, '⚠ Falha ao importar do Drive. Você pode reconectar depois.'])
            console.warn('[onboarding] upload-drive-source:', e)
          }
        }

        setProgress(100)
        setLogs(prev => [
          ...prev,
          `▸ ${result.agents} agente(s) provisionado(s).`,
          ...(website ? ['▸ Contexto do site será indexado em instantes.'] : []),
          '▸ Bureau pronto.',
        ])
        setDone(true)
      })
      .catch((e: Error) => {
        if (cancelledRef.current) return
        cancelAnimationFrame(rafRef.current)
        setError(e.message || 'Erro ao inicializar o bureau.')
      })

    return () => {
      cancelledRef.current = true
      cancelAnimationFrame(rafRef.current)
      timers.forEach(clearTimeout)
    }
  }, [attempt]) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="flow-page on">
        <FlowTop step="launch" />
        <div className="launch-body">
          <div className="launch-icon">❌</div>
          <div className="launch-h">Algo deu errado</div>
          <div className="launch-sub" style={{ maxWidth: 340 }}>{error}</div>
          <button
            className="btn btn-primary"
            style={{ marginTop: 24 }}
            onClick={() => setAttempt(a => a + 1)}
          >
            Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flow-page on">
      <FlowTop step="launch" />
      <div className="launch-body">
        <div className="launch-icon">{done ? '✅' : '🚀'}</div>
        <div className="launch-h">{done ? 'Bureau pronto!' : 'Iniciando seu bureau'}</div>
        <div className="launch-sub">
          {done ? 'Seus agentes estão prontos. Bem-vindo ao blu.' : 'Os agentes estão aprendendo sobre o seu negócio. Isso leva alguns segundos.'}
        </div>
        <div className="launch-progress">
          <div className="lp-bar" style={{ width: `${progress}%` }} />
        </div>
        <div className="launch-log">
          {logs.map((line, i) => (
            <div key={i} className="ll show">{line}</div>
          ))}
        </div>
        {done && (
          <button className="btn btn-primary btn-lg" style={{ marginTop: 28 }} onClick={() => onDone(bqMappingResult, bqCredentialId, resolvedClientId, csvSourceId)}>
            Entrar no blu →
          </button>
        )}
      </div>
    </div>
  )
}

// ─── OnboardingApp ────────────────────────────────────────────────────────────

export default function OnboardingApp() {
  const [step, setStep] = useState<Step>('auth')
  const [searchParams] = useSearchParams()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [mappingResult, setMappingResult] = useState<ColumnMappingResult | null>(null)
  const [confirmedColumnMapping, setConfirmedColumnMapping] = useState<Record<string, string> | null>(null)
  const [pendingCredentials, setPendingCredentials] = useState<PendingCredential[]>([])
  const [bqCredentialId, setBqCredentialId] = useState<number | null>(null)
  const [bqClientId, setBqClientId] = useState<string | null>(null)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [csvSheetName, setCsvSheetName] = useState<string>('')
  const [csvSchemaType, setCsvSchemaType] = useState<string>('invoices')
  const [csvSourceId, setCsvSourceId] = useState<string | null>(null)
  const [driveFileId, setDriveFileId] = useState<string | null>(null)

  const { draft, saveDraft, bootstrap } = useOnboardingDraft(user?.email ?? '')

  const mode = searchParams.get('mode') === 'login' ? 'login' : 'signup'

  // Pre-seed onboarding draft from Google user_metadata on OAuth return.
  // This avoids losing the user's name/email when the Google redirect happens.
  useEffect(() => {
    if (loading || !user) return
    const meta = (user.user_metadata ?? {}) as Record<string, unknown>
    const fullName = typeof meta.full_name === 'string'
      ? meta.full_name
      : typeof meta.name === 'string'
        ? meta.name
        : ''
    if (fullName || user.email) {
      const patch: Partial<OnboardingDraft> = {}
      if (fullName) patch.nome = fullName
      if (user.email) patch.email = user.email
      if (user.app_metadata?.provider === 'google') patch.authMethod = 'google'
      saveDraft(patch)
    }
    // intentionally ignore draft deps; runs only when user metadata changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, user?.email, (user?.user_metadata as Record<string, unknown> | undefined)?.full_name, (user?.user_metadata as Record<string, unknown> | undefined)?.name, (user?.app_metadata as Record<string, unknown> | undefined)?.provider, loading, saveDraft])

  // When user is authenticated at the auth step, route based on profile state.
  // Handles: (a) existing session on /onboarding?mode=login, (b) return from Google OAuth.
  // Uses centralized RPC is_onboarded_client() (multi-signal check).
  const clientIdChecked = useRef(false)
  useEffect(() => {
    if (loading || !user || step !== 'auth') return
    // Guard against multiple firings from repeated auth state events (OAuth emits several)
    if (clientIdChecked.current) return
    clientIdChecked.current = true
    let cancelled = false

    // Use the centralized RPC that checks multiple "is this a real client" signals
    supabase.rpc('is_onboarded_client').then(
      ({ data: onboarded }) => {
        if (cancelled) return

        if (onboarded) {
          // Client is onboarded by any signal — go to app
          navigate('/app', { replace: true })
        } else if (localStorage.getItem('onboarding_returning_to_data') === '1') {
          // User came back from Drive OAuth during the data step — restore it.
          localStorage.removeItem('onboarding_returning_to_data')
          if (!cancelled) setStep('data')
        } else {
          // New or provisional client — ensure tenant row and show onboarding
          supabase.rpc('get_my_client_id').then(
            ({ data: clientId }) => {
              if (cancelled) return
              if (!clientId) {
                supabase.rpc('ensure_tenant_row').then(() => {}, () => {})
              }
              if (!cancelled) setStep('info')
            },
            () => { if (!cancelled) setStep('info') }
          )
        }
      },
      () => {
        // RPC failed gracefully — fall back to original behavior
        supabase.rpc('get_my_client_id').then(
          async ({ data: clientId }) => {
            if (cancelled) return
            if (clientId) {
              const { data: row } = await supabase
                .from('clientes_blu')
                .select('onboarding_completed_at')
                .eq('client_id', clientId)
                .maybeSingle()
              if (row?.onboarding_completed_at) {
                navigate('/app', { replace: true })
              } else if (!cancelled) {
                setStep('info')
              }
            } else {
              try { await supabase.rpc('ensure_tenant_row') } catch { /* best-effort */ }
              if (!cancelled) setStep('info')
            }
          },
          () => { if (!cancelled) setStep('info') }
        )
      }
    )

    return () => { cancelled = true }
  }, [user?.id, loading, step, navigate])

  const go = useCallback((s: Step) => setStep(s), [])

  if (loading) return null

  // Map internal codes back to display strings for initializing StepInfo (empty = no pre-selection)
  const initialVertical = VERTICAL_DISPLAY[draft.vertical ?? ''] ?? ''
  const initialPorte = PORTE_DISPLAY[draft.porte] ?? ''

  if (step === 'auth') {
    return (
      <StepAuth
        onNext={() => go('info')}
        mode={mode}
      />
    )
  }
  if (step === 'info') {
    return (
      <StepInfo
        onNext={() => go('data')}
        // Suppress back button when user is already authenticated to avoid auth→info redirect loop
        onBack={user ? undefined : () => go('auth')}
        saveDraft={saveDraft}
        initialNome={draft.nome}
        initialEmpresa={draft.empresa}
        initialCnpj={draft.cnpj ?? ''}
        initialTelefone={''}
        initialWebsite={draft.website}
        initialVertical={initialVertical}
        initialPorte={initialPorte}
        initialProdutoServico={draft.produtoServico ?? ''}
      />
    )
  }
  if (step === 'data') {
    return (
      <StepData
        // CSV: go to mapping first (pre-launch). Drive/BQ/no-data: go straight to launch.
        onNext={(result) => result ? go('mapping') : go('launch')}
        onBack={() => go('info')}
        onSkip={() => go('launch')}
        saveDraft={saveDraft}
        onMappingReady={setMappingResult}
        onCsvFileReady={(file, sheetName, schemaType) => {
          setCsvFile(file)
          setCsvSheetName(sheetName ?? '')
          if (schemaType) setCsvSchemaType(schemaType)
        }}
        onDriveFileReady={(fileId) => setDriveFileId(fileId)}
        onCredentialCollected={(platform, nomServico, credentials) =>
          setPendingCredentials(prev => [
            ...prev.filter(c => c.platform !== platform),
            { platform, nomServico, credentials },
          ])
        }
      />
    )
  }
  if (step === 'mapping') {
    return (
      <StepMapping
        // Pre-launch (CSV): go to launch after confirm. Post-launch (BQ/Drive): go to /app.
        onNext={() => bqClientId ? navigate('/app', { replace: true }) : go('launch')}
        // Pre-launch: back to data. Post-launch: no back (bootstrap already ran).
        onBack={bqClientId ? undefined : () => go('data')}
        onConfirmedMapping={setConfirmedColumnMapping}
        saveDraft={saveDraft}
        mappingResult={mappingResult}
        credentialId={bqCredentialId}
        clientId={bqClientId}
        csvSourceId={csvSourceId}
      />
    )
  }
  return (
    <StepLaunch
      bootstrap={bootstrap}
      pendingCredentials={pendingCredentials}
      website={draft.website || undefined}
      csvFile={csvFile}
      csvSheetName={csvSheetName}
      csvSchemaType={csvSchemaType}
      driveFileId={driveFileId}
      confirmedColumnMapping={confirmedColumnMapping ?? undefined}
      onDone={(bqMapping, credentialId, clientId, uploadedCsvSourceId) => {
        try { localStorage.removeItem('blu_first_run_done') } catch {}
        useAppStore.setState({ firstRun: true })
        setBqCredentialId(credentialId)
        setBqClientId(clientId)
        if (uploadedCsvSourceId) setCsvSourceId(uploadedCsvSourceId)
        // Show post-launch mapping only for BQ/Drive (columns discovered during launch).
        // CSV was already mapped pre-launch.
        if (bqMapping) {
          setMappingResult(bqMapping)
          go('mapping')
        } else {
          navigate('/app', { replace: true })
        }
      }}
    />
  )
}
