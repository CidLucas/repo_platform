import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchRoutines,
  fetchCustomRoutines,
  fetchRoutineCatalog,
  toggleRoutine,
  updateRoutineTrigger,
  createCustomRoutine,
  deleteCustomRoutine,
  submitRoutineForApproval,
  type ClientRoutine,
  type CustomRoutine,
  type RoutineStep,
} from '../../api/routines'
import Toggle from './Toggle'

// ─── Trigger configurator ─────────────────────────────────────────────────────

const DAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'] as const
const EVENTS = [
  { value: 'onboarding_completed', label: 'Onboarding concluído' },
  { value: 'new_integration', label: 'Nova integração conectada' },
  { value: 'monthly_close', label: 'Fechamento do mês' },
  { value: 'document_created', label: 'Documento criado' },
] as const

function buildCronExpression(days: number[], hour: number, minute: number): string {
  const d = days.length === 7 ? '*' : days.join(',')
  return `${minute} ${hour} * * ${d}`
}

function parseCronExpression(expr: string): { days: number[]; hour: number; minute: number } {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return { days: [1], hour: 9, minute: 0 }
  const [min, hr, , , dow] = parts
  const days = dow === '*' ? [0, 1, 2, 3, 4, 5, 6] : dow.split(',').map(Number)
  return { days, hour: parseInt(hr, 10) || 9, minute: parseInt(min, 10) || 0 }
}

function TriggerConfigurator({
  routine,
  clientId,
  domain,
  onClose,
}: {
  routine: ClientRoutine
  clientId: string
  domain: string
  onClose: () => void
}) {
  const qc = useQueryClient()

  const catalogTrigger = routine.cross_agent_routines?.trigger_type ?? 'manual'
  const effectiveTriggerType = routine.trigger_type || catalogTrigger
  const effectiveTriggerConfig = routine.trigger_config || routine.cross_agent_routines?.trigger_config || {}

  const [triggerType, setTriggerType] = useState<ClientRoutine['trigger_type']>(
    effectiveTriggerType as ClientRoutine['trigger_type']
  )

  const defaultExpr = (effectiveTriggerConfig as Record<string, string>).expression || '0 9 * * 1'
  const parsed = parseCronExpression(defaultExpr)
  const [days, setDays] = useState<number[]>(parsed.days)
  const [hour, setHour] = useState(parsed.hour)
  const [minute, setMinute] = useState(parsed.minute)
  const [eventType, setEventType] = useState<string>(
    (effectiveTriggerConfig as Record<string, string>).event_type || EVENTS[0].value
  )

  const saveMut = useMutation({
    mutationFn: () => {
      let cfg: Record<string, unknown> = {}
      if (triggerType === 'schedule') {
        cfg = { expression: buildCronExpression(days, hour, minute) }
      } else if (triggerType === 'event') {
        cfg = { event_type: eventType }
      }
      return updateRoutineTrigger(routine.id, clientId, triggerType, cfg)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['routines', domain, clientId] })
      onClose()
    },
  })

  const toggleDay = (d: number) =>
    setDays(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d].sort((a, b) => a - b))

  const inputStyle = {
    background: 'rgba(0,0,0,.3)',
    border: '1px solid var(--gb)',
    borderRadius: 5,
    padding: '4px 8px',
    fontSize: 11,
    color: 'inherit',
    fontFamily: 'var(--mono)',
  } as const

  return (
    <div
      style={{
        background: 'rgba(0,0,0,.2)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--r)',
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 9,
        marginTop: 6,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Configurar Gatilho
      </div>

      {/* Trigger type selector */}
      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
        {(['manual', 'schedule', 'event'] as const).map(t => (
          <span
            key={t}
            className={`pill${triggerType === t ? ' on' : ''}`}
            style={{ cursor: 'pointer', fontSize: 10.5 }}
            onClick={() => setTriggerType(t)}
          >
            {t === 'manual' ? 'Manual' : t === 'schedule' ? 'Agenda' : 'Evento'}
          </span>
        ))}
      </div>

      {/* Schedule config */}
      {triggerType === 'schedule' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
          <div style={{ display: 'flex', gap: 4 }}>
            {DAYS.map((label, i) => (
              <div
                key={i}
                onClick={() => toggleDay(i)}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 14,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 9.5,
                  cursor: 'pointer',
                  background: days.includes(i) ? 'var(--accent)' : 'rgba(0,0,0,.3)',
                  color: days.includes(i) ? '#fff' : 'var(--mu)',
                  border: '1px solid var(--gb)',
                  transition: 'background .15s',
                }}
              >
                {label}
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 7, alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--mu)' }}>Hora:</span>
            <select value={hour} onChange={e => setHour(Number(e.target.value))} style={inputStyle}>
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>{String(i).padStart(2, '0')}h</option>
              ))}
            </select>
            <select value={minute} onChange={e => setMinute(Number(e.target.value))} style={inputStyle}>
              {[0, 15, 30, 45].map(m => (
                <option key={m} value={m}>{String(m).padStart(2, '0')}min</option>
              ))}
            </select>
          </div>
          <div style={{ fontSize: 10, color: 'var(--mu)', fontFamily: 'var(--mono)' }}>
            cron: {buildCronExpression(days, hour, minute)}
          </div>
        </div>
      )}

      {/* Event config */}
      {triggerType === 'event' && (
        <select value={eventType} onChange={e => setEventType(e.target.value)} style={inputStyle}>
          {EVENTS.map(ev => (
            <option key={ev.value} value={ev.value}>{ev.label}</option>
          ))}
        </select>
      )}

      {triggerType === 'manual' && (
        <div style={{ fontSize: 11, color: 'var(--mu)' }}>
          Execute manualmente pelo painel de controle.
        </div>
      )}

      <div style={{ display: 'flex', gap: 7 }}>
        <button
          className="btn bp"
          style={{ fontSize: 10.5, padding: '4px 10px' }}
          disabled={saveMut.isPending}
          onClick={() => saveMut.mutate()}
        >
          {saveMut.isPending ? 'Salvando…' : 'Salvar'}
        </button>
        <button
          className="btn bs"
          style={{ fontSize: 10.5, padding: '4px 10px' }}
          onClick={onClose}
        >
          Cancelar
        </button>
      </div>
      {saveMut.isError && (
        <div style={{ fontSize: 11, color: 'var(--urg)' }}>Erro ao salvar. Tente novamente.</div>
      )}
    </div>
  )
}

// ─── Catalog routine row ──────────────────────────────────────────────────────

function CatalogRoutineRow({
  routine,
  clientId,
  domain,
  onToggle,
}: {
  routine: ClientRoutine
  clientId: string
  domain: string
  onToggle: (id: string, enabled: boolean) => void
}) {
  const [showConfig, setShowConfig] = useState(false)
  const isActive = routine.active && routine.status === 'active'
  const name = routine.cross_agent_routines?.name ?? routine.routine_id
  const triggerLabel: Record<string, string> = {
    manual: 'manual',
    schedule: 'agenda',
    event: 'evento',
    numeric: 'métrica',
    cron: 'agenda',
  }
  const effectiveTrigger = routine.trigger_type || routine.cross_agent_routines?.trigger_type || 'manual'

  return (
    <div
      style={{
        background: 'var(--glass)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--r)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '9px 12px',
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600 }}>{name}</div>
          <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 2, display: 'flex', gap: 8 }}>
            <span>{routine.routine_id}</span>
            <span
              style={{ cursor: 'pointer', textDecoration: 'underline', color: 'var(--accent)' }}
              onClick={() => setShowConfig(v => !v)}
            >
              {triggerLabel[effectiveTrigger] ?? effectiveTrigger} ↳ configurar
            </span>
          </div>
        </div>
        <Toggle
          checked={isActive}
          onChange={v => onToggle(routine.id, v)}
        />
      </div>
      {showConfig && (
        <div style={{ padding: '0 12px 12px' }}>
          <TriggerConfigurator
            routine={routine}
            clientId={clientId}
            domain={domain}
            onClose={() => setShowConfig(false)}
          />
        </div>
      )}
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
  const { data: catalog = { functions: [], artifacts: [], skills: [], triggers: [], skill_slugs: [] } } = useQuery({
    queryKey: ['routine-catalog'],
    queryFn: () => fetchRoutineCatalog(),
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
              {catalog.skill_slugs.map(slug => (
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
              <optgroup label="Functions">
                {catalog.functions.map(f => (
                  <option key={f.id} value={f.id}>{f.label}</option>
                ))}
              </optgroup>
              <optgroup label="Artifacts">
                {catalog.artifacts.map(a => (
                  <option key={a.id} value={a.id}>{a.label}</option>
                ))}
              </optgroup>
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
          clientId={clientId!}
          domain={domain}
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
