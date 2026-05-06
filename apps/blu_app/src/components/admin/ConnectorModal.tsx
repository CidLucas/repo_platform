/**
 * ConnectorModal — credential form for each connector type.
 * Uses @radix-ui/react-dialog (same as ApprovalModal) + blu_app primitives.
 */

import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, AlertCircle, CheckCircle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { cn } from '@/utils/cn'
import { Button } from '@/components/primitives/Button'
import { Input } from '@/components/primitives/Input'
import { Select } from '@/components/primitives/Select'
import { createCredential } from '@/api/connectors'
import type { CredentialPayload } from '@/api/connectors'
import { useAuth } from '@/hooks/useAuth'
import type { ConnectorDef } from './IntegrationCard'

// ── Textarea primitive (blu_app has no Textarea primitive) ─────────────────

function Textarea({
  label,
  hint,
  error,
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string
  hint?: string
  error?: string
}) {
  return (
    <div className="w-full flex flex-col gap-1">
      {label && <label className="text-caption text-gray-200 font-medium select-none">{label}</label>}
      <textarea
        className={cn(
          'bg-elevated border border-border rounded text-white',
          'placeholder-gray-400 text-body-sm w-full px-3 py-2',
          'transition-colors duration-normal focus:outline-none resize-none',
          'hover:border-gray-400',
          error
            ? 'border-urgent focus:border-urgent'
            : 'focus:border-blu-500',
          className,
        )}
        {...props}
      />
      {error && <p className="text-caption-sm text-urgent">{error}</p>}
      {!error && hint && <p className="text-caption-sm text-gray-400">{hint}</p>}
    </div>
  )
}

// ── ConnectorModal ─────────────────────────────────────────────────────────

interface ConnectorModalProps {
  connector: ConnectorDef
  open: boolean
  onClose: () => void
}

type FormData = Record<string, string>

export function ConnectorModal({ connector, open, onClose }: ConnectorModalProps) {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [formData, setFormData] = useState<FormData>({})
  const [result, setResult] = useState<'success' | 'error' | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const set = (field: string, value: string) =>
    setFormData((prev) => ({ ...prev, [field]: value }))

  const mutation = useMutation({
    mutationFn: async () => {
      if (!clientId) throw new Error('Sessão inválida')
      const payload = buildPayload(connector.id, formData)
      return createCredential({
        client_id: clientId,
        nome_servico: connector.label,
        tipo_servico: connector.id.toUpperCase(),
        credentials: payload,
      })
    },
    onSuccess: () => {
      setResult('success')
      qc.invalidateQueries({ queryKey: ['integrations'] })
    },
    onError: (e) => {
      setResult('error')
      setErrorMsg(e instanceof Error ? e.message : 'Tente novamente mais tarde.')
    },
  })

  function handleClose() {
    setFormData({})
    setResult(null)
    setErrorMsg(null)
    onClose()
  }

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && handleClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            'fixed inset-0 z-40 bg-black/70 backdrop-blur-sm',
            'data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out',
          )}
        />
        <Dialog.Content
          aria-describedby={undefined}
          className={cn(
            'fixed z-50 flex flex-col',
            'inset-0 bg-surface overflow-y-auto',
            'md:inset-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2',
            'md:w-full md:max-w-lg md:max-h-[90dvh] md:rounded-lg md:shadow-xl',
            'md:border md:border-border md:overflow-hidden',
            'data-[state=open]:animate-slide-up data-[state=closed]:opacity-0',
          )}
          aria-label={`Conectar ${connector.label}`}
        >
          {/* Accent bar */}
          <div
            className="h-0.5 shrink-0 rounded-t-lg"
            style={{ background: `linear-gradient(to right, ${connector.color}, transparent)` }}
          />

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
            <div className="flex items-center gap-3">
              <ProviderBadge color={connector.color} label={connector.label} />
              <div>
                <Dialog.Title className="text-body font-medium text-white leading-none">
                  Conectar {connector.label}
                </Dialog.Title>
                <p className="text-caption text-gray-400 mt-0.5">Configure as credenciais de acesso</p>
              </div>
            </div>
            <Dialog.Close asChild>
              <button
                className="p-1.5 rounded text-gray-400 hover:text-white transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-blu-500 outline-none"
                aria-label="Fechar"
              >
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-4 md:p-5">
            {result === 'success' ? (
              <SuccessState connector={connector} onClose={handleClose} />
            ) : (
              <div className="flex flex-col gap-4">
                {renderFields(connector.id, formData, set)}
                {result === 'error' && errorMsg && (
                  <div className="flex items-start gap-2 rounded border border-urgent/30 bg-urgent/10 px-3 py-2 text-caption text-urgent">
                    <AlertCircle size={14} className="shrink-0 mt-0.5" />
                    {errorMsg}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          {result !== 'success' && (
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border shrink-0">
              <Button variant="ghost" size="sm" onClick={handleClose}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={mutation.isPending}
                onClick={() => mutation.mutate()}
              >
                {connector.id === 'whatsapp' ? 'Salvar' : 'Conectar'}
              </Button>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────

function ProviderBadge({ color, label }: { color: string; label: string }) {
  const initials = label
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
  return (
    <div
      className="w-9 h-9 rounded-md flex items-center justify-center shrink-0 text-caption font-medium"
      style={{ backgroundColor: `${color}22`, border: `1px solid ${color}33` }}
    >
      <span style={{ color }}>{initials}</span>
    </div>
  )
}

function SuccessState({ connector, onClose }: { connector: ConnectorDef; onClose: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-6 text-center">
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center"
        style={{ backgroundColor: `${connector.color}22` }}
      >
        <CheckCircle size={24} style={{ color: connector.color }} />
      </div>
      <div>
        <p className="text-body font-medium text-white">{connector.label} conectado!</p>
        <p className="text-caption text-gray-400 mt-1">
          {connector.id === 'bigquery'
            ? 'Descoberta de colunas em andamento em segundo plano.'
            : 'Suas credenciais foram salvas com sucesso.'}
        </p>
      </div>
      <Button variant="primary" size="sm" onClick={onClose}>
        Fechar
      </Button>
    </div>
  )
}

// ── Field renderers per connector type ────────────────────────────────────

function renderFields(id: string, data: FormData, set: (k: string, v: string) => void) {
  switch (id) {
    case 'whatsapp':
      return (
        <>
          <Input
            label="Número WhatsApp"
            placeholder="+5511999999999"
            value={data.whatsapp_number ?? ''}
            onChange={(e) => set('whatsapp_number', e.target.value)}
            hint="Número com código do país que será usado para enviar e receber mensagens."
          />
          <Input
            label="Identificação (opcional)"
            placeholder="Ex: WhatsApp Comercial"
            value={data.contact_label ?? ''}
            onChange={(e) => set('contact_label', e.target.value)}
            hint="Rótulo amigável para identificar este número internamente."
          />
        </>
      )

    case 'shopify':
      return (
        <>
          <Input
            label="Nome da Loja"
            placeholder="minha-loja"
            value={data.shop_name ?? ''}
            onChange={(e) => set('shop_name', e.target.value)}
            hint="O subdomínio da sua loja (ex: minha-loja.myshopify.com)"
          />
          <Input
            label="Access Token"
            type="password"
            placeholder="shpat_..."
            value={data.access_token ?? ''}
            onChange={(e) => set('access_token', e.target.value)}
            hint="Token de acesso da Admin API do Shopify."
          />
          <Select
            label="Versão da API"
            value={data.api_version ?? '2024-01'}
            onChange={(e) => set('api_version', e.target.value)}
          >
            <option value="2024-01">2024-01 (Recomendado)</option>
            <option value="2023-10">2023-10</option>
            <option value="2023-07">2023-07</option>
          </Select>
        </>
      )

    case 'vtex':
      return (
        <>
          <Input
            label="Nome da Conta"
            placeholder="minhaloja"
            value={data.account_name ?? ''}
            onChange={(e) => set('account_name', e.target.value)}
          />
          <Input
            label="App Key"
            placeholder="vtexappkey-minhaloja-XXXXX"
            value={data.app_key ?? ''}
            onChange={(e) => set('app_key', e.target.value)}
          />
          <Input
            label="App Token"
            type="password"
            placeholder="..."
            value={data.app_token ?? ''}
            onChange={(e) => set('app_token', e.target.value)}
          />
          <Select
            label="Ambiente"
            value={data.environment ?? 'vtexcommercestable'}
            onChange={(e) => set('environment', e.target.value)}
          >
            <option value="vtexcommercestable">Produção (stable)</option>
            <option value="vtexcommercebeta">Beta</option>
          </Select>
        </>
      )

    case 'loja_integrada':
      return (
        <>
          <Input
            label="Chave da API"
            type="password"
            placeholder="Sua chave de API"
            value={data.api_key ?? ''}
            onChange={(e) => set('api_key', e.target.value)}
            hint="Painel Admin → Configurações → Integrações → API"
          />
          <Input
            label="Chave da Aplicação (opcional)"
            placeholder="Para apps parceiros"
            value={data.application_key ?? ''}
            onChange={(e) => set('application_key', e.target.value)}
          />
        </>
      )

    case 'bigquery':
      return (
        <>
          <Textarea
            label="Service Account JSON"
            placeholder='{"type": "service_account", "project_id": "...", ...}'
            value={data.service_account_json ?? ''}
            onChange={(e) => set('service_account_json', e.target.value)}
            rows={5}
            className="font-mono text-xs"
            hint="Cole o conteúdo do arquivo JSON da Service Account (contém project_id)."
          />
          <Input
            label="Dataset ID"
            placeholder="meu_dataset"
            value={data.dataset_id ?? ''}
            onChange={(e) => set('dataset_id', e.target.value)}
          />
          <Input
            label="Nome da Tabela"
            placeholder="minha_tabela"
            value={data.table_name ?? ''}
            onChange={(e) => set('table_name', e.target.value)}
            hint="Nome da tabela no BigQuery que você deseja sincronizar."
          />
          <Select
            label="Região dos dados"
            value={data.location ?? 'southamerica-east1'}
            onChange={(e) => set('location', e.target.value)}
          >
            <option value="southamerica-east1">South America — São Paulo</option>
            <option value="US">United States (US)</option>
            <option value="EU">European Union (EU)</option>
            <option value="us-east1">US East (us-east1)</option>
            <option value="us-west1">US West (us-west1)</option>
            <option value="asia-northeast1">Asia Northeast — Tokyo</option>
          </Select>
        </>
      )

    case 'postgresql':
    case 'mysql': {
      const defaultPort = id === 'postgresql' ? '5432' : '3306'
      return (
        <>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <Input
                label="Host"
                placeholder="localhost"
                value={data.host ?? ''}
                onChange={(e) => set('host', e.target.value)}
              />
            </div>
            <Input
              label="Porta"
              placeholder={defaultPort}
              value={data.port ?? ''}
              onChange={(e) => set('port', e.target.value)}
            />
          </div>
          <Input
            label="Banco de Dados"
            placeholder="meu_banco"
            value={data.database ?? ''}
            onChange={(e) => set('database', e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Usuário"
              placeholder="usuario"
              value={data.user ?? ''}
              onChange={(e) => set('user', e.target.value)}
            />
            <Input
              label="Senha"
              type="password"
              placeholder="••••••••"
              value={data.password ?? ''}
              onChange={(e) => set('password', e.target.value)}
            />
          </div>
        </>
      )
    }

    case 'conta_azul':
      return (
        <>
          <Input
            label="Client ID"
            placeholder="Seu Client ID OAuth2"
            value={data.client_id ?? ''}
            onChange={(e) => set('client_id', e.target.value)}
            hint="Conta Azul → Configurações → Integrações → Aplicativos"
          />
          <Input
            label="Client Secret"
            type="password"
            placeholder="Seu Client Secret OAuth2"
            value={data.client_secret ?? ''}
            onChange={(e) => set('client_secret', e.target.value)}
            hint="Gerado junto com o Client ID na mesma tela de Aplicativos."
          />
          <Input
            label="Access Token"
            type="password"
            placeholder="Token de acesso OAuth2"
            value={data.access_token ?? ''}
            onChange={(e) => set('access_token', e.target.value)}
            hint="Token obtido após autorizar o aplicativo no fluxo OAuth2 do Conta Azul."
          />
        </>
      )

    default:
      return (
        <p className="text-caption text-gray-400">
          Configuração para este conector em breve.
        </p>
      )
  }
}

// ── Payload builder ────────────────────────────────────────────────────────

function buildPayload(id: string, data: FormData): CredentialPayload {
  switch (id) {
    case 'shopify':
      return {
        shop_name: data.shop_name || '',
        access_token: data.access_token || '',
        api_version: data.api_version || '2024-01',
      }
    case 'vtex':
      return {
        account_name: data.account_name || '',
        app_key: data.app_key || '',
        app_token: data.app_token || '',
        environment: data.environment || 'vtexcommercestable',
      }
    case 'loja_integrada':
      return {
        api_key: data.api_key || '',
        application_key: data.application_key,
      }
    case 'bigquery': {
      let sa: Record<string, unknown> = {}
      try {
        sa = JSON.parse(data.service_account_json || '{}')
      } catch {
        // invalid JSON — will fail on the server
      }
      return {
        project_id: (sa.project_id as string) || '',
        dataset_id: data.dataset_id || '',
        table_name: data.table_name || '',
        location: data.location || 'southamerica-east1',
        service_account_json: sa,
      }
    }
    case 'postgresql':
    case 'mysql':
      return {
        host: data.host || '',
        port: parseInt(data.port || '5432', 10),
        database: data.database || '',
        user: data.user || '',
        password: data.password || '',
      }
    case 'whatsapp':
      return {
        whatsapp_number: data.whatsapp_number || '',
        contact_label: data.contact_label || '',
      }
    case 'conta_azul':
      return {
        client_id: data.client_id || '',
        client_secret: data.client_secret || '',
        access_token: data.access_token || '',
      }
    default:
      return {} as CredentialPayload
  }
}
