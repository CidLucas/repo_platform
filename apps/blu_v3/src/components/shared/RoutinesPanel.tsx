import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchRoutines,
  fetchCustomRoutines,
  fetchAgentActions,
  toggleRoutine,
  createCustomRoutine,
  deleteCustomRoutine,
  submitRoutineForApproval,
  type ClientRoutine,
  type CustomRoutine,
  type RoutineStep,
} from '../../api/routines'

// ─── Catalog routine row ──────────────────────────────────────────────────────

function CatalogRoutineRow({
  routine,
  onToggle,
}: {
  routine: ClientRoutine
  onToggle: (id: string, enabled: boolean) => void
}) {
  const isActive = routine.active && routine.status === 'active'
  const name = routine.cross_agent_routines?.name ?? routine.routine_id

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '9px 12px',
        background: 'var(--glass)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--r)',
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600 }}>{name}</div>
        {routine.routine_id && (
          <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 2 }}>{routine.routine_id}</div>
        )}
      </div>
      <div
        onClick={() => onToggle(routine.id, !isActive)}
        style={{
          width: 36,
          height: 20,
          borderRadius: 10,
          background: isActive ? 'var(--ok)' : 'var(--gb)',
          cursor: 'pointer',
          position: 'relative',
          transition: 'background .2s',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 2,
            left: isActive ? 18 : 2,
            width: 16,
            height: 16,
            borderRadius: 8,
            background: '#fff',
            transition: 'left .2s',
          }}
        />
      </div>
    </div>
  )
}

// ─── Custom routine row ───────────────────────────────────────────────────────

function CustomRoutineRow({
  routine,
  onDelete,
  onSubmit,
}: {
  routine: CustomRoutine
  onDelete: (id: string) => void
  onSubmit: (id: string, name: string) => void
}) {
  const statusColor: Record<string, string> = {
    active: 'var(--ok)',
    inactive: 'var(--mu)',
    pending_approval: '#fbbf24',
    draft: 'var(--mu)',
  }
  const statusLabel: Record<string, string> = {
    active: 'Ativa',
    inactive: 'Inativa',
    pending_approval: 'Aguardando aprovação',
    draft: 'Rascunho',
  }

  return (
    <div
      style={{
        padding: '9px 12px',
        background: 'var(--glass)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--r)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600 }}>{routine.name}</div>
          {routine.description && (
            <div style={{ fontSize: 11, color: 'var(--mu)', marginTop: 2 }}>{routine.description}</div>
          )}
        </div>
        <span
          style={{
            fontSize: 10,
            color: statusColor[routine.status] ?? 'var(--mu)',
            background: 'rgba(0,0,0,.25)',
            borderRadius: 4,
            padding: '2px 6px',
          }}
        >
          {statusLabel[routine.status] ?? routine.status}
        </span>
        {routine.created_by_ai && (
          <span style={{ fontSize: 10, color: '#818cf8', background: 'rgba(129,140,248,.12)', borderRadius: 4, padding: '2px 6px' }}>
            ✦ IA
          </span>
        )}
      </div>
      <div style={{ marginTop: 7, fontSize: 11, color: 'var(--mu)' }}>
        {routine.steps.length} passo{routine.steps.length !== 1 ? 's' : ''} · gatilho: {routine.trigger_type}
      </div>
      {(routine.status === 'draft') && (
        <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
          <button
            className="btn bp"
            style={{ fontSize: 10.5, padding: '4px 10px' }}
            onClick={() => onSubmit(routine.id, routine.name)}
          >
            Enviar para aprovação
          </button>
          <button
            className="btn bs"
            style={{ fontSize: 10.5, padding: '4px 10px' }}
            onClick={() => onDelete(routine.id)}
          >
            Excluir
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Quick routine builder ────────────────────────────────────────────────────

function QuickBuilder({
  domain,
  clientId,
  onCreated,
  onCancel,
}: {
  domain: string
  clientId: string
  onCreated: () => void
  onCancel: () => void
}) {
  const qc = useQueryClient()
  const { data: actions = [] } = useQuery({
    queryKey: ['agent-actions'],
    queryFn: () => fetchAgentActions(),
    staleTime: 300_000,
  })

  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [triggerType, setTriggerType] = useState<'manual' | 'document' | 'schedule'>('manual')
  const [steps, setSteps] = useState<RoutineStep[]>([{ step: 1, agent: '', action: '', output: undefined }])

  const createMut = useMutation({
    mutationFn: () =>
      createCustomRoutine(clientId, {
        name,
        description: desc || undefined,
        steps: steps.filter(s => s.agent && s.action),
        trigger_type: triggerType,
        created_by_ai: false,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['custom-routines', domain, clientId] })
      onCreated()
    },
  })

  const addStep = () =>
    setSteps(s => [...s, { step: s.length + 1, agent: '', action: '', output: undefined }])

  const removeStep = (i: number) =>
    setSteps(s => s.filter((_, idx) => idx !== i).map((st, idx) => ({ ...st, step: idx + 1 })))

  const updateStep = (i: number, field: keyof RoutineStep, value: string) =>
    setSteps(s => s.map((st, idx) => (idx === i ? { ...st, [field]: value || undefined } : st)))


  return (
    <div
      style={{
        background: 'var(--glass)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--r)',
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ fontSize: 12.5, fontWeight: 600 }}>Nova Rotina</div>

      <input
        placeholder="Nome da rotina *"
        value={name}
        onChange={e => setName(e.target.value)}
        style={{
          background: 'rgba(0,0,0,.3)',
          border: '1px solid var(--gb)',
          borderRadius: 5,
          padding: '6px 10px',
          fontSize: 12,
          color: 'inherit',
          fontFamily: 'var(--mono)',
        }}
      />
      <input
        placeholder="Descrição (opcional)"
        value={desc}
        onChange={e => setDesc(e.target.value)}
        style={{
          background: 'rgba(0,0,0,.3)',
          border: '1px solid var(--gb)',
          borderRadius: 5,
          padding: '6px 10px',
          fontSize: 12,
          color: 'inherit',
          fontFamily: 'var(--mono)',
        }}
      />

      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: 'var(--mu)' }}>Gatilho:</span>
        {(['manual', 'document', 'schedule'] as const).map(t => (
          <span
            key={t}
            className={`pill${triggerType === t ? ' on' : ''}`}
            style={{ cursor: 'pointer' }}
            onClick={() => setTriggerType(t)}
          >
            {t === 'manual' ? 'Manual' : t === 'document' ? 'Documento' : 'Agenda'}
          </span>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 11, color: 'var(--mu)', fontWeight: 600 }}>Passos</div>
        {steps.map((step, i) => (
          <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: 'var(--mu)', minWidth: 16 }}>{i + 1}.</span>
            <select
              value={step.agent}
              onChange={e => updateStep(i, 'agent', e.target.value)}
              style={{
                background: 'rgba(0,0,0,.3)',
                border: '1px solid var(--gb)',
                borderRadius: 5,
                padding: '4px 7px',
                fontSize: 11,
                color: 'inherit',
                flex: 1,
              }}
            >
              <option value="">Agente…</option>
              {[...new Set(actions.map(a => a.agent_slug))].map(slug => (
                <option key={slug} value={slug}>{slug}</option>
              ))}
            </select>
            <select
              value={step.action}
              onChange={e => updateStep(i, 'action', e.target.value)}
              style={{
                background: 'rgba(0,0,0,.3)',
                border: '1px solid var(--gb)',
                borderRadius: 5,
                padding: '4px 7px',
                fontSize: 11,
                color: 'inherit',
                flex: 2,
              }}
            >
              <option value="">Ação…</option>
              {actions
                .filter(a => !step.agent || a.agent_slug === step.agent)
                .map(a => (
                  <option key={a.id} value={a.id}>{a.label}</option>
                ))}
            </select>
            {steps.length > 1 && (
              <button
                className="btn bs"
                style={{ fontSize: 10, padding: '3px 7px' }}
                onClick={() => removeStep(i)}
              >
                ✕
              </button>
            )}
          </div>
        ))}
        <button
          className="btn bs"
          style={{ fontSize: 10.5, padding: '4px 10px', alignSelf: 'flex-start' }}
          onClick={addStep}
        >
          + Passo
        </button>
      </div>

      <div style={{ display: 'flex', gap: 7, marginTop: 2 }}>
        <button
          className="btn bp"
          style={{ fontSize: 11, padding: '5px 12px' }}
          disabled={!name.trim() || steps.filter(s => s.agent && s.action).length === 0 || createMut.isPending}
          onClick={() => createMut.mutate()}
        >
          {createMut.isPending ? 'Salvando…' : 'Salvar como rascunho'}
        </button>
        <button
          className="btn bs"
          style={{ fontSize: 11, padding: '5px 12px' }}
          onClick={onCancel}
        >
          Cancelar
        </button>
      </div>
      {createMut.isError && (
        <div style={{ fontSize: 11, color: 'var(--urg)' }}>Erro ao salvar. Tente novamente.</div>
      )}
    </div>
  )
}

// ─── Main panel ───────────────────────────────────────────────────────────────

export default function RoutinesPanel({ domain }: { domain: string }) {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [showBuilder, setShowBuilder] = useState(false)

  const { data: catalogRoutines = [], isLoading: catalogLoading } = useQuery({
    queryKey: ['routines', domain, clientId ?? ''],
    queryFn: () => fetchRoutines(clientId!, domain),
    enabled: !!clientId,
    staleTime: 120_000,
  })

  const { data: customRoutines = [], isLoading: customLoading } = useQuery({
    queryKey: ['custom-routines', domain, clientId ?? ''],
    queryFn: () => fetchCustomRoutines(clientId!, domain),
    enabled: !!clientId,
    staleTime: 120_000,
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      toggleRoutine(id, clientId!, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['routines', domain, clientId ?? ''] }),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteCustomRoutine(id, clientId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['custom-routines', domain, clientId ?? ''] }),
  })

  const submitMut = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      submitRoutineForApproval(clientId!, id, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['custom-routines', domain, clientId ?? ''] }),
  })

  const isLoading = catalogLoading || customLoading

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
      {/* Catalog routines */}
      <div style={{ fontSize: 11, color: 'var(--mu)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Rotinas do Catálogo
      </div>
      {isLoading && (
        <div style={{ color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
      )}
      {!isLoading && catalogRoutines.length === 0 && (
        <div style={{ fontSize: 11.5, color: 'var(--mu)' }}>Nenhuma rotina de catálogo disponível para este domínio.</div>
      )}
      {catalogRoutines.map(r => (
        <CatalogRoutineRow
          key={r.id}
          routine={r}
          onToggle={(id, enabled) => toggleMut.mutate({ id, enabled })}
        />
      ))}

      {/* Custom routines */}
      <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ fontSize: 11, color: 'var(--mu)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', flex: 1 }}>
          Rotinas Personalizadas
        </div>
        {!showBuilder && (
          <button
            className="btn bp"
            style={{ fontSize: 10.5, padding: '4px 10px' }}
            onClick={() => setShowBuilder(true)}
          >
            + Nova
          </button>
        )}
      </div>

      {showBuilder && (
        <QuickBuilder
          domain={domain}
          clientId={clientId!}
          onCreated={() => setShowBuilder(false)}
          onCancel={() => setShowBuilder(false)}
        />
      )}

      {customRoutines.length === 0 && !showBuilder && (
        <div style={{ fontSize: 11.5, color: 'var(--mu)' }}>
          Crie rotinas personalizadas para automatizar processos específicos do seu negócio.
        </div>
      )}
      {customRoutines.map(r => (
        <CustomRoutineRow
          key={r.id}
          routine={r}
          onDelete={id => deleteMut.mutate(id)}
          onSubmit={(id, name) => submitMut.mutate({ id, name })}
        />
      ))}
    </div>
  )
}
