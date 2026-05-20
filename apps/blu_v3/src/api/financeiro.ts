import { supabase } from './client'

export interface CnpjEnrichment {
  brand: string | null
  logo_url: string | null
  colors: Record<string, string> | null
  social: Record<string, string> | null
}

export async function fetchCnpjEnrichments(cnpjs: string[]): Promise<Record<string, CnpjEnrichment>> {
  const digits = cnpjs.map(c => c.replace(/\D/g, '')).filter(c => c.length === 14)
  if (digits.length === 0) return {}
  const { data, error } = await supabase.functions.invoke('polp-cnpj-enrich', {
    body: { cnpjs: digits },
  })
  if (error) throw error
  return (data ?? {}) as Record<string, CnpjEnrichment>
}

export interface CreditData {
  creditLimit: number | null
  availableCreditLimit: number | null
  minimumPayment: number | null
  balanceDueDate: string | null
  brand: string | null
  level: string | null
}

export interface PolpAccount {
  id: string
  client_id: string
  integration_id: string
  polp_account_id: number
  type: 'BANK' | 'CREDIT' | string
  subtype: string | null
  number: string | null
  name: string | null
  balance: number
  currency_code: string
  marketing_name: string | null
  owner: string | null
  credit_data: CreditData | null
  updated_at: string
}

export interface PaymentDataParty {
  name: string | null
  document: string | null
  branchNumber: string | null
  documentType: string | null
  accountNumber: string | null
  routingNumber: string | null
}

export interface PaymentData {
  paymentMethod: string | null
  receiver: PaymentDataParty | null
  payer: PaymentDataParty | null
  reason: string | null
  referenceNumber: string | null
  receiverReferenceId: string | null
}

export interface CreditCardMetadata {
  billId: string | null
  payeeMCC: string | null
  cardNumber: string | null
  totalAmount: number | null
  purchaseDate: string | null
  installmentNumber: number | null
  totalInstallments: number | null
}

export interface PolpTransaction {
  id: string
  client_id: string
  polp_account_id: number
  polp_transaction_id: number
  external_id: string | null
  description: string | null
  amount: number
  currency_code: string
  date: string
  type: 'DEBIT' | 'CREDIT' | string
  status: string | null
  balance_after: number | null
  category: Record<string, unknown> | null
  merchant: Record<string, unknown> | null
  payment_data: PaymentData | null
  credit_card_metadata: CreditCardMetadata | null
  updated_at: string
}

export interface PolpBillPayment {
  amount: number
  date: string
}

export interface PolpBill {
  id: string
  client_id: string
  polp_account_id: number
  polp_bill_id: number
  due_date: string
  total_amount: number
  minimum_payment_amount: number | null
  currency_code: string
  allows_installments: boolean | null
  payments: PolpBillPayment[] | null
  status: string
  updated_at: string
}

export async function fetchPolpAccounts(clientId: string): Promise<PolpAccount[]> {
  const { data, error } = await supabase
    .from('polp_accounts')
    .select('id, client_id, integration_id, polp_account_id, type, subtype, number, name, balance, currency_code, marketing_name, owner, credit_data, updated_at')
    .eq('client_id', clientId)
    .order('type')
  if (error) throw error
  return (data ?? []) as PolpAccount[]
}

export async function fetchPolpTransactions(clientId: string, limit = 50): Promise<PolpTransaction[]> {
  const { data, error } = await supabase
    .from('polp_transactions')
    .select('id, client_id, polp_account_id, polp_transaction_id, external_id, description, amount, currency_code, date, type, status, balance_after, category, merchant, payment_data, credit_card_metadata, updated_at')
    .eq('client_id', clientId)
    .order('date', { ascending: false })
    .limit(limit)
  if (error) throw error
  return (data ?? []) as PolpTransaction[]
}

export async function fetchPolpBills(clientId: string): Promise<PolpBill[]> {
  const { data, error } = await supabase
    .from('polp_bills')
    .select('id, client_id, polp_account_id, polp_bill_id, due_date, total_amount, minimum_payment_amount, currency_code, allows_installments, payments, status, updated_at')
    .eq('client_id', clientId)
    .eq('status', 'open')
    .gt('total_amount', 0)
    .order('due_date', { ascending: true })
  if (error) throw error
  return (data ?? []) as PolpBill[]
}

export interface ConnectedAccount {
  id: string
  provider: string
  account_name: string | null
  balance: number | null
  currency: string
  status: 'active' | 'error' | 'disconnected'
  last_sync_at: string | null
}

export interface ReportRun {
  id: string
  report_type: 'dre' | 'cash_flow' | 'margin' | 'custom'
  label: string
  period: string
  status: 'ready' | 'generating' | 'error'
  created_at: string
  file_url: string | null
}

export async function fetchConnectedAccounts(clientId: string): Promise<ConnectedAccount[]> {
  const { data, error } = await supabase
    .from('credencial_servico_externo')
    .select('id, tipo_servico, nome_servico, status, ativo, connection_metadata, updated_at')
    .eq('client_id', clientId)
    .order('tipo_servico')

  if (error) throw error
  return (data ?? []).map((row) => {
    const meta = (row.connection_metadata ?? {}) as Record<string, unknown>
    const rawStatus = row.status as string | null
    const ativo = row.ativo as boolean | null
    let status: ConnectedAccount['status'] = 'disconnected'
    if (rawStatus === 'error') status = 'error'
    else if (rawStatus === 'active' || ativo === true) status = 'active'
    return {
      id: row.id,
      provider: (row.tipo_servico ?? row.nome_servico ?? 'Integração') as string,
      account_name: (row.nome_servico as string | null) ?? null,
      balance: typeof meta.balance === 'number' ? meta.balance : null,
      currency: typeof meta.currency === 'string' ? meta.currency : 'BRL',
      status,
      last_sync_at: (row.updated_at as string | null) ?? null,
    }
  })
}

export async function fetchReportRuns(clientId: string): Promise<ReportRun[]> {
  const { data, error } = await supabase
    .from('report_runs')
    .select('id, status, output_url, started_at, completed_at, metadata')
    .eq('client_id', clientId)
    .order('started_at', { ascending: false })
    .limit(10)

  if (error) throw error
  return (data ?? []).map((row) => {
    const meta = (row.metadata ?? {}) as Record<string, unknown>
    return {
      id: row.id,
      report_type: (typeof meta.report_type === 'string' ? meta.report_type : 'custom') as ReportRun['report_type'],
      label: typeof meta.label === 'string' ? meta.label : 'Relatório',
      period: typeof meta.period === 'string' ? meta.period : '',
      status: row.status ?? 'ready',
      created_at: row.started_at,
      file_url: row.output_url ?? null,
    }
  })
}
