import { useAppStore } from '../../store/appStore'
import Modal from './Modal'

interface ModalField {
  label: string
  type: string
  placeholder: string
}

type IntgFields = Record<string, ModalField[]>

const FIELDS: IntgFields = {
  brad:    [['Cliente ID','text','123456789'],['Client Secret','password','••••••'],['Agência','text','0001'],['Conta PJ','text','']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  nub:     [['Chave de API','password','••••••'],['ID Empresa','text','']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  omie:    [['App Key','text',''],['App Secret','password',''],['Código Empresa','text','']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  tiny:    [['Token de API','password',''],['ID Loja','text','']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  outlook: [['Tenant ID','text',''],['Client ID','text',''],['Client Secret','password','']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  wab:     [['Número de telefone','tel','+55 11 9 0000-0000'],['API Key','password',''],['Webhook URL','text','https://']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  pbi:     [['Workspace ID','text',''],['Client ID','text',''],['Client Secret','password','']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  slack:   [['Bot Token','password','xoxb-'],['Canal padrão','text','#blu-alertas']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  'ic-monday': [['Token de API','password','eyJhbGci...']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  'ic-notion':  [['Token de integração','password','secret_...']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  'ic-asana':   [['Token pessoal','password','0/...']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  'ic-clickup': [['API Key','password','pk_...']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
  'ic-linear':  [['API Key','password','lin_api_...']].map(([l,t,p]) => ({ label: l, type: t, placeholder: p })),
}

const DEFAULT_FIELDS: ModalField[] = [
  { label: 'API Key', type: 'password', placeholder: '' },
  { label: 'Domínio / URL', type: 'text', placeholder: '' },
]

interface IntegrationModalProps {
  open: boolean
  rowId: string
  name: string
  mode: 'connect' | 'config'
  onClose: () => void
  onConnect: (rowId: string) => void
  onDisconnect: (rowId: string) => void
}

export default function IntegrationModal({
  open,
  rowId,
  name,
  mode,
  onClose,
  onConnect,
  onDisconnect,
}: IntegrationModalProps) {
  const { addToast } = useAppStore()
  const fields = FIELDS[rowId] ?? DEFAULT_FIELDS

  const handleConnect = () => {
    onConnect(rowId)
    addToast('ok', 'Conectado', `${name} conectado com sucesso.`)
    onClose()
  }

  const handleDisconnect = () => {
    onDisconnect(rowId)
    addToast('ok', 'Desconectado', `${name} desconectado.`)
    onClose()
  }

  const handleSave = () => {
    addToast('ok', 'Salvo', 'Configurações salvas.')
    onClose()
  }

  const handleSync = () => {
    addToast('ok', 'Sincronizando', 'Sincronização iniciada.')
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      width="440px"
      title={mode === 'connect' ? `Conectar — ${name}` : `Configurar — ${name}`}
      subtitle={mode === 'connect'
        ? `Informe as credenciais para ativar a integração com ${name}.`
        : 'Integração ativa. Revise ou atualize as configurações abaixo.'}
    >
      <div className="modal-body" id="m-body">
        {mode === 'connect' ? (
          fields.map((f, i) => (
            <div className="intg-field" key={i}>
              <label>{f.label}</label>
              <input type={f.type} placeholder={f.placeholder} />
            </div>
          ))
        ) : (
          <>
            <div className="intg-field">
              <label>API Key / Credencial</label>
              <input type="password" value="••••••••••••" readOnly />
            </div>
            <div className="intg-field">
              <label>Última sincronização</label>
              <input type="text" value="05/05/2026 10:32" readOnly />
            </div>
            <div className="intg-field">
              <label>Dados sincronizados este mês</label>
              <input type="text" value="1.247 registros" readOnly />
            </div>
            <div style={{ marginTop: 14 }}>
              <div className="ld-lbl" style={{ marginBottom: 6 }}>Ações</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn bs" style={{ fontSize: 11 }} onClick={handleSync}>
                  Sincronizar agora
                </button>
                <button className="btn brd" style={{ fontSize: 11 }} onClick={handleDisconnect}>
                  Desconectar
                </button>
              </div>
            </div>
          </>
        )}
      </div>
      <div className="modal-acts" id="m-acts">
        <button className="btn bg" onClick={onClose}>Cancelar</button>
        {mode === 'connect' ? (
          <button className="btn bp" onClick={handleConnect}>Conectar</button>
        ) : (
          <button className="btn bp" onClick={handleSave}>Salvar</button>
        )}
      </div>
    </Modal>
  )
}
