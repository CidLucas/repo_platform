import { useState } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchApprovalsByAgent,
  approveRequest,
  rejectRequest,
  snoozeApproval,
  createPaymentApproval,
} from '../../api/approvals'
import { fetchInsights, formatKpi } from '../../api/insights'
import { fetchConnectedAccounts, fetchPolpAccounts, fetchPolpTransactions, fetchPolpBills, type PolpBill, type PolpTransaction } from '../../api/financeiro'
import { useTxCategories, useSaveTxCategory } from '../../hooks/usePreferences'
import { getFinanceIndicators, getContextMetrics, type ContextMetricRow } from '../../api/analytics'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import RoutineConfigSection from '../../components/shared/RoutineConfigSection'

import RoutineExecutionFeed from '../../components/shared/RoutineExecutionFeed'
import DecisionCard from '../../components/shared/DecisionCard'
import EmptyState from '../../components/shared/EmptyState'
import LoadingState from '../../components/shared/LoadingState'
import { snoozeUntil } from '../../utils/time'
import { formatBRL } from '../../utils/formatters'

type Tab = 'decisoes' | 'compromissos' | 'tarefas' | 'historico' | 'config'


function fmtCompact(value: number | null): string {
  if (value === null) return '—'
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `R$ ${(value / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `R$ ${(value / 1_000).toFixed(0)}K`
  return formatBRL(value)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

const BANK_ICONS: Record<string, string> = {
  '260': '🟣', '104': '🏛', '033': '🔴', '341': '🟠',
  '001': '🟡', '077': '🟠', '237': '🔵', '323': '💙', '336': '🟢',
}
const SERVICE_ICONS: [RegExp, string][] = [
  [/netflix/i, '🎬'], [/spotify/i, '🎵'], [/uber/i, '🚗'],
  [/ifood|iFood/i, '🍕'], [/amazon/i, '📦'], [/apple/i, '🍎'],
  [/google/i, '🔵'], [/microsoft/i, '🪟'], [/rappi/i, '🛵'],
  [/99\s*(pop|taxi)/i, '🚕'], [/nubank/i, '🟣'], [/inter\b/i, '🟠'],
  [/ita[uú]/i, '🟠'], [/bradesco/i, '🔵'], [/santander/i, '🔴'],
  [/mercado\s*pago/i, '💙'], [/caixa/i, '🏛'], [/banco\s*do\s*brasil|bb\b/i, '🟡'],
]
const MCC_ICONS: Record<string, string> = {
  '5812': '🍽', '5814': '🍔', '5411': '🛒', '5912': '💊',
  '4121': '🚗', '4511': '✈', '7011': '🏨', '5732': '💻',
  '7372': '💻', '4814': '📱', '7991': '🎭', '8099': '🏥',
}
const CATEGORY_ICON_MAP: Record<string, string> = {
  // Material Icon name → emoji
  'restaurant': '🍽', 'fastfood': '🍔', 'local_dining': '🍽',
  'shopping_cart': '🛒', 'local_grocery_store': '🛒',
  'local_pharmacy': '💊', 'medical_services': '🏥', 'health_and_safety': '🏥',
  'directions_car': '🚗', 'local_taxi': '🚕', 'flight': '✈', 'directions_transit': '🚌',
  'local_gas_station': '⛽', 'local_parking': '🅿',
  'hotel': '🏨', 'house': '🏠', 'home': '🏠',
  'devices': '💻', 'computer': '💻', 'phone_android': '📱', 'smartphone': '📱',
  'sports_esports': '🎮', 'movie': '🎬', 'music_note': '🎵', 'theaters': '🎭',
  'school': '🎓', 'book': '📚',
  'account_balance': '🏦', 'savings': '💰', 'payments': '💳', 'credit_card': '💳',
  'attach_money': '💰', 'trending_up': '📈', 'bar_chart': '📊',
  'receipt': '🧾', 'receipt_long': '🧾',
  'work': '💼', 'business': '🏢', 'store': '🏪',
  'fitness_center': '🏋', 'spa': '💆',
  'volunteer_activism': '🤝', 'handshake': '🤝',
  'local_shipping': '📦', 'inventory': '📦',
  'wifi': '📶', 'router': '📶',
  'security': '🔒', 'gavel': '⚖',
  'more_horiz': '•', 'category': '•',
}

function getTxIcon(tx: PolpTransaction): string {
  // 1. Usar category.icon do Polp se disponível
  const cat = tx.category as Record<string, unknown> | null
  if (cat?.icon && typeof cat.icon === 'string') {
    const mapped = CATEGORY_ICON_MAP[cat.icon]
    if (mapped) return mapped
  }
  // 2. Match por nome de serviço conhecido
  const searchStr = `${tx.description ?? ''} ${tx.payment_data?.receiver?.name ?? ''} ${(tx.merchant as Record<string,unknown> | null)?.name ?? ''}`.toLowerCase()
  for (const [re, icon] of SERVICE_ICONS) {
    if (re.test(searchStr)) return icon
  }
  // 3. Routing number → banco
  const routing = tx.payment_data?.receiver?.routingNumber ?? tx.payment_data?.payer?.routingNumber ?? ''
  if (routing && BANK_ICONS[routing]) return BANK_ICONS[routing]
  // 4. MCC
  const mcc = tx.credit_card_metadata?.payeeMCC
  if (mcc && MCC_ICONS[mcc]) return MCC_ICONS[mcc]
  // 5. Fallback direcional
  return tx.type === 'CREDIT' ? '↑' : '↓'
}

const TX_CATEGORIES = [
  'Restaurante', 'Fast food', 'Supermercado', 'Delivery',
  'Transporte', 'Passagens', 'Combustível', 'Estacionamento',
  'Saúde', 'Farmácia', 'Academia',
  'Lazer', 'Streaming', 'Entretenimento',
  'Telefone', 'Internet', 'Assinatura',
  'Educação', 'Software',
  'Aluguel', 'Serviços', 'Fornecedor',
  'Salário', 'Transferência', 'PIX recebido',
  'Imposto', 'Tarifa bancária',
  'Outro',
]

function getTxFingerprint(tx: PolpTransaction): string {
  const m = tx.merchant as Record<string, unknown> | null
  if (m?.id) return `merchant:${m.id}`
  if (tx.description) return `desc:${tx.description}`
  return `id:${tx.id}`
}

export default function FinanceiroRoom() {
  const { go, addToast, openChatWith } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('decisoes')
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [analyticsPeriod, setAnalyticsPeriod] = useState<'30d' | '90d' | '1y'>('30d')
  const [queuedBillIds, setQueuedBillIds] = useState<Set<string>>(new Set())
  const [editingTxId, setEditingTxId] = useState<string | null>(null)
  const { data: localCategories = {} } = useTxCategories()
  const saveCategoryMut = useSaveTxCategory()

  const [approvalsQ, insightsQ, kpiQ, accountsQ, contextMetricsQ, polpAccountsQ, polpTxQ, polpBillsQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'financeiro', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('financeiro', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(10, 'financeiro'),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['finance-indicators', analyticsPeriod],
        queryFn: () => getFinanceIndicators(analyticsPeriod),
        enabled: !!clientId,
        staleTime: 120_000,
        refetchOnMount: 'always' as const,
      },
      {
        queryKey: ['financeiro-accounts', clientId ?? ''],
        queryFn: () => fetchConnectedAccounts(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['analytics', 'contextMetrics', clientId ?? '', analyticsPeriod],
        queryFn: () => getContextMetrics(analyticsPeriod),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['polp-accounts', clientId ?? ''],
        queryFn: () => fetchPolpAccounts(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['polp-transactions', clientId ?? ''],
        queryFn: () => fetchPolpTransactions(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['polp-bills', clientId ?? ''],
        queryFn: () => fetchPolpBills(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
    ],
  })

  const polpTransactions = polpTxQ.data ?? []

  const invalidateApprovals = () => qc.invalidateQueries({ queryKey: ['approvals'] })

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => { invalidateApprovals(); addToast('ok', 'Aprovado', 'Pagamento agendado.') },
  })
  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: () => { invalidateApprovals(); addToast('no', 'Rejeitado', 'Blu anotou.') },
  })
  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => { invalidateApprovals(); addToast('sn', 'Adiado', 'Lembrete em 2 horas.') },
  })
  const payBillMut = useMutation({
    mutationFn: ({ bill, cardName }: { bill: PolpBill; cardName: string }) =>
      createPaymentApproval(clientId!, bill, cardName),
    onSuccess: (_data, { bill, cardName }) => {
      setQueuedBillIds(prev => new Set([...prev, bill.id]))
      invalidateApprovals()
      addToast('ok', 'Aprovação criada', `Fatura ${cardName} aguarda confirmação.`)
    },
    onError: () => addToast('no', 'Erro', 'Não foi possível criar a aprovação.'),
  })
  const approvals = approvalsQ.data ?? []
  const pendingCount = approvals.length

  const finInsights = (insightsQ.data ?? []).filter(
    () => true  // room filter is server-side via p_room='financeiro'
  )
  const financeiroContextMetrics: ContextMetricRow[] = (contextMetricsQ.data ?? []).filter(
    (m) => m.dimension === 'finance'
  )

  const fin = kpiQ.data

  const accounts = accountsQ.data ?? []
  const polpAccounts = polpAccountsQ.data ?? []
  const polpBills = polpBillsQ.data ?? []

  const consolidatedBalance = polpAccounts.length > 0
    ? polpAccounts.filter(a => a.type === 'BANK').reduce((sum, a) => sum + a.balance, 0)
    : accounts.reduce((sum, a) => sum + (a.balance ?? 0), 0)

  const creditInUse = polpAccounts
    .filter(a => a.type === 'CREDIT')
    .reduce((sum, a) => {
      const cd = a.credit_data
      return sum + (cd?.creditLimit != null && cd?.availableCreditLimit != null ? cd.creditLimit - cd.availableCreditLimit : 0)
    }, 0)


  return (
    <div>
      <div className="rh">
        <div className="rav">📊</div>
        <div><div className="rn">Financeiro</div><div className="rd">Fluxo de caixa, pagamentos e relatórios</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }} onClick={() => openChatWith('Quero criar uma nova missão financeira')}>+ Nova Missão</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
            <span className="ph-cnt">{pendingCount} pendente{pendingCount !== 1 ? 's' : ''}</span>
          </div>
          <div className="rtabs" id="fTabs">
            {(['decisoes', 'compromissos', 'tarefas', 'historico', 'config'] as Tab[]).map(t => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'decisoes' ? <>Decisões {pendingCount > 0 && <span className="tbdg">{pendingCount}</span>}</>
                  : t === 'compromissos' ? <>Compromissos {polpBills.filter(b => b.status !== 'CLOSED').length > 0 && <span className="tbdg">{polpBills.filter(b => b.status !== 'CLOSED').length}</span>}</>
                  : t === 'historico' ? 'Histórico'
                  : t.charAt(0).toUpperCase() + t.slice(1)}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* DECISÕES */}
            <div className={`tc${tab === 'decisoes' ? ' on' : ''}`} id="f-decisoes">
              <div className="dl">
                {approvalsQ.isLoading && (
                  <LoadingState message="Carregando decisões financeiras…" />
                )}
                {!approvalsQ.isLoading && approvals.length === 0 && (
                  <EmptyState
                    icon="✓"
                    title="Nenhuma decisão pendente"
                    description="Tudo em dia. O Blu irá notificá-lo quando houver algo financeiro para resolver."
                  />
                )}
                {approvals.map(approval => (
                  <DecisionCard
                    key={approval.id}
                    approval={approval}
                    onApprove={function () { approveMut.mutate(approval.id) }}
                    onReject={function () { rejectMut.mutate(approval.id) }}
                    onSnooze={function () { snoozeMut.mutate(approval.id) }}
                  />
                ))}
              </div>
            </div>

            {/* COMPROMISSOS */}
            <div className={`tc${tab === 'compromissos' ? ' on' : ''}`} id="f-compromissos">
              {polpBillsQ.isLoading && (
                <LoadingState message="Carregando faturas de cartão…" />
              )}
              {!polpBillsQ.isLoading && polpBills.length === 0 && (
                <EmptyState
                  icon="💳"
                  title="Nenhuma fatura encontrada"
                  description="Conecte suas contas em Integrações para acompanhar faturas e vencimentos."
                />
              )}
              {(() => {
                // Deduplicate: show only the most recent cycle per card
                const latestPerAccount = polpBills.reduce<Map<number, PolpBill>>((map, bill) => {
                  const ex = map.get(bill.polp_account_id)
                  if (!ex || bill.due_date > ex.due_date) map.set(bill.polp_account_id, bill)
                  return map
                }, new Map())
                const dedupedBills = [...latestPerAccount.values()].sort((a, b) => a.due_date.localeCompare(b.due_date))

                // Older open cycles per account (to show summary)
                const olderCycles = (acctId: number, latestDue: string) =>
                  polpBills.filter(b => b.polp_account_id === acctId && b.due_date < latestDue)

                const today = new Date(); today.setHours(0, 0, 0, 0)
                const overdue = dedupedBills.filter(b => new Date(b.due_date) < today)
                const upcoming = dedupedBills.filter(b => new Date(b.due_date) >= today)

                const BillRow = ({ bill }: { bill: PolpBill }) => {
                  const dueDate = new Date(bill.due_date)
                  const todayMs = new Date().setHours(0, 0, 0, 0)
                  const daysUntil = Math.round((dueDate.getTime() - todayMs) / 86400000)
                  const isOverdue = daysUntil < 0
                  const isSoon = daysUntil <= 3 && !isOverdue
                  const isClosed = bill.status === 'CLOSED'
                  const cardName = polpAccounts.find(a => a.polp_account_id === bill.polp_account_id)?.marketing_name ?? 'Cartão'
                  const older = olderCycles(bill.polp_account_id, bill.due_date)
                  const olderTotal = older.reduce((s, b) => s + b.total_amount, 0)
                  const paidSum = Array.isArray(bill.payments)
                    ? bill.payments.reduce((s, p) => s + p.amount, 0)
                    : 0
                  const remaining = bill.total_amount - paidSum
                  const partiallyPaid = paidSum > 0 && remaining > 0
                  const isQueued = queuedBillIds.has(bill.id)

                  const WINDOW_MS = 7 * 86400000
                  const matchedTx = polpTransactions.filter(tx => {
                    if (tx.polp_account_id !== bill.polp_account_id) return false
                    if (tx.type !== 'CREDIT') return false
                    const diff = Math.abs(new Date(tx.date).getTime() - dueDate.getTime())
                    if (diff > WINDOW_MS) return false
                    const amt = Math.abs(tx.amount)
                    const tol = 0.01
                    const matchesTotal = bill.total_amount > 0 && Math.abs(amt - bill.total_amount) / bill.total_amount < tol
                    const matchesMin = bill.minimum_payment_amount != null && bill.minimum_payment_amount > 0
                      && Math.abs(amt - bill.minimum_payment_amount) / bill.minimum_payment_amount < tol
                    return matchesTotal || matchesMin
                  })

                  const showFooter = partiallyPaid || bill.minimum_payment_amount != null || matchedTx.length > 0 || older.length > 0
                  return (
                    <div className="dc warn" style={{ padding: '10px 12px', marginBottom: 6 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: showFooter ? 6 : 0 }}>
                        <span style={{ fontSize: 16, marginTop: 1 }}>💳</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 600 }}>{cardName}</div>
                          <div style={{ fontSize: 10, color: 'var(--mu)' }}>
                            Venc. {dueDate.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })}
                            {' '}·{' '}
                            <span style={{ color: isOverdue ? 'var(--urg)' : isSoon ? 'var(--att)' : 'var(--mu)' }}>
                              {isOverdue
                                ? `${Math.abs(daysUntil)}d atrasada`
                                : daysUntil === 0
                                  ? 'vence hoje'
                                  : `${daysUntil}d`}
                            </span>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                          <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--mono)', color: isOverdue ? 'var(--urg)' : 'var(--fg)' }}>
                            {formatBRL(bill.total_amount)}
                          </div>
                          {partiallyPaid && (
                            <div style={{ fontSize: 9.5, color: 'var(--ok)' }}>{formatBRL(paidSum)} pago</div>
                          )}
                          {!isClosed && (
                            <button
                              className="btn bp"
                              style={{ fontSize: 10, padding: '2px 8px', opacity: isQueued ? 0.55 : 1 }}
                              disabled={isQueued || payBillMut.isPending}
                              onClick={() => payBillMut.mutate({ bill, cardName })}
                            >
                              {isQueued ? '✓ Enviado' : 'Pagar agora'}
                            </button>
                          )}
                        </div>
                      </div>
                      {showFooter && (
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 10, color: 'var(--mu)', borderTop: '1px solid var(--bd)', paddingTop: 6 }}>
                          {partiallyPaid && (
                            <span style={{ color: 'var(--ok)' }}>
                              ✓ {formatBRL(paidSum)} pago · restante {formatBRL(remaining)}
                            </span>
                          )}
                          {bill.minimum_payment_amount != null && bill.minimum_payment_amount < bill.total_amount && (
                            <span>mín. {formatBRL(bill.minimum_payment_amount)}</span>
                          )}
                          {bill.allows_installments && <span>parcelável</span>}
                          {older.length > 0 && (
                            <span style={{ color: 'var(--urg)' }}>
                              ⚠ +{older.length} ciclo{older.length > 1 ? 's' : ''} anterior{older.length > 1 ? 'es' : ''} em aberto · {formatBRL(olderTotal)}
                            </span>
                          )}
                          {matchedTx.map((tx, i) => (
                            <span key={i} style={{ color: 'var(--ok)' }}>
                              💚 conciliada: {formatBRL(Math.abs(tx.amount))} em {new Date(tx.date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                }

                return (
                  <div className="dl">
                    {overdue.length > 0 && (
                      <>
                        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--urg)', letterSpacing: '0.06em', textTransform: 'uppercase', padding: '8px 0 4px' }}>
                          Atrasadas ({overdue.length})
                        </div>
                        {overdue.map(b => <BillRow key={b.id} bill={b} />)}
                      </>
                    )}
                    {upcoming.length > 0 && (
                      <>
                        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--mu)', letterSpacing: '0.06em', textTransform: 'uppercase', padding: '8px 0 4px' }}>
                          Próximas ({upcoming.length})
                        </div>
                        {upcoming.map(b => <BillRow key={b.id} bill={b} />)}
                      </>
                    )}
                  </div>
                )
              })()}
            </div>

            {/* TAREFAS */}
            <div className={`tc${tab === 'tarefas' ? ' on' : ''}`} id="f-tarefas">
              <RoutineExecutionFeed domain="financeiro" />
            </div>

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`} id="f-historico">
              {polpTxQ.isLoading && [0,1,2].map(i => (
                <div key={i} style={{ padding: '8px 0', opacity: 0.4, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <div style={{ background: 'var(--gb)', borderRadius: 3, height: 12, width: 32 }} />
                  <div style={{ background: 'var(--gb)', borderRadius: 3, height: 12, flex: 1 }} />
                  <div style={{ background: 'var(--gb)', borderRadius: 3, height: 12, width: 60 }} />
                </div>
              ))}
              {!polpTxQ.isLoading && polpTransactions.length === 0 && (
                <EmptyState
                  icon="💸"
                  title="Nenhuma transação encontrada"
                  description="Conecte suas contas bancárias em Integrações para visualizar movimentações."
                />
              )}
              {polpTransactions.map(tx => {
                const isCredit = tx.type === 'CREDIT'
                const isPending = tx.status === 'PENDING'

                const pd = tx.payment_data
                const pixReceiverName = pd?.paymentMethod === 'PIX' ? pd?.receiver?.name ?? null : null
                const merchant = tx.merchant as Record<string, unknown> | null
                // Usar logo do merchant do Polp diretamente (CDN confiável)
                const merchantLogo = (merchant?.logo_url as string | null) ?? null
                const label = (merchant?.name as string | null) ?? pixReceiverName ?? tx.description ?? '—'

                const MCC: Record<string, string> = {
                  '4121': 'Transporte', '4511': 'Passagens', '4814': 'Telecom',
                  '5411': 'Supermercado', '5732': 'Eletrônicos', '5812': 'Restaurante',
                  '5814': 'Fast food', '5912': 'Farmácia', '7011': 'Hotel',
                  '7372': 'Software', '7991': 'Lazer', '8099': 'Saúde',
                }
                const ccm = tx.credit_card_metadata
                const mccLabel = ccm?.payeeMCC ? MCC[ccm.payeeMCC] ?? null : null
                const cat = tx.category as Record<string, unknown> | null
                const pluggyCat = cat?.description as string | undefined
                const fingerprint = getTxFingerprint(tx)
                const categoryLabel = localCategories[fingerprint] ?? pluggyCat ?? mccLabel ?? null
                const isEditing = editingTxId === tx.id

                const saveCategory = (val: string) => {
                  const trimmed = val.trim()
                  if (trimmed) {
                    saveCategoryMut.mutate({ ...localCategories, [fingerprint]: trimmed })
                  }
                  setEditingTxId(null)
                }

                return (
                  <div key={tx.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 6,
                    padding: '5px 0',
                    borderBottom: '1px solid var(--gb)',
                    overflow: 'hidden',
                  }}>
                    {/* Icon */}
                    <span style={{ position: 'relative', width: 16, height: 16, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ fontSize: 13, lineHeight: 1 }}>{getTxIcon(tx)}</span>
                      {merchantLogo && (
                        <img src={merchantLogo} alt=""
                          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                          style={{ position: 'absolute', inset: 0, width: 16, height: 16, borderRadius: 3, objectFit: 'contain', background: 'var(--sb)' }}
                        />
                      )}
                    </span>
                    {/* Name */}
                    <span style={{ flex: '1 1 0', minWidth: 0, maxWidth: '42%', fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: isPending ? 'var(--mu)' : 'var(--fg)' }}>
                      {label}
                    </span>
                    {/* Category — dropdown */}
                    {isEditing ? (
                      <select
                        autoFocus
                        value={categoryLabel ?? ''}
                        style={{ width: 100, fontSize: 11, background: 'var(--sb)', border: '1px solid var(--ac)', borderRadius: 3, padding: '2px 4px', color: 'var(--fg)', outline: 'none', flexShrink: 0, cursor: 'pointer' }}
                        onChange={(e) => saveCategory(e.currentTarget.value)}
                        onBlur={() => setEditingTxId(null)}
                        onKeyDown={(e) => { if (e.key === 'Escape') setEditingTxId(null) }}
                      >
                        <option value="">— categoria —</option>
                        {TX_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    ) : (
                      <button
                        onClick={() => setEditingTxId(tx.id)}
                        style={{
                          fontSize: 11, flexShrink: 0, cursor: 'pointer', whiteSpace: 'nowrap',
                          background: categoryLabel ? 'color-mix(in srgb,var(--fg) 8%,transparent)' : 'transparent',
                          border: categoryLabel ? '1px solid color-mix(in srgb,var(--fg) 12%,transparent)' : '1px dashed color-mix(in srgb,var(--fg) 22%,transparent)',
                          borderRadius: 3, padding: '2px 6px',
                          color: categoryLabel ? 'var(--mu)' : 'color-mix(in srgb,var(--fg) 28%,transparent)',
                        }}
                      >
                        {categoryLabel ?? '+ cat'}
                      </button>
                    )}
                    {/* Date */}
                    <span style={{ fontSize: 11, color: 'var(--mu)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                      {new Date(tx.date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                    </span>
                    {/* Amount */}
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0, minWidth: 72, textAlign: 'right', color: isCredit ? 'var(--ok)' : isPending ? 'var(--mu)' : 'var(--fg)' }}>
                      {isCredit ? '+' : '−'}{formatBRL(Math.abs(tx.amount))}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="f-config">
              <RoutineConfigSection domain="financeiro" />
            </div>
            <div className="anl-hd" onClick={() => setAnalyticsOpen(o => !o)}>
              <span className="anl-ttl">📊 Analytics</span>
              <div className="anl-nums">
                <div className="anl-kpi">
                  <span className="anl-l">Faturamento</span>
                  <span className="anl-v">{fmtCompact(fin?.receita_liquida ?? null)}</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-l">Margem</span>
                  <span className="anl-v" style={{ color: 'var(--ok)' }}>
                    {fin?.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}
                  </span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-l">Despesas</span>
                  <span className="anl-v" style={{ color: 'var(--urg)' }}>{fmtCompact(fin?.custo_total ?? null)}</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-l">Fluxo 30d</span>
                  <span className="anl-v" style={{ color: fin?.cash_flow_30d != null ? (fin.cash_flow_30d >= 0 ? 'var(--ok)' : 'var(--urg)') : undefined }}>
                    {fmtCompact(fin?.cash_flow_30d ?? null)}
                  </span>
                </div>
              </div>
              <span className={`anl-chev${analyticsOpen ? ' open' : ''}`} id="anlChev">▶</span>
            </div>
            <div style={{ display: 'flex', gap: 4, padding: '0 12px 8px' }}>
              {(['30d', '90d', '1y'] as const).map(p => (
                <span
                  key={p}
                  className={`pill${analyticsPeriod === p ? ' on' : ''}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setAnalyticsPeriod(p)}
                >
                  {p === '30d' ? '30d' : p === '90d' ? '90d' : '1 ano'}
                </span>
              ))}
            </div>
            <div className={`anl-body${analyticsOpen ? ' open' : ''}`} id="anlBody">
              {kpiQ.isLoading ? (
                <LoadingState message="Carregando indicadores financeiros…" />
              ) : kpiQ.isError ? (
                <div style={{ fontSize: 11, color: 'var(--urg)', textAlign: 'center', padding: '8px 0' }}>
                  Erro ao carregar.{' '}
                  <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => void kpiQ.refetch()}>Tentar novamente</span>
                </div>
              ) : null}
              <div className="anl-kpi-grid">
                <div className="anl-kc">
                  <div className="anl-kl">Faturamento</div>
                  <div className="anl-kv">{fmtCompact(fin?.receita_liquida ?? null)}</div>
                  {fin?.receita_yoy_perc != null && (
                    <div className={`anl-kd ${fin.receita_yoy_perc >= 0 ? 'up' : 'dn'}`}>
                      {fin.receita_yoy_perc >= 0 ? '↑' : '↓'} {Math.abs(fin.receita_yoy_perc).toFixed(1)}% vs. período anterior
                    </div>
                  )}
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Despesas</div>
                  <div className="anl-kv">{fmtCompact(fin?.custo_total ?? null)}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Margem bruta</div>
                  <div className="anl-kv" style={{ color: 'var(--ok)' }}>
                    {fin?.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}
                  </div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Caixa consolidado</div>
                  <div className="anl-kv">{formatBRL(consolidatedBalance)}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Ticket médio</div>
                  <div className="anl-kv">{formatBRL(fin?.ticket_medio ?? null)}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Pedidos</div>
                  <div className="anl-kv">{fin?.total_pedidos ?? '—'}</div>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {([
                  { label: 'Margem operacional', value: fin?.margem_operacional_perc ?? null, fmt: 'perc', src: 'ERP / Contabilidade' },
                  { label: 'Burn rate mensal', value: fin?.burn_rate_mensal ?? null, fmt: 'brl', src: 'Integração contábil' },
                  { label: 'Runway', value: fin?.runway_meses ?? null, fmt: 'months', src: 'Contábil + caixa' },
                  { label: 'DSO', value: fin?.dso_dias ?? null, fmt: 'days', src: 'Sistema de cobrança' },
                  { label: 'DPO', value: fin?.dpo_dias ?? null, fmt: 'days', src: 'ERP / AP' },
                  { label: 'CCC', value: fin?.ccc_dias ?? null, fmt: 'days', src: 'DSO + DPO + estoque' },
                  { label: 'Fluxo 30d', value: fin?.cash_flow_30d ?? null, fmt: 'brl', src: 'Saldos diários' },
                ] as { label: string; value: number | null; fmt: 'perc' | 'brl' | 'days' | 'months'; src: string }[]).map(({ label, value, fmt, src }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                    <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{label}</span>
                    {value != null ? (
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {fmt === 'perc' ? `${value.toFixed(1)}%`
                          : fmt === 'brl' ? formatBRL(value)
                          : fmt === 'months' ? `${value.toFixed(1)}m`
                          : `${value.toFixed(0)}d`}
                      </span>
                    ) : (
                      <span style={{ fontSize: 9, color: 'var(--mu)', opacity: .5, fontStyle: 'italic', whiteSpace: 'nowrap', flexShrink: 0 }}>↳ {src}</span>
                    )}
                  </div>
                ))}
              </div>
              {financeiroContextMetrics.length > 0 && (
                <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  {financeiroContextMetrics.map((m) => (
                    <div key={m.kpi} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                      <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{m.label}</span>
                      {m.current_value != null && (
                        <span style={{ fontFamily: 'var(--mono)', color: 'var(--fg)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                          {m.unit === 'R$' ? formatBRL(m.current_value) : m.unit === '%' ? `${m.current_value.toFixed(1)}%` : m.current_value.toLocaleString('pt-BR')}
                        </span>
                      )}
                      {m.mom_pct != null && (
                        <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: m.mom_pct >= 0 ? 'var(--ok)' : 'var(--urg)', background: m.mom_pct >= 0 ? 'color-mix(in srgb,var(--ok) 12%,transparent)' : 'color-mix(in srgb,var(--urg) 12%,transparent)', padding: '1px 3px', borderRadius: 3, whiteSpace: 'nowrap', flexShrink: 0 }}>
                          {m.mom_pct >= 0 ? '↑' : '↓'}{Math.abs(m.mom_pct).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* SIDEBAR */}
        <div className="rcol">
          <RColResizeHandle />

          <CollapsiblePanel id="fin-contas" icon="🏦" title="Contas" action={<button className="ph-add" onClick={() => openChatWith('Quero adicionar uma nova conta bancária')}>＋</button>}>
            <div className="dr-sec">
              {polpAccountsQ.isLoading && [0,1].map(i => (
                <div key={i} style={{ padding: '8px 0', opacity: 0.4, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <div style={{ background: 'var(--gb)', borderRadius: '50%', height: 20, width: 20 }} />
                  <div style={{ background: 'var(--gb)', borderRadius: 3, height: 12, flex: 1 }} />
                  <div style={{ background: 'var(--gb)', borderRadius: 3, height: 12, width: 80 }} />
                </div>
              ))}
              {!polpAccountsQ.isLoading && polpAccounts.length === 0 && accounts.length === 0 && (
                <EmptyState
                  icon="🏦"
                  title="Nenhuma conta conectada"
                  description="Conecte contas bancárias e cartões em Integrações para acompanhar saldos e transações."
                />
              )}
              {polpAccounts.length > 0 ? polpAccounts.map(acc => {
                const cd = acc.credit_data
                const creditLimit = cd?.creditLimit ?? null
                const creditUsed = creditLimit != null && cd?.availableCreditLimit != null
                  ? creditLimit - cd.availableCreditLimit
                  : null
                const usedPct = creditUsed != null && creditLimit != null && creditLimit > 0
                  ? Math.min(100, (creditUsed / creditLimit) * 100)
                  : null
                const subtitle = acc.number ?? acc.owner ?? acc.subtype ?? ''
                return (
                  <div key={acc.id} className="acc-row" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 13 }}>{acc.type === 'CREDIT' ? '💳' : '🏦'}</span>
                      <div className="acc-name" style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 500 }}>{acc.marketing_name ?? acc.name ?? acc.subtype ?? acc.type}</div>
                        {subtitle && <div style={{ fontSize: 10, color: 'var(--mu)' }}>{subtitle}</div>}
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div className="acc-val" style={acc.balance < 0 ? { color: 'var(--urg)' } : undefined}>
                          {formatBRL(acc.balance)}
                        </div>
                        <div style={{ fontSize: 9.5, color: 'var(--ok)', fontFamily: 'var(--mono)' }}>↑ sincronizado</div>
                      </div>
                    </div>
                    {acc.type === 'CREDIT' && creditUsed != null && creditLimit != null && (
                      <div style={{ paddingLeft: 19 }}>
                        <div style={{ height: 3, background: 'var(--bd)', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${usedPct}%`, background: usedPct != null && usedPct > 80 ? 'var(--urg)' : 'var(--att)', borderRadius: 2 }} />
                        </div>
                        <div style={{ fontSize: 9.5, color: 'var(--mu)', marginTop: 2 }}>
                          {formatBRL(creditUsed)} de {formatBRL(creditLimit)} usados
                        </div>
                      </div>
                    )}
                  </div>
                )
              }) : accounts.map(acc => (
                <div key={acc.id} className="acc-row">
                  <span style={{ fontSize: 13 }}>{acc.provider.includes('cartão') || acc.provider.includes('card') ? '💳' : '🏦'}</span>
                  <div className="acc-name">
                    <div style={{ fontSize: 12, fontWeight: 500 }}>{acc.account_name ?? acc.provider}</div>
                    <div style={{ fontSize: 10, color: 'var(--mu)' }}>{acc.provider}</div>
                  </div>
                  <div>
                    <div className="acc-val" style={acc.balance !== null && acc.balance < 0 ? { color: 'var(--urg)' } : undefined}>
                      {formatBRL(acc.balance)}
                    </div>
                    <div style={{ fontSize: 9.5, color: acc.status === 'active' ? 'var(--ok)' : 'var(--att)', fontFamily: 'var(--mono)' }}>
                      {acc.status === 'active' ? '↑ sincronizado' : acc.status === 'error' ? '⚠ erro' : 'desconectado'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {(polpAccounts.length > 0 || accounts.length > 0) && (
              <div className="dr-sec">
                <div className="dr-ttl">Saldo consolidado</div>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--mono)', fontVariantNumeric: 'tabular-nums', color: 'var(--fg)' }}>
                  {formatBRL(consolidatedBalance)}
                </div>
                {creditInUse > 0 && (
                  <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 2 }}>
                    Caixa {formatBRL(consolidatedBalance)} · Crédito {formatBRL(creditInUse)} em uso
                  </div>
                )}
              </div>
            )}
          </CollapsiblePanel>
          <CollapsiblePanel id="fin-pagamentos" icon="📄" title="Próximos pagamentos">
            <div className="dr-sec">
              {polpBillsQ.isLoading && [0,1].map(i => (
                <div key={i} style={{ padding: '8px 0', opacity: 0.4, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <div style={{ background: 'var(--gb)', borderRadius: '50%', height: 20, width: 20 }} />
                  <div style={{ background: 'var(--gb)', borderRadius: 3, height: 12, flex: 1 }} />
                  <div style={{ background: 'var(--gb)', borderRadius: 3, height: 12, width: 80 }} />
                </div>
              ))}
              {!polpBillsQ.isLoading && polpBills.length === 0 && approvals.length === 0 && (
                <EmptyState
                  icon="📄"
                  title="Nenhum pagamento pendente"
                  description="Quando houver faturas ou aprovações a pagar, elas aparecerão aqui."
                />
              )}
              {polpBills.length > 0 ? (() => {
                const latest = [...polpBills.reduce<Map<number, PolpBill>>((m, b) => {
                  const ex = m.get(b.polp_account_id)
                  if (!ex || b.due_date > ex.due_date) m.set(b.polp_account_id, b)
                  return m
                }, new Map()).values()].sort((a, b) => a.due_date.localeCompare(b.due_date))
                const todayMs = new Date().setHours(0, 0, 0, 0)
                return latest.map(bill => {
                const rawDueDate = new Date(bill.due_date + 'T00:00:00')
                const isCurrentOverdue = rawDueDate.getTime() < todayMs

                // Project next cycle when the latest bill is already overdue
                const acc = polpAccounts.find(a => a.polp_account_id === bill.polp_account_id)
                const cd = acc?.credit_data
                let dueDate = rawDueDate
                let displayAmount = bill.total_amount
                let isProjected = false
                if (isCurrentOverdue) {
                  const next = new Date(rawDueDate)
                  next.setMonth(next.getMonth() + 1)
                  dueDate = next
                  isProjected = true
                  if (cd?.creditLimit != null && cd?.availableCreditLimit != null) {
                    displayAmount = cd.creditLimit - cd.availableCreditLimit
                  }
                }

                const daysUntil = Math.round((dueDate.getTime() - todayMs) / 86400000)
                const isOverdue = daysUntil < 0
                const isSoon = daysUntil <= 3 && !isOverdue
                const cardName = acc?.marketing_name ?? 'Fatura cartão'
                const partiallyPaid = !isProjected && Array.isArray(bill.payments) && bill.payments.length > 0
                return (
                  <div key={bill.id} className="hi">
                    <div className="hi-n">
                      {cardName}
                      {isProjected && <span style={{ marginLeft: 4, fontSize: 9, color: 'var(--mu)', fontStyle: 'italic' }}>projetada</span>}
                      {partiallyPaid && <span style={{ marginLeft: 4, fontSize: 9, color: 'var(--ok)' }}>✓ parcialmente pago</span>}
                    </div>
                    <div className="hi-m">
                      <span style={{ color: isOverdue ? 'var(--urg)' : isSoon ? 'var(--att)' : 'var(--mu)' }}>
                        {isOverdue ? `${Math.abs(daysUntil)}d atraso` : daysUntil === 0 ? 'hoje' : `${daysUntil}d`} · {dueDate.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                      </span>
                      <span className="hi-a" style={{ color: isOverdue ? 'var(--urg)' : 'var(--att)' }}>
                        {formatBRL(displayAmount)}
                      </span>
                    </div>
                    {!isProjected && bill.minimum_payment_amount != null && bill.minimum_payment_amount < bill.total_amount && (
                      <div style={{ fontSize: 9.5, color: 'var(--mu)', marginTop: 1 }}>
                        mínimo {formatBRL(bill.minimum_payment_amount)}
                      </div>
                    )}
                  </div>
                )
                })
              })() : approvals.map(a => (
                <div key={a.id} className="hi">
                  <div className="hi-n">{a.title}</div>
                  <div className="hi-m">
                    <span>{formatDate(a.created_at)}</span>
                    {(a.metadata as Record<string, unknown> | null)?.amount != null && (
                      <span className="hi-a" style={{ color: 'var(--att)' }}>
                        {formatBRL(Number((a.metadata as Record<string, unknown>).amount))}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CollapsiblePanel>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          {finInsights.length > 0 ? finInsights.slice(0, 3).map(ins => (
            <div key={ins.id} className="ich">
              <span className="ich-em">
                {ins.severity === 'error' ? '⚠️' : ins.severity === 'warning' ? '💡' : '📈'}
              </span>
              <div className="ich-body">
                <span className="ich-tag tg-f">{formatKpi(ins.kpi)}</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          )) : (
            <>
              <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-f">Tendência</span><div className="ich-txt">Carregando insights financeiros…</div></div></div>
            </>
          )}
          <div className="nums-chip" onClick={() => setTab('tarefas')} style={{ cursor: 'pointer' }}>
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver na aba Tarefas →</div>
          </div>
          <div className="nums-chip" onClick={() => setTab('historico')}>
            <div className="nums-head">📊 KPIs do mês</div>
            <div className="nums-row">
              <div className="nkpi">
                <span className="nv">{fin ? `${(fin.receita_liquida / 1000).toFixed(1)}K` : '—'}</span>
                <span className="nl">Faturamento</span>
                {fin?.receita_yoy_perc != null && (
                  <span className={`nd ${fin.receita_yoy_perc >= 0 ? 'up' : 'dn'}`}>
                    {fin.receita_yoy_perc >= 0 ? '↑' : '↓'} {Math.abs(fin.receita_yoy_perc).toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="nkpi">
                <span className="nv">{fin?.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}</span>
                <span className="nl">Margem</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
