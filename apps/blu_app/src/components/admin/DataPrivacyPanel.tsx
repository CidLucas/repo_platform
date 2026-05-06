import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Shield, Download, Trash2, AlertTriangle, CheckCircle } from 'lucide-react'
import { Button } from '@/components/primitives/Button'
import { requestDataExport, requestDataDeletion } from '@/api/admin'

interface DataPrivacyPanelProps {
  clientId: string
}

export function DataPrivacyPanel({ clientId }: DataPrivacyPanelProps) {
  const [exportDone, setExportDone] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleteRequested, setDeleteRequested] = useState(false)

  const exportMutation = useMutation({
    mutationFn: () => requestDataExport(clientId),
    onSuccess: () => setExportDone(true),
  })

  const deleteMutation = useMutation({
    mutationFn: () => requestDataDeletion(clientId),
    onSuccess: () => {
      setDeleteRequested(true)
      setDeleteConfirm(false)
    },
  })

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-md bg-blu-500/10 border border-blu-500/20 flex items-center justify-center shrink-0">
          <Shield size={18} strokeWidth={1.5} className="text-blu-400" />
        </div>
        <div>
          <h2 className="text-heading-sm text-white">Privacidade e LGPD</h2>
          <p className="text-caption text-gray-400 mt-0.5">
            Gerencie seus dados pessoais de acordo com a Lei Geral de Proteção de Dados (LGPD).
          </p>
        </div>
      </div>

      {/* Rights summary */}
      <div className="bg-surface border border-border rounded-md p-4">
        <h3 className="text-body-sm font-medium text-white mb-3">Seus direitos</h3>
        <ul className="space-y-2 text-caption text-gray-400">
          {[
            'Acessar todos os dados pessoais que armazenamos sobre você',
            'Exportar seus dados em formato legível por máquina',
            'Corrigir dados incorretos ou incompletos',
            'Solicitar a exclusão de seus dados (direito ao esquecimento)',
            'Revogar consentimento de uso dos seus dados a qualquer momento',
          ].map((right) => (
            <li key={right} className="flex items-start gap-2">
              <CheckCircle size={13} strokeWidth={2} className="text-ok shrink-0 mt-0.5" />
              {right}
            </li>
          ))}
        </ul>
      </div>

      {/* Data export */}
      <div className="bg-surface border border-border rounded-md p-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h3 className="text-body-sm font-medium text-white">Exportar meus dados</h3>
            <p className="text-caption text-gray-400 mt-0.5">
              Receba um arquivo com todos os dados que o Blu armazena sobre sua conta
              e empresa. Será enviado ao e-mail cadastrado em até 48h.
            </p>
          </div>
          {exportDone ? (
            <div className="flex items-center gap-1.5 text-caption text-ok shrink-0">
              <CheckCircle size={14} strokeWidth={2} />
              Solicitação enviada
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              loading={exportMutation.isPending}
              onClick={() => exportMutation.mutate()}
              leftIcon={<Download size={14} strokeWidth={1.5} />}
              className="shrink-0"
            >
              Solicitar exportação
            </Button>
          )}
        </div>
      </div>

      {/* Data retention */}
      <div className="bg-surface border border-border rounded-md p-4">
        <h3 className="text-body-sm font-medium text-white mb-2">Retenção de dados</h3>
        <div className="space-y-2 text-caption text-gray-400">
          <div className="flex justify-between">
            <span>Dados de aprovações</span>
            <span className="text-gray-300">2 anos</span>
          </div>
          <div className="flex justify-between">
            <span>Logs de auditoria</span>
            <span className="text-gray-300">5 anos (obrigação legal)</span>
          </div>
          <div className="flex justify-between">
            <span>Conversas com agentes</span>
            <span className="text-gray-300">1 ano</span>
          </div>
          <div className="flex justify-between">
            <span>Dados analíticos</span>
            <span className="text-gray-300">3 anos</span>
          </div>
        </div>
      </div>

      {/* Data deletion */}
      <div className="bg-surface border border-urgent/30 rounded-md p-4">
        <h3 className="text-body-sm font-medium text-urgent mb-1">Excluir meus dados</h3>
        <p className="text-caption text-gray-400 mb-3">
          Solicita a exclusão permanente de todos os dados associados à sua conta.
          Esta ação não pode ser desfeita. Logs de auditoria obrigatórios serão
          anonimizados, não excluídos, conforme exigido por lei.
        </p>

        {deleteRequested ? (
          <div className="flex items-center gap-2 text-caption text-ok">
            <CheckCircle size={14} strokeWidth={2} />
            Solicitação de exclusão registrada. Nossa equipe entrará em contato em até 15 dias úteis.
          </div>
        ) : !deleteConfirm ? (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setDeleteConfirm(true)}
            leftIcon={<Trash2 size={13} strokeWidth={1.5} />}
          >
            Solicitar exclusão
          </Button>
        ) : (
          <div className="space-y-3">
            <div className="flex items-start gap-2 p-3 bg-urgent/10 rounded border border-urgent/20">
              <AlertTriangle size={14} strokeWidth={1.5} className="text-urgent shrink-0 mt-0.5" />
              <p className="text-caption text-urgent">
                Tem certeza? Todos os dados serão excluídos permanentemente, incluindo histórico
                de aprovações, insights e configurações. Isso encerrará sua conta no Blu.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="danger"
                size="sm"
                loading={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate()}
              >
                Sim, excluir minha conta
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDeleteConfirm(false)}
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* DPO contact */}
      <p className="text-caption-sm text-gray-500">
        Para exercer seus direitos ou tirar dúvidas, entre em contato com nosso{' '}
        <a
          href="mailto:dpo@blu.ai"
          className="text-blu-400 hover:text-blu-300 underline underline-offset-2 transition-colors duration-normal"
        >
          Encarregado de Dados (DPO)
        </a>
        {' '}em dpo@blu.ai.
      </p>
    </div>
  )
}
