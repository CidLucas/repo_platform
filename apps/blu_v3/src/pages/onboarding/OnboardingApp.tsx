import React, { useState, useEffect, useRef, useCallback } from 'react'
import * as XLSX from 'xlsx'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth, supabase } from '@blu/auth'
import { useOnboardingDraft, VERTICAL_MAP, PORTE_MAP, type OnboardingDraft } from '../../hooks/useOnboardingDraft'
import { createCredential, createBigQueryCredentialWithDiscovery, type ConnectorPlatform, type CredentialPayload, type BigQueryCredentials } from '../../api/connectors'

interface PendingCredential {
  platform: ConnectorPlatform
  nomServico: string
  credentials: CredentialPayload
}

type Step = 'auth' | 'info' | 'data' | 'mapping' | 'launch'

const STEP_ORDER: Step[] = ['auth', 'info', 'data', 'mapping', 'launch']
const STEP_LABELS = ['Conta', 'Empresa', 'Dados', 'Mapeamento']

const VERTICALS = ['Comércio', 'Serviços', 'Indústria', 'Saúde', 'Educação', 'Agronegócio', 'Financeiro', 'Outro']
const TEAM_SIZES = ['Só eu', '2–10 pessoas', '10–50 pessoas', '50+ pessoas']

const PRIMARY_FOCUS = [
  { id: 'vendas',      label: 'Vendas' },
  { id: 'operacao',   label: 'Operação' },
  { id: 'atendimento', label: 'Atendimento' },
  { id: 'estoque',    label: 'Estoque' },
  { id: 'outro',      label: 'Outro' },
]

// Canonical field names for manual mapping in StepMapping unknown column dropdown
const CANONICAL_FIELDS = [
  'date', 'customer_name', 'customer_id', 'product_name', 'product_id',
  'sku', 'quantity', 'unit_price', 'total_amount', 'discount',
  'invoice_number', 'supplier_name', 'supplier_id', 'category',
  'payment_method', 'status', 'notes', 'city', 'state', 'country',
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
  { id: 'bigquery', icon: '📊', name: 'BigQuery', sub: 'Data warehouse', connector: 'bigquery' },
  { id: 'shopify', icon: '🛍', name: 'Shopify', sub: 'E-commerce', connector: 'shopify', comingSoon: true },
  { id: 'vtex', icon: '🔷', name: 'VTEX', sub: 'E-commerce', connector: 'vtex', comingSoon: true },
  { id: 'postgresql', icon: '🐘', name: 'PostgreSQL', sub: 'Banco de dados', connector: 'postgresql', comingSoon: true },
  { id: 'conta_azul', icon: '📋', name: 'Conta Azul', sub: 'ERP / NF-e', connector: 'conta_azul', comingSoon: true },
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

async function callMatchColumns(sourceColumns: string[]): Promise<ColumnMappingResult | null> {
  if (sourceColumns.length === 0) return null
  try {
    const { data, error } = await supabase.functions.invoke('match-columns', {
      body: { source_columns: sourceColumns, schema_type: 'invoices' },
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

function parseSpreadsheetHeaders(file: File): Promise<string[]> {
  const isXlsx = /\.(xlsx|xls)$/i.test(file.name)

  if (isXlsx) {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target?.result as ArrayBuffer)
          const wb = XLSX.read(data, { type: 'array', sheetRows: 1 })
          const ws = wb.Sheets[wb.SheetNames[0]]
          const rows = XLSX.utils.sheet_to_json<string[]>(ws, { header: 1, defval: '' })
          const headers = (rows[0] ?? []).map((h: unknown) => String(h).trim()).filter(Boolean)
          resolve(headers)
        } catch {
          resolve([])
        }
      }
      reader.onerror = () => resolve([])
      reader.readAsArrayBuffer(file)
    })
  }

  // CSV — detect delimiter (semicolon or comma) and strip quotes
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string ?? ''
      const firstLine = text.split(/\r?\n/)[0] ?? ''
      const delim = firstLine.includes(';') ? ';' : ','
      const headers = firstLine.split(delim).map(h => h.replace(/^"|"$/g, '').trim()).filter(Boolean)
      resolve(headers)
    }
    reader.onerror = () => resolve([])
    reader.readAsText(file)
  })
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
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            />
          </div>

          {error && (
            <div style={{ fontSize: 12.5, color: 'var(--urg)', marginBottom: 4 }}>{error}</div>
          )}

          <button
            className="btn btn-blue"
            style={{ width: '100%' }}
            onClick={handleSubmit}
            disabled={submitting || !email || !password}
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
              <a href="#" style={{ color: 'var(--blue3)' }}>Termos de Uso</a> e a{' '}
              <a href="#" style={{ color: 'var(--blue3)' }}>Política de Privacidade</a>.
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
  vertical?: string
  confidence: number
  suggested_agents?: string[]
}

function StepInfo({
  onNext, onBack, saveDraft,
  initialNome, initialEmpresa, initialWebsite, initialVertical, initialPorte,
  initialPrimaryFocus, initialProdutoServico,
}: {
  onNext: () => void
  onBack: () => void
  saveDraft: (patch: Partial<OnboardingDraft>) => Promise<void>
  initialNome: string
  initialEmpresa: string
  initialWebsite: string
  initialVertical: string
  initialPorte: string
  initialPrimaryFocus: string
  initialProdutoServico: string
}) {
  const [nome, setNome] = useState(initialNome)
  const [empresa, setEmpresa] = useState(initialEmpresa)
  const [website, setWebsite] = useState(initialWebsite)
  const [vertical, setVertical] = useState(initialVertical || 'Comércio')
  const [teamSize, setTeamSize] = useState(initialPorte || 'Só eu')
  const [primaryFocus, setPrimaryFocus] = useState(initialPrimaryFocus || '')
  const [produtoServico, setProdutoServico] = useState(initialProdutoServico || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [detecting, setDetecting] = useState(false)
  const [siteContext, setSiteContext] = useState<SiteContext | null>(null)

  async function handleWebsiteBlur() {
    const url = website.trim()
    if (!url) return
    setDetecting(true)
    setSiteContext(null)
    try {
      const { data, error } = await supabase.functions.invoke('onboarding-website-intel', {
        body: { website_url: url },
      })
      if (error || !data) return
      const ctx = data as SiteContext
      // Auto-fill vertical and company name if confidence is high enough
      const detected = VERTICAL_DISPLAY[ctx.vertical as string]
      if (detected && ctx.confidence >= 0.5) {
        setVertical(detected)
        if (ctx.company_name && !empresa.trim()) setEmpresa(ctx.company_name)
      }
      // Show context card for any confidence level to let user confirm/adjust
      if (ctx.vertical || ctx.company_name) setSiteContext(ctx)
    } catch {
      // best-effort, silent
    } finally {
      setDetecting(false)
    }
  }

  async function handleNext() {
    if (!empresa.trim()) { setError('Nome da empresa é obrigatório.'); return }
    setSaving(true)
    setError(null)
    try {
      await saveDraft({
        nome: nome.trim(),
        empresa: empresa.trim(),
        website: website.trim(),
        vertical: VERTICAL_MAP[vertical] ?? null,
        porte: PORTE_MAP[teamSize] ?? teamSize,
        primaryFocus: (primaryFocus as OnboardingDraft['primaryFocus']) || null,
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
          <div className="fc-h">Sobre a sua empresa</div>
          <div className="fc-sub">O blu usa estas informações para calibrar os agentes ao seu negócio.</div>
          <div className="row2">
            <div className="field">
              <label>Seu nome</label>
              <input type="text" placeholder="Carlos Lima" value={nome} onChange={e => setNome(e.target.value)} />
            </div>
            <div className="field">
              <label>Nome da empresa *</label>
              <input type="text" placeholder="Distribuidora Alvo" value={empresa} onChange={e => setEmpresa(e.target.value)} />
            </div>
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
            {detecting && <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>Analisando site…</div>}
          </div>

          {/* Context card: shown after website-intel returns results */}
          {siteContext && (
            <div style={{
              margin: '4px 0 8px',
              padding: '12px 14px',
              background: 'var(--blue-tint, rgba(59,130,246,.06))',
              border: '1px solid rgba(59,130,246,.18)',
              borderRadius: 'var(--rl)',
            }}>
              <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--blue3)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                ✦ Encontramos algumas informações sobre sua empresa
                <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--muted)', background: 'var(--surface2)', padding: '1px 6px', borderRadius: 10 }}>
                  {Math.round(siteContext.confidence * 100)}% de confiança
                </span>
              </div>
              {siteContext.company_name && (
                <div style={{ fontSize: 12.5, color: 'var(--muted2)', marginBottom: 4 }}>
                  Empresa detectada: <strong style={{ color: 'var(--fg)' }}>{siteContext.company_name}</strong>
                </div>
              )}
              {siteContext.vertical && (
                <div style={{ fontSize: 12.5, color: 'var(--muted2)', marginBottom: 10 }}>
                  Setor sugerido: <strong style={{ color: 'var(--fg)' }}>{VERTICAL_DISPLAY[siteContext.vertical] ?? siteContext.vertical}</strong>
                  <span style={{ marginLeft: 6, color: 'var(--muted)', fontSize: 11.5 }}>— confirme abaixo se correto</span>
                </div>
              )}
              {/* Contextual questions — these seed the mind map via the context-gatherer post-launch */}
              <div style={{ borderTop: '1px solid rgba(59,130,246,.12)', paddingTop: 10, marginTop: 2 }}>
                <div style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 8 }}>
                  Duas perguntas rápidas para contextualizar seus agentes:
                </div>
                <div className="field" style={{ marginBottom: 10 }}>
                  <label style={{ fontSize: 12 }}>Qual é o principal produto ou serviço que você oferece?</label>
                  <input
                    type="text"
                    placeholder="ex: Software de gestão, Móveis planejados, Consultoria financeira"
                    value={produtoServico}
                    onChange={e => setProdutoServico(e.target.value)}
                    style={{ marginTop: 4 }}
                  />
                </div>
                <div className="field" style={{ marginBottom: 0 }}>
                  <label style={{ fontSize: 12 }}>Foco atual do negócio</label>
                  <div className="radio-pills" style={{ marginTop: 4 }}>
                    {PRIMARY_FOCUS.map(f => (
                      <div
                        key={f.id}
                        className={`rp${primaryFocus === f.id ? ' on' : ''}`}
                        onClick={() => setPrimaryFocus(f.id)}
                      >
                        {f.label}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="field">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              Setor *
              {siteContext && siteContext.confidence >= 0.5 && (
                <span style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--blue3)', background: 'var(--blue-tint, rgba(59,130,246,.1))', padding: '1px 7px', borderRadius: 20 }}>
                  detectado automaticamente
                </span>
              )}
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
            <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>
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
  onNext, onBack, onSkip, saveDraft, onMappingReady, onCredentialCollected,
}: {
  onNext: () => void
  onBack: () => void
  onSkip: () => void
  saveDraft: (patch: Partial<OnboardingDraft>) => Promise<void>
  onMappingReady: (result: ColumnMappingResult | null) => void
  onCredentialCollected: (platform: ConnectorPlatform, nomServico: string, credentials: CredentialPayload) => void
}) {
  const [connected, setConnected] = useState<Record<string, boolean>>({})
  const [interested, setInterested] = useState<Record<string, boolean>>({})
  const [openForm, setOpenForm] = useState<string | null>(null)
  const [csvUploaded, setCsvUploaded] = useState(false)
  const [csvHeaders, setCsvHeaders] = useState<string[]>([])
  const [csvFileName, setCsvFileName] = useState<string>('')
  const csvRef = useRef<HTMLInputElement>(null)

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
    setCsvUploaded(true)
    setCsvFileName(file.name)
    const headers = await parseSpreadsheetHeaders(file)
    setCsvHeaders(headers)
  }

  async function handleNext() {
    const systems = [
      ...Object.keys(connected).filter(k => connected[k]),
      ...Object.keys(interested).filter(k => interested[k]),
    ]
    await saveDraft({ systems, csvUploaded })
    // Match CSV columns if uploaded; BQ columns are discovered in StepLaunch
    const mappingResult = csvHeaders.length > 0 ? await callMatchColumns(csvHeaders) : null
    onMappingReady(mappingResult)
    onNext()
  }

  const selectedSystem = SYSTEMS.find(s => s.id === openForm)

  return (
    <div className="flow-page on">
      <FlowTop step="data" onBack={onBack} />
      <div className="flow-body">
        <div className="flow-card" style={{ maxWidth: 600 }}>
          <div className="fc-h">Conecte seus dados</div>
          <div className="fc-sub">O blu aprende sobre seu negócio a partir dos seus dados. Escolha de onde vêm.</div>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 10 }}>Sistemas</div>
          <div className="dsrc-grid">
            {SYSTEMS.map(s => (
              <div
                key={s.id}
                className={`dsrc${connected[s.id] ? ' connected' : ''}${openForm === s.id ? ' active' : ''}`}
                onClick={() => handleTileClick(s)}
                style={{ position: 'relative', cursor: connected[s.id] ? 'default' : 'pointer' }}
              >
                {s.comingSoon && (
                  <div style={{ position: 'absolute', top: 6, right: 6, fontSize: 9, fontWeight: 700, background: 'var(--surface2)', color: 'var(--muted)', padding: '2px 5px', borderRadius: 4 }}>
                    EM BREVE
                  </div>
                )}
                <span className="dsrc-icon">{s.icon}</span>
                <div className="dsrc-name">{s.name}</div>
                <div className="dsrc-sub">
                  {connected[s.id]
                    ? '✓ Conectado'
                    : interested[s.id]
                    ? '✓ Interesse registrado'
                    : s.sub}
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
            <div className="dsrc" style={{ position: 'relative', cursor: 'default', opacity: 0.7 }}>
              <div style={{ position: 'absolute', top: 6, right: 6, fontSize: 9, fontWeight: 700, background: 'var(--surface2)', color: 'var(--muted)', padding: '2px 5px', borderRadius: 4 }}>
                EM BREVE
              </div>
              <span className="dsrc-icon">🗂</span>
              <div className="dsrc-name">Google Drive</div>
              <div className="dsrc-sub">Sheets · Docs</div>
            </div>
          </div>
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
  onNext, onBack, saveDraft, mappingResult, credentialId, clientId,
}: {
  onNext: () => void
  onBack: () => void
  saveDraft: (patch: Partial<OnboardingDraft>) => Promise<void>
  mappingResult: ColumnMappingResult | null
  credentialId: number | null
  clientId: string | null
}) {
  const [openGroup, setOpenGroup] = useState<'auto' | 'warn' | 'unknown' | null>(null)
  const [warnSelections, setWarnSelections] = useState<Record<string, string>>({})
  const [unknownSelections, setUnknownSelections] = useState<Record<string, string>>({})
  const [flagged, setFlagged] = useState<Record<string, boolean>>({})
  const [confirming, setConfirming] = useState(false)

  async function handleConfirm() {
    setConfirming(true)
    try {
      await saveDraft({ mapping_confirmed: true })

      // Fire ETL job — non-blocking, navigate immediately
      if (clientId && credentialId) {
        const autoMatched: Record<string, string> = {}
        for (const d of (mappingResult?.details ?? [])) {
          if (d.auto_matched && d.canonical_column) autoMatched[d.source_column] = d.canonical_column
        }
        // Merge: auto → warn selections → manual unknown selections (skip 'ignorar')
        const manualMapped = Object.fromEntries(
          Object.entries(unknownSelections).filter(([, v]) => v && v !== 'ignorar')
        )
        const column_mapping = { ...autoMatched, ...warnSelections, ...manualMapped }
        supabase.functions
          .invoke('run-sync-etl', {
            body: { client_id: clientId, credential_id: credentialId, column_mapping },
          })
          .catch((e: unknown) => console.warn('[onboarding] run-sync-etl:', e))
      }

      onNext()
    } finally {
      setConfirming(false)
    }
  }

  const toggle = (g: 'auto' | 'warn' | 'unknown') => setOpenGroup(prev => prev === g ? null : g)

  // Derive rows from real mapping result, or fall back to empty state
  const autoRows = (mappingResult?.details ?? []).filter(d => d.auto_matched)
  const warnRows = (mappingResult?.needs_review ?? [])
  const unknownCols = mappingResult?.unmatched ?? []

  const hasData = mappingResult !== null

  return (
    <div className="flow-page map-page on">
      <FlowTop step="mapping" onBack={onBack} />
      <div className="map-body">
        <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-.03em', marginBottom: 5 }}>Revisão de mapeamento</div>
        <div style={{ fontSize: 14, color: 'var(--muted2)', marginBottom: 20 }}>
          {hasData
            ? 'O blu mapeou automaticamente as colunas do seu arquivo para o esquema interno. Revise, corrija ou sinalize qualquer erro.'
            : 'Nenhum arquivo conectado. Você pode confirmar e continuar, ou voltar para conectar uma fonte de dados.'}
        </div>
        <div className="map-summary">
          {hasData ? (
            <>
              <div className="ms-chip ms-ok">✓ {autoRows.length} mapeados automaticamente</div>
              {warnRows.length > 0 && <div className="ms-chip ms-warn">⚠ {warnRows.length} precisam de confirmação</div>}
              {unknownCols.length > 0 && <div className="ms-chip ms-err">✗ {unknownCols.length} não reconhecido{unknownCols.length !== 1 ? 's' : ''}</div>}
            </>
          ) : (
            <div className="ms-chip" style={{ color: 'var(--mu)' }}>Sem dados para mapear</div>
          )}
          <div className="ms-sep" />
          <button className="btn btn-primary ms-cta" onClick={handleConfirm} disabled={confirming}>
            {confirming ? 'Confirmando…' : 'Confirmar e continuar →'}
          </button>
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
                      <td>
                        {!isMapped && !isIgnored && (
                          <button
                            className={`map-flag${flagged[col] ? ' flagged' : ''}`}
                            onClick={() => setFlagged(p => ({ ...p, [col]: !p[col] }))}
                          >
                            {flagged[col] ? 'Sinalizado' : 'Sinalizar erro'}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, paddingBottom: 28 }}>
          <div style={{ fontSize: 13, color: 'var(--muted2)' }}>
            Dúvida em alguma coluna? <span style={{ color: 'var(--blue3)', cursor: 'pointer' }}>Ver documentação do esquema blu →</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>
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

function StepLaunch({ bootstrap, pendingCredentials, onDone, website }: {
  bootstrap: () => Promise<{ client_id: string; agents: number; routines: number; prompts_seeded: number }>
  pendingCredentials: PendingCredential[]
  onDone: (mappingResult: ColumnMappingResult | null, credentialId: number | null, clientId: string) => void
  website?: string
}) {
  const [attempt, setAttempt] = useState(0)
  const [progress, setProgress] = useState(0)
  const [logs, setLogs] = useState<string[]>([])
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bqMappingResult, setBqMappingResult] = useState<ColumnMappingResult | null>(null)
  const [bqCredentialId, setBqCredentialId] = useState<number | null>(null)
  const [resolvedClientId, setResolvedClientId] = useState<string>('')
  const rafRef = useRef<number>(0)

  useEffect(() => {
    let cancelled = false
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
        if (!cancelled) setLogs(prev => [...prev, line])
      }, (i + 1) * 900))
    })

    // Animate to 85% while RPC runs
    const totalMs = 5000
    const start = Date.now()
    const tick = () => {
      if (cancelled) return
      const pct = Math.min(85, ((Date.now() - start) / totalMs) * 85)
      setProgress(pct)
      if (pct < 85) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)

    bootstrap()
      .then(async (result) => {
        if (cancelled) return
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
              if (!cancelled) setLogs(prev => [...prev, `▸ ${pc.nomServico} conectado — ${columns.length} colunas descobertas.`])
            } else {
              await createCredential(result.client_id, pc.platform, pc.nomServico, pc.credentials)
              if (!cancelled) setLogs(prev => [...prev, `▸ ${pc.nomServico} conectado.`])
            }
          } catch (e) {
            if (!cancelled) setLogs(prev => [...prev, `⚠ Falha ao conectar ${pc.nomServico}.`])
            console.warn('[onboarding] credential creation failed:', e)
          }
        }

        // Run match-columns on BQ columns if discovered (overwrites any CSV mapping)
        if (bqColumns.length > 0) {
          try {
            const bqMapping = await callMatchColumns(bqColumns)
            if (!cancelled && bqMapping) {
              setBqMappingResult(bqMapping)
              setBqCredentialId(discoveredCredentialId)
              setLogs(prev => [...prev, `▸ Mapeamento de colunas concluído.`])
            }
          } catch (e) {
            console.warn('[onboarding] match-columns failed:', e)
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
        if (cancelled) return
        cancelAnimationFrame(rafRef.current)
        setError(e.message || 'Erro ao inicializar o bureau.')
      })

    return () => {
      cancelled = true
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
          <button className="btn btn-primary btn-lg" style={{ marginTop: 28 }} onClick={() => onDone(bqMappingResult, bqCredentialId, resolvedClientId)}>
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
  const [pendingCredentials, setPendingCredentials] = useState<PendingCredential[]>([])
  const [bqCredentialId, setBqCredentialId] = useState<number | null>(null)
  const [bqClientId, setBqClientId] = useState<string | null>(null)

  const { draft, saveDraft, bootstrap } = useOnboardingDraft(user?.email ?? '')

  const mode = searchParams.get('mode') === 'login' ? 'login' : 'signup'

  // When user is authenticated at the auth step, route based on profile state.
  // Handles: (a) existing session on /onboarding?mode=login, (b) return from Google OAuth.
  const clientIdChecked = useRef(false)
  useEffect(() => {
    if (loading || !user || step !== 'auth') return
    // Guard against multiple firings from repeated auth state events (OAuth emits several)
    if (clientIdChecked.current) return
    clientIdChecked.current = true
    let cancelled = false
    supabase.rpc('get_my_client_id').then(
      ({ data }) => {
        if (cancelled) return
        if (data) {
          navigate('/app', { replace: true })
        } else {
          // No client profile yet — continue through onboarding (info step)
          setStep('info')
        }
      },
      () => {
        if (!cancelled) setStep('info')
      },
    )
    return () => { cancelled = true }
  }, [user?.id, loading, step, navigate])

  const go = useCallback((s: Step) => setStep(s), [])

  if (loading) return null

  // Map internal codes back to display strings for initializing StepInfo
  const initialVertical = VERTICAL_DISPLAY[draft.vertical ?? ''] ?? 'Comércio'
  const initialPorte = PORTE_DISPLAY[draft.porte] ?? 'Só eu'

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
        onBack={() => go('auth')}
        saveDraft={saveDraft}
        initialNome={draft.nome}
        initialEmpresa={draft.empresa}
        initialWebsite={draft.website}
        initialVertical={initialVertical}
        initialPorte={initialPorte}
        initialPrimaryFocus={draft.primaryFocus ?? ''}
        initialProdutoServico={draft.produtoServico ?? ''}
      />
    )
  }
  if (step === 'data') {
    return (
      <StepData
        onNext={() => go('launch')}
        onBack={() => go('info')}
        onSkip={() => go('launch')}
        saveDraft={saveDraft}
        onMappingReady={setMappingResult}
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
        onNext={() => navigate('/app', { replace: true })}
        onBack={() => go('launch')}
        saveDraft={saveDraft}
        mappingResult={mappingResult}
        credentialId={bqCredentialId}
        clientId={bqClientId}
      />
    )
  }
  return (
    <StepLaunch
      bootstrap={bootstrap}
      pendingCredentials={pendingCredentials}
      website={draft.website || undefined}
      onDone={(bqMapping, credentialId, clientId) => {
        // BQ mapping (if discovered) takes priority over CSV mapping
        const finalMapping = bqMapping ?? mappingResult
        setBqCredentialId(credentialId)
        setBqClientId(clientId)
        if (finalMapping) {
          setMappingResult(finalMapping)
          go('mapping')
        } else {
          navigate('/app', { replace: true })
        }
      }}
    />
  )
}
