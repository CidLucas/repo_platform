import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchRoutines,
  fetchCustomRoutines,
  fetchRoutineCatalog,
  fetchRoutineConfig,
  upsertRoutineConfig,
  toggleRoutine,
  updateRoutineConfig,
  updateRoutineTrigger,
  createCustomRoutine,
  deleteCustomRoutine,
  submitRoutineForApproval,
  type ClientRoutine,
  type CustomRoutine,
  type CatalogStep,
  type ConfigSchemaField,
  type ActionDef,
  type SkillDef,
  type TriggerDef,
  type ActionParam,
} from '../../api/routines'
import RoutinePreviewCard from './RoutinePreviewCard'
import Toggle from './Toggle'

// ─── Trigger configurator ─────────────────────────────────────────────────────

const DAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'] as const

type ScheduleFreq = 'daily' | 'weekly' | 'monthly'

function detectFreq(days: number[], expr: string): ScheduleFreq {
  // If cron day-of-month field (position 2) is not '*' → monthly
  const parts = expr.trim().split(/\s+/)
  if (parts.length === 5 && parts[2] !== '*') return 'monthly'
  if (days.length === 7) return 'daily'
  return 'weekly'
}

function buildCronExpression(
  days: number[],
  hour: number,
  minute: number,
  freq: ScheduleFreq,
  monthDay: number,
): string {
  if (freq === 'daily') return `${minute} ${hour} * * *`
  if (freq === 'monthly') return `${minute} ${hour} ${monthDay} * *`
  const d = days.length === 7 ? '*' : days.join(',')
  return `${minute} ${hour} * * ${d}`
}

function parseCronExpression(expr: string) {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return { days: [1], hour: 9, minute: 0, monthDay: 1 }
  const [min, hr, dom, , dow] = parts
  const days = dow === '*' ? [0, 1, 2, 3, 4, 5, 6] : dow.split(',').map(Number)
  return {
    days,
    hour: parseInt(hr, 10) || 9,
    minute: parseInt(min, 10) || 0,
    monthDay: dom !== '*' ? parseInt(dom, 10) || 1 : 1,
  }
}

// ─── Schema field renderer ────────────────────────────────────────────────────

function DictField({
  field, value, onChange,
}: {
  field: ConfigSchemaField
  value: unknown
  onChange: (v: unknown) => void
}) {
  const maxEntries = field.max_entries ?? 3
  const current: Record<string, string> =
    value && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, string>)
      : {}

  const entries = Object.entries(current)
  const remaining = maxEntries - entries.length

  const updateKey = (oldKey: string, newKey: string) => {
    const updated: Record<string, string> = {}
    for (const [k, v] of Object.entries(current)) {
      updated[k === oldKey ? newKey : k] = v
    }
    onChange(updated)
  }

  const updateValue = (key: string, val: string) => {
    onChange({ ...current, [key]: val })
  }

  const addEntry = () => {
    if (entries.length >= maxEntries) return
    onChange({ ...current, '': '' })
  }

  const removeEntry = (key: string) => {
    const updated = { ...current }
    delete updated[key]
    onChange(updated)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <span style={{ fontSize: 11, color: 'var(--mu)' }}>{field.label}</span>
      {entries.map(([key, val], i) => (
        <div key={i} style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          <input
            type="text"
            className="input"
            placeholder="Nome"
            value={key}
            onChange={e => updateKey(key, e.target.value)}
            style={{ flex: 1 }}
          />
          <input
            type="text"
            className="input"
            placeholder="https://..."
            value={val}
            onChange={e => updateValue(key, e.target.value)}
            style={{ flex: 2 }}
          />
          <button
            className="btn bs"
            style={{ fontSize: 9.5, padding: '2px 6px' }}
            onClick={() => removeEntry(key)}
          >✕</button>
        </div>
      ))}
      {remaining > 0 && (
        <button
          className="btn bs"
          style={{ fontSize: 10, padding: '3px 8px', alignSelf: 'flex-start' }}
          onClick={addEntry}
        >
          + Adicionar ({entries.length}/{maxEntries})
        </button>
      )}
    </div>
  )
}

function SchemaField({
  field, value, onChange,
}: {
  field: ConfigSchemaField
  value: unknown
  onChange: (v: unknown) => void
}) {
  const current = value ?? field.default

  if (field.type === 'dict') {
    return <DictField field={field} value={value} onChange={onChange} />
  }

  if (field.type === 'boolean') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>{field.label}</span>
        <Toggle checked={Boolean(current)} onChange={v => onChange(v)} />
      </div>
    )
  }

  if (field.type === 'select' && field.options) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>{field.label}</span>
        <select className="input" value={String(current ?? '')} onChange={e => onChange(e.target.value)}>
          {field.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
    )
  }

  if (field.type === 'number') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>{field.label}</span>
        <input
          type="number"
          className="input"
          value={String(current ?? '')}
          onChange={e => onChange(Number(e.target.value))}
          style={{ width: 70 }}
        />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>{field.label}</span>
      <input
        type="text"
        className="input"
        value={String(current ?? '')}
        onChange={e => onChange(e.target.value)}
        style={{ flex: 1, maxWidth: 160 }}
      />
    </div>
  )
}

// ─── Built-in routine row ─────────────────────────────────────────────────────

const SCHEDULE_HOURS = [6, 7, 8, 9, 10, 12, 18, 20]

function BuiltInRoutineRow({
  routine, clientId, domain,
  onToggle,
}: {
  routine: ClientRoutine
  clientId: string
  domain: string
  onToggle: (id: string, enabled: boolean) => void
}) {
  const qc = useQueryClient()
  const [showMore, setShowMore] = useState(false)

  const cat = routine.cross_agent_routines
  const name = cat?.name ?? routine.routine_id
  const isActive = routine.active && routine.status === 'active'
  const configSchema: ConfigSchemaField[] = cat?.config_schema ?? []

  // Use catalog trigger_type when the client row still has the default 'manual'.
  // This ensures schedule pills render for cron routines before the client has
  // explicitly saved a trigger override.
  const effectiveTriggerType =
    (routine.trigger_type === 'manual' ? cat?.trigger_type : routine.trigger_type) ||
    cat?.trigger_type ||
    'manual'
  const effectiveTriggerConfig = routine.trigger_config || cat?.trigger_config || {}
  const isSchedule = effectiveTriggerType === 'schedule' || effectiveTriggerType === 'cron'

  // Config schema: pills for select ≤4 options, everything else in "mais"
  const inlinePillFields = configSchema.filter(
    f => f.type === 'select' && f.options && f.options.length <= 4
  )
  const remainingFields = configSchema.filter(f => !inlinePillFields.includes(f))

  const [configDraft, setConfigDraft] = useState<Record<string, unknown>>(routine.config ?? {})

  const defaultExpr = (effectiveTriggerConfig as Record<string, string>).expression || '0 9 * * 1'
  const parsed = parseCronExpression(defaultExpr)
  const [days, setDays] = useState<number[]>(parsed.days)
  const [hour, setHour] = useState(parsed.hour)
  const [monthDay, setMonthDay] = useState(parsed.monthDay)
  const [freq, setFreq] = useState<ScheduleFreq>(() => detectFreq(parsed.days, defaultExpr))

  const configMut = useMutation({
    mutationFn: (cfg: Record<string, unknown>) => updateRoutineConfig(routine.id, clientId, cfg),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['routines', domain, clientId] }),
  })

  const triggerMut = useMutation({
    mutationFn: ({ d, h, f, md }: { d: number[]; h: number; f: ScheduleFreq; md: number }) =>
      updateRoutineTrigger(
        routine.id, clientId,
        effectiveTriggerType as ClientRoutine['trigger_type'],
        { expression: buildCronExpression(d, h, 0, f, md) }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['routines', domain, clientId] }),
  })

  const toggleDay = (i: number) => {
    const newDays = days.includes(i)
      ? days.filter(x => x !== i)
      : [...days, i].sort((a, b) => a - b)
    setDays(newDays)
    triggerMut.mutate({ d: newDays, h: hour, f: freq, md: monthDay })
  }

  const selectHour = (h: number) => {
    setHour(h)
    triggerMut.mutate({ d: days, h, f: freq, md: monthDay })
  }

  const selectFreq = (f: ScheduleFreq) => {
    setFreq(f)
    triggerMut.mutate({ d: days, h: hour, f, md: monthDay })
  }

  const selectMonthDay = (md: number) => {
    setMonthDay(md)
    triggerMut.mutate({ d: days, h: hour, f: freq, md })
  }

  const handlePillClick = (fieldKey: string, value: string) => {
    const newCfg = { ...configDraft, [fieldKey]: value }
    setConfigDraft(newCfg)
    configMut.mutate(newCfg)
  }

  return (
    <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>

      {/* Header: name + toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, flex: 1, minWidth: 0 }}>{name}</div>
        <Toggle
          checked={isActive}
          onChange={v => onToggle(routine.id, v)}
        />
      </div>

      {/* Schedule trigger: frequency + day + hour pills */}
      {isSchedule && (() => {
        const MONTH_DAYS = Array.from({ length: 28 }, (_, i) => i + 1)
        return (
          <>
            {/* Frequência */}
            <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 10, marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Frequência
            </div>
            <div style={{ display: 'flex', gap: 4 }}>
              {(['daily', 'weekly', 'monthly'] as ScheduleFreq[]).map(f => (
                <span
                  key={f}
                  className={`pill${freq === f ? ' on' : ''}`}
                  style={{ cursor: 'pointer', fontSize: 10 }}
                  onClick={() => selectFreq(f)}
                >
                  {f === 'daily' ? 'Diário' : f === 'weekly' ? 'Semanal' : 'Mensal'}
                </span>
              ))}
            </div>

            {/* Dias da semana — só para semanal */}
            {freq === 'weekly' && (
              <>
                <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 8, marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Dias
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {DAYS.map((label, i) => (
                    <span
                      key={i}
                      className={`pill${days.includes(i) ? ' on' : ''}`}
                      style={{ cursor: 'pointer', fontSize: 10 }}
                      onClick={() => toggleDay(i)}
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </>
            )}

            {/* Dia do mês — só para mensal */}
            {freq === 'monthly' && (
              <>
                <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 8, marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Dia do mês
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {MONTH_DAYS.map(d => (
                    <span
                      key={d}
                      className={`pill${monthDay === d ? ' on' : ''}`}
                      style={{ cursor: 'pointer', fontSize: 10, minWidth: 22, textAlign: 'center' }}
                      onClick={() => selectMonthDay(d)}
                    >
                      {d}
                    </span>
                  ))}
                </div>
              </>
            )}

            <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 8, marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Hora
            </div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {SCHEDULE_HOURS.map(h => (
                <span
                  key={h}
                  className={`pill${hour === h ? ' on' : ''}`}
                  style={{ cursor: 'pointer', fontSize: 10 }}
                  onClick={() => selectHour(h)}
                >
                  {String(h).padStart(2, '0')}:00
                </span>
              ))}
            </div>
            {triggerMut.isPending && (
              <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 5 }}>Salvando…</div>
            )}
          </>
        )
      })()}

      {/* Non-schedule: show trigger type as badge */}
      {!isSchedule && (
        <div style={{ marginTop: 7, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span className="pill" style={{ fontSize: 10, cursor: 'default' }}>
            {effectiveTriggerType === 'manual' ? 'Manual'
              : effectiveTriggerType === 'event' ? 'Evento'
              : effectiveTriggerType === 'numeric' ? 'Monitoramento'
              : effectiveTriggerType}
          </span>
          {effectiveTriggerType === 'numeric' && typeof (effectiveTriggerConfig as Record<string, unknown>).metric === 'string' && (
            <span style={{ fontSize: 10, color: 'var(--mu)' }}>
              ↳ {String((effectiveTriggerConfig as Record<string, unknown>).metric ?? '').replace(/_/g, ' ')}
            </span>
          )}
        </div>
      )}

      {/* Config schema inline pills */}
      {inlinePillFields.map(field => {
        const currentVal = configDraft[field.key] ?? field.default
        return (
          <div key={field.key} style={{ marginTop: 9 }}>
            <div style={{ fontSize: 10, color: 'var(--mu)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {field.label}
            </div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {field.options!.map(opt => (
                <span
                  key={opt.value}
                  className={`pill${currentVal === opt.value ? ' on' : ''}`}
                  style={{ cursor: 'pointer', fontSize: 10.5 }}
                  onClick={() => handlePillClick(field.key, opt.value)}
                >
                  {opt.label}
                </span>
              ))}
            </div>
          </div>
        )
      })}

      {/* Remaining complex config fields */}
      {remainingFields.length > 0 && (
        <>
          <div style={{ marginTop: 9 }}>
            <span
              style={{ fontSize: 10.5, cursor: 'pointer', color: 'var(--accent)', textDecoration: 'underline' }}
              onClick={() => setShowMore(v => !v)}
            >
              mais {showMore ? '▴' : '▾'}
            </span>
          </div>
          {showMore && (
            <div style={{ marginTop: 8, padding: '10px 12px', background: 'rgba(0,0,0,.15)', borderRadius: 6, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Parâmetros</div>
              {remainingFields.map(field => (
                <SchemaField
                  key={field.key}
                  field={field}
                  value={configDraft[field.key]}
                  onChange={v => setConfigDraft(d => ({ ...d, [field.key]: v }))}
                />
              ))}
              <div style={{ display: 'flex', gap: 7 }}>
                <button className="btn bp" style={{ fontSize: 10.5, padding: '4px 10px' }} disabled={configMut.isPending} onClick={() => configMut.mutate(configDraft)}>
                  {configMut.isPending ? 'Salvando…' : 'Salvar'}
                </button>
                <button className="btn bs" style={{ fontSize: 10.5, padding: '4px 10px' }} onClick={() => setShowMore(false)}>Fechar</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ─── Custom routine row ───────────────────────────────────────────────────────

function CustomRoutineRow({
  routine, onDelete, onPreview,
}: {
  routine: CustomRoutine
  onDelete: (id: string) => void
  onPreview: (routine: CustomRoutine) => void
}) {
  const statusColor: Record<string, string> = {
    active: 'var(--ok)', inactive: 'var(--mu)',
    pending_approval: 'var(--yellow)', draft: 'var(--mu)',
  }
  const statusLabel: Record<string, string> = {
    active: 'Ativa', inactive: 'Inativa',
    pending_approval: 'Aguardando aprovação', draft: 'Rascunho',
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '9px 0', borderBottom: '1px solid var(--gb)' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {routine.name}
          </span>
          {routine.created_by_ai && (
            <span style={{ fontSize: 9.5, color: 'var(--blue3)', background: 'rgba(129,140,248,.12)', borderRadius: 4, padding: '1px 5px', flexShrink: 0 }}>✦ IA</span>
          )}
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 2 }}>
          {routine.steps.length} passo{routine.steps.length !== 1 ? 's' : ''} · {routine.trigger_type}
        </div>
      </div>

      <span style={{ fontSize: 10, color: statusColor[routine.status] ?? 'var(--mu)', background: 'rgba(0,0,0,.25)', borderRadius: 4, padding: '2px 6px', flexShrink: 0 }}>
        {statusLabel[routine.status] ?? routine.status}
      </span>

      {routine.status === 'draft' && (
        <>
          <button className="btn bp" style={{ fontSize: 10, padding: '3px 8px' }} onClick={() => onPreview(routine)}>
            Revisar →
          </button>
          <button className="btn bs" style={{ fontSize: 10, padding: '3px 8px' }} onClick={() => onDelete(routine.id)}>
            ✕
          </button>
        </>
      )}
    </div>
  )
}

// ─── Quick builder (manual) ───────────────────────────────────────────────────

type StepType = 'function' | 'skill' | 'artifact'

interface BuilderStep {
  _id: string
  step: number
  type: StepType
  label: string
  on_failure: 'halt' | 'continue'
  // function / artifact
  fn: string
  inputs: Record<string, string>
  // skill
  skill_slug: string
  task_template: string
  output_key: string
}

function makeStep(n: number): BuilderStep {
  return {
    _id: `${Date.now()}_${n}`,
    step: n,
    type: 'function',
    label: '',
    on_failure: 'halt',
    fn: '',
    inputs: {},
    skill_slug: '',
    task_template: '',
    output_key: 'result',
  }
}

function toStep(s: BuilderStep): CatalogStep {
  const base: CatalogStep = {
    step: s.step,
    id: `step_${s.step}`,
    type: s.type,
    label: s.label || undefined,
    on_failure: s.on_failure,
  }
  if (s.type === 'skill') {
    return {
      ...base,
      skill_slug: s.skill_slug,
      task_template: s.task_template,
      outputs: s.output_key ? { [s.output_key]: 'output do agente' } : undefined,
    }
  }
  return {
    ...base,
    function: s.fn,
    inputs: Object.keys(s.inputs).length ? s.inputs : undefined,
  }
}

// Trigger configurator for QuickBuilder

function TriggerConfig({
  triggerType,
  triggerConfig,
  triggers,
  onChange,
}: {
  triggerType: string
  triggerConfig: Record<string, string>
  triggers: TriggerDef[]
  onChange: (type: string, cfg: Record<string, string>) => void
}) {
  const def = triggers.find(t => t.id === triggerType)
  if (!def || def.config_schema.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 7, padding: '10px 12px', background: 'rgba(0,0,0,.15)', borderRadius: 6 }}>
      {def.config_schema.map(field => {
        const val = triggerConfig[field.key] ?? String(field.default ?? '')
        if (field.type === 'select' && field.options) {
          return (
            <div key={field.key} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{field.key}</span>
              <div style={{ fontSize: 9.5, color: 'var(--mu)', marginBottom: 2, fontStyle: 'italic' }}>{field.description}</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {field.options.map(opt => (
                  <span
                    key={opt.value}
                    className={`pill${val === opt.value ? ' on' : ''}`}
                    style={{ cursor: 'pointer', fontSize: 10 }}
                    onClick={() => onChange(triggerType, { ...triggerConfig, [field.key]: opt.value })}
                  >
                    {opt.label}
                  </span>
                ))}
              </div>
            </div>
          )
        }
        return (
          <div key={field.key} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <span style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {field.key}{field.required ? ' *' : ''}
            </span>
            <div style={{ fontSize: 9.5, color: 'var(--mu)', marginBottom: 2, fontStyle: 'italic' }}>{field.description}</div>
            <input
              type={field.type === 'int' || field.type === 'float' ? 'number' : 'text'}
              className="input"
              value={val}
              placeholder={String(field.default ?? '')}
              onChange={e => onChange(triggerType, { ...triggerConfig, [field.key]: e.target.value })}
              style={{ width: '100%' }}
            />
          </div>
        )
      })}
    </div>
  )
}

// Inputs panel for function/artifact steps

function InputsPanel({
  params,
  values,
  onChange,
}: {
  params: ActionParam[]
  values: Record<string, string>
  onChange: (v: Record<string, string>) => void
}) {
  if (params.length === 0) {
    return <div style={{ fontSize: 10, color: 'var(--mu)', fontStyle: 'italic' }}>Nenhum input necessário.</div>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {params.map(p => (
        <div key={p.key} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
            <span style={{ fontSize: 10, color: 'var(--mu)', fontFamily: 'var(--mono)' }}>{p.key}</span>
            <span style={{ fontSize: 9, color: 'var(--mu)', opacity: 0.6 }}>{p.type}{p.required ? ' *' : ''}</span>
          </div>
          <div style={{ fontSize: 9.5, color: 'var(--mu)', fontStyle: 'italic', marginBottom: 2 }}>{p.description}</div>
          <input
            type="text"
            className="input"
            value={values[p.key] ?? String(p.default ?? '')}
            placeholder={p.default != null ? String(p.default) : `{{${p.key}}}`}
            onChange={e => onChange({ ...values, [p.key]: e.target.value })}
            style={{ width: '100%' }}
          />
        </div>
      ))}
    </div>
  )
}

// Step card

function StepCard({
  step,
  functions,
  artifacts,
  skills,
  onChange,
  onRemove,
  canRemove,
}: {
  step: BuilderStep
  functions: ActionDef[]
  artifacts: ActionDef[]
  skills: SkillDef[]
  onChange: (s: BuilderStep) => void
  onRemove: () => void
  canRemove: boolean
}) {
  const up = (patch: Partial<BuilderStep>) => onChange({ ...step, ...patch })

  const selectedFn = step.type === 'function'
    ? functions.find(f => f.id === step.fn)
    : step.type === 'artifact'
    ? artifacts.find(a => a.id === step.fn)
    : null

  const selectedSkill = skills.find(s => s.id === step.skill_slug)

  return (
    <div style={{ background: 'rgba(0,0,0,.18)', border: '1px solid var(--gb)', borderRadius: 6, padding: '10px 11px', display: 'flex', flexDirection: 'column', gap: 8 }}>

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 10, color: 'var(--mu)', minWidth: 18, fontFamily: 'var(--mono)' }}>{step.step}.</span>
        <input
          className="input"
          placeholder="Rótulo (opcional)"
          value={step.label}
          onChange={e => up({ label: e.target.value })}
          style={{ flex: 1 }}
        />
        {canRemove && (
          <button className="btn bs" style={{ fontSize: 10, padding: '2px 7px' }} onClick={onRemove}>✕</button>
        )}
      </div>

      {/* Type selector */}
      <div style={{ display: 'flex', gap: 4 }}>
        {(['function', 'skill', 'artifact'] as StepType[]).map(t => (
          <span
            key={t}
            className={`pill${step.type === t ? ' on' : ''}`}
            style={{ cursor: 'pointer', fontSize: 10 }}
            onClick={() => up({ type: t, fn: '', skill_slug: '', inputs: {} })}
          >
            {t === 'function' ? 'Função' : t === 'skill' ? 'Agente IA' : 'Ação'}
          </span>
        ))}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 4, alignItems: 'center' }}>
          <span style={{ fontSize: 9.5, color: 'var(--mu)' }}>falha:</span>
          {(['halt', 'continue'] as const).map(v => (
            <span
              key={v}
              className={`pill${step.on_failure === v ? ' on' : ''}`}
              style={{ cursor: 'pointer', fontSize: 9.5 }}
              onClick={() => up({ on_failure: v })}
            >
              {v === 'halt' ? 'parar' : 'continuar'}
            </span>
          ))}
        </span>
      </div>

      {/* Function step */}
      {step.type === 'function' && (
        <>
          <select
            className="input"
            value={step.fn}
            onChange={e => up({ fn: e.target.value, inputs: {} })}
          >
            <option value="">Selecione uma função…</option>
            {functions.map(f => (
              <option key={f.id} value={f.id}>{f.label}</option>
            ))}
          </select>
          {selectedFn && (
            <div style={{ fontSize: 10, color: 'var(--mu)', fontStyle: 'italic', lineHeight: 1.4 }}>{selectedFn.description}</div>
          )}
          {selectedFn && selectedFn.inputs.length > 0 && (
            <>
              <div style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Inputs</div>
              <InputsPanel params={selectedFn.inputs} values={step.inputs} onChange={inputs => up({ inputs })} />
            </>
          )}
          {selectedFn && selectedFn.outputs.length > 0 && (
            <div style={{ fontSize: 9.5, color: 'var(--mu)', lineHeight: 1.5 }}>
              <span style={{ fontWeight: 600 }}>Gera: </span>
              {selectedFn.outputs.map(o => (
                <span key={o.key} style={{ fontFamily: 'var(--mono)', background: 'rgba(255,255,255,.07)', padding: '0 4px', borderRadius: 3, marginRight: 4 }}>
                  {`{{${o.key}}}`}
                </span>
              ))}
            </div>
          )}
        </>
      )}

      {/* Skill (AI agent / L3 skill) step */}
      {step.type === 'skill' && (
        <>
          <select
            className="input"
            value={step.skill_slug}
            onChange={e => up({ skill_slug: e.target.value })}
          >
            <option value="">Selecione um agente ou skill…</option>
            <optgroup label="Agentes">
              {skills.filter(s => s.kind !== 'l3_skill').map(s => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </optgroup>
            <optgroup label="Skills narrativas (L3)">
              {skills.filter(s => s.kind === 'l3_skill').map(s => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </optgroup>
          </select>
          {selectedSkill && (
            <div style={{ fontSize: 10, color: 'var(--mu)', fontStyle: 'italic', lineHeight: 1.4 }}>{selectedSkill.description}</div>
          )}
          <div style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tarefa</div>
          <textarea
            className="input"
            value={step.task_template}
            onChange={e => up({ task_template: e.target.value })}
            placeholder="Descreva o que o agente deve fazer. Use {{chave}} para referenciar saídas de passos anteriores."
            rows={4}
            style={{ width: '100%', resize: 'vertical', lineHeight: 1.5 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 10, color: 'var(--mu)', whiteSpace: 'nowrap' }}>Salvar resultado em:</span>
            <input
              className="input"
              value={step.output_key}
              onChange={e => up({ output_key: e.target.value })}
              placeholder="chave (ex: insights)"
              style={{ flex: 1, fontFamily: 'var(--mono)' }}
            />
          </div>
          {step.output_key && (
            <div style={{ fontSize: 9.5, color: 'var(--mu)' }}>
              Próximos passos podem usar{' '}
              <span style={{ fontFamily: 'var(--mono)', background: 'rgba(255,255,255,.07)', padding: '0 4px', borderRadius: 3 }}>
                {`{{${step.output_key}}}`}
              </span>
            </div>
          )}
        </>
      )}

      {/* Artifact step */}
      {step.type === 'artifact' && (
        <>
          <select
            className="input"
            value={step.fn}
            onChange={e => up({ fn: e.target.value, inputs: {} })}
          >
            <option value="">Selecione uma ação…</option>
            {artifacts.map(a => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
          {selectedFn && (
            <div style={{ fontSize: 10, color: 'var(--mu)', fontStyle: 'italic', lineHeight: 1.4 }}>{selectedFn.description}</div>
          )}
          {selectedFn && selectedFn.inputs.length > 0 && (
            <>
              <div style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Inputs</div>
              <InputsPanel params={selectedFn.inputs} values={step.inputs} onChange={inputs => up({ inputs })} />
            </>
          )}
        </>
      )}
    </div>
  )
}

// Static fallback — trigger types are stable and don't need a live API response
const STATIC_TRIGGERS: TriggerDef[] = [
  {
    id: 'manual',
    label: 'Manual',
    description: 'Disparada sob demanda a partir do painel ou do chat.',
    config_schema: [],
  },
  {
    id: 'schedule',
    label: 'Agendada',
    description: 'Executa automaticamente em horários definidos (cron).',
    config_schema: [
      { key: 'expression', type: 'str', description: 'Expressão cron (ex: 0 9 * * 1 = segunda às 9h)', required: true },
    ],
  },
  {
    id: 'event',
    label: 'Evento',
    description: 'Dispara quando um evento específico ocorre na plataforma.',
    config_schema: [
      {
        key: 'event_type',
        type: 'select',
        description: 'Tipo de evento que dispara a rotina',
        required: true,
        options: [
          { value: 'ingestion_completed', label: 'Ingestão de dados concluída' },
          { value: 'onboarding_completed', label: 'Onboarding do cliente concluído' },
          { value: 'monthly_close', label: 'Fechamento mensal' },
          { value: 'new_integration', label: 'Nova integração conectada' },
          { value: 'document_created', label: 'Documento criado' },
        ],
      },
      { key: 'cooldown_hours', type: 'int', description: 'Intervalo mínimo entre execuções (horas)', default: 1, required: false },
    ],
  },
  {
    id: 'numeric',
    label: 'Monitoramento',
    description: 'Dispara quando uma métrica ultrapassa um limite definido.',
    config_schema: [
      { key: 'metric', type: 'str', description: 'Métrica monitorada (ex: new_clients_monthly_rate)', required: true },
      { key: 'threshold', type: 'float', description: 'Valor limite que dispara a rotina', required: true },
      { key: 'window_months', type: 'int', description: 'Janela de avaliação em meses', default: 1, required: false },
      { key: 'cooldown_hours', type: 'int', description: 'Intervalo mínimo entre execuções (horas)', default: 24, required: false },
    ],
  },
]

function QuickBuilder({
  clientId,
  onCreated, onCancel,
}: {
  clientId: string
  onCreated: (routine: CustomRoutine) => void
  onCancel: () => void
}) {
  const { data: catalog } = useQuery({
    queryKey: ['routine-catalog'],
    queryFn: () => fetchRoutineCatalog(),
    staleTime: 300_000,
  })

  const functions: ActionDef[] = catalog?.functions ?? []
  const artifacts: ActionDef[] = catalog?.artifacts ?? []
  // Merge agent-executor skills + L3 narrative skills into one list for the builder
  const skills: SkillDef[] = [
    ...(catalog?.skills ?? []),
    ...(catalog?.l3_skills ?? []),
  ]
  const triggers: TriggerDef[] = catalog?.triggers?.length ? catalog.triggers : STATIC_TRIGGERS

  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [triggerType, setTriggerType] = useState('manual')
  const [triggerConfig, setTriggerConfig] = useState<Record<string, string>>({})
  const [steps, setSteps] = useState<BuilderStep[]>([makeStep(1)])

  const createMut = useMutation({
    mutationFn: () => createCustomRoutine(clientId, {
      name,
      description: desc || undefined,
      steps: steps.filter(isStepValid).map(toStep),
      trigger_type: triggerType as CustomRoutine['trigger_type'],
      trigger_config: triggerConfig,
      created_by_ai: false,
    }),
    onSuccess: data => onCreated(data),
  })

  const addStep = () => setSteps(s => [...s, makeStep(s.length + 1)])
  const removeStep = (id: string) => setSteps(s =>
    s.filter(x => x._id !== id).map((x, i) => ({ ...x, step: i + 1 }))
  )
  const updateStep = (id: string, updated: BuilderStep) =>
    setSteps(s => s.map(x => x._id === id ? updated : x))

  const validSteps = steps.filter(isStepValid)
  const canSave = name.trim().length > 0 && validSteps.length > 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 600 }}>Nova rotina</div>

      <input className="input" placeholder="Nome *" value={name} onChange={e => setName(e.target.value)} />
      <input className="input" placeholder="Descrição (opcional)" value={desc} onChange={e => setDesc(e.target.value)} />

      {/* Trigger */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Gatilho</div>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {triggers.map(t => (
            <span
              key={t.id}
              className={`pill${triggerType === t.id ? ' on' : ''}`}
              style={{ cursor: 'pointer', fontSize: 10 }}
              onClick={() => { setTriggerType(t.id); setTriggerConfig({}) }}
              title={t.description}
            >
              {t.label}
            </span>
          ))}
        </div>
        {triggers.find(t => t.id === triggerType)?.description && (
          <div style={{ fontSize: 10, color: 'var(--mu)', fontStyle: 'italic' }}>
            {triggers.find(t => t.id === triggerType)!.description}
          </div>
        )}
        <TriggerConfig
          triggerType={triggerType}
          triggerConfig={triggerConfig}
          triggers={triggers}
          onChange={(type, cfg) => { setTriggerType(type); setTriggerConfig(cfg) }}
        />
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Passos</div>
        {steps.map(s => (
          <StepCard
            key={s._id}
            step={s}
            functions={functions}
            artifacts={artifacts}
            skills={skills}
            onChange={updated => updateStep(s._id, updated)}
            onRemove={() => removeStep(s._id)}
            canRemove={steps.length > 1}
          />
        ))}
        <button className="btn bs" style={{ fontSize: 10.5, padding: '4px 10px', alignSelf: 'flex-start' }} onClick={addStep}>
          + Passo
        </button>
      </div>

      <div style={{ display: 'flex', gap: 7 }}>
        <button
          className="btn bp"
          style={{ fontSize: 11, padding: '5px 12px' }}
          disabled={!canSave || createMut.isPending}
          onClick={() => createMut.mutate()}
        >
          {createMut.isPending ? 'Salvando…' : 'Continuar →'}
        </button>
        <button className="btn bs" style={{ fontSize: 11, padding: '5px 12px' }} onClick={onCancel}>Cancelar</button>
      </div>
      {createMut.isError && <div style={{ fontSize: 11, color: 'var(--urg)' }}>Erro ao salvar. Tente novamente.</div>}
    </div>
  )
}

function isStepValid(s: BuilderStep): boolean {
  if (s.type === 'skill') return s.skill_slug.length > 0 && s.task_template.length > 0
  return s.fn.length > 0
}

// ─── Global config panel ──────────────────────────────────────────────────────

const NOTIFICATION_CHANNELS = [
  { value: 'email', label: 'Email' },
  { value: 'slack', label: 'Slack' },
  { value: 'in_app', label: 'In-app' },
  { value: 'none', label: 'Nenhum' },
] as const

const HOURS_00_23 = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))

function GlobalConfigPanel({ domain }: { domain: string }) {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [open, setOpen] = useState(true)

  const { data: serverConfig } = useQuery({
    queryKey: ['routine-global-config', domain, clientId ?? ''],
    queryFn: () => fetchRoutineConfig(clientId!, domain),
    enabled: !!clientId,
    staleTime: 120_000,
  })

  const [localConfig, setLocalConfig] = useState<Record<string, unknown>>({})
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    if (!hydrated && serverConfig !== undefined) {
      setLocalConfig(serverConfig)
      setHydrated(true)
    }
  }, [serverConfig, hydrated])

  const saveMut = useMutation({
    mutationFn: (cfg: Record<string, unknown>) => upsertRoutineConfig(clientId!, domain, cfg),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['routine-global-config', domain, clientId ?? ''] }),
  })

  const get = (key: string, fallback: unknown) => localConfig[key] ?? fallback

  const update = (key: string, value: unknown) =>
    setLocalConfig(prev => ({ ...prev, [key]: value }))

  const trackHistory = Boolean(get('track_execution_history', false))

  return (
    <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', marginBottom: 14 }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '9px 12px', cursor: 'pointer',
          borderBottom: open ? '1px solid var(--gb)' : 'none',
        }}
      >
        <span style={{ fontSize: 10.5, color: 'var(--mu)', width: 10, display: 'inline-block' }}>
          {open ? '▾' : '▸'}
        </span>
        <span style={{ fontSize: 11.5, fontWeight: 600, flex: 1 }}>Configurações globais</span>
      </div>

      {open && (
        <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 9 }}>
          {/* notification_channel */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>Canal de notificação</span>
            <select
              className="input"
              value={String(get('notification_channel', 'email'))}
              onChange={e => update('notification_channel', e.target.value)}
            >
              {NOTIFICATION_CHANNELS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* execution_window_start */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>Janela de execução — início</span>
            <select
              className="input"
              value={String(get('execution_window_start', '00'))}
              onChange={e => update('execution_window_start', e.target.value)}
            >
              {HOURS_00_23.map(h => <option key={h} value={h}>{h}</option>)}
            </select>
          </div>

          {/* execution_window_end */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>Janela de execução — fim</span>
            <select
              className="input"
              value={String(get('execution_window_end', '23'))}
              onChange={e => update('execution_window_end', e.target.value)}
            >
              {HOURS_00_23.map(h => <option key={h} value={h}>{h}</option>)}
            </select>
          </div>

          {/* max_parallel_routines */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>Máx. rotinas paralelas</span>
            <input
              type="number"
              className="input"
              min={1}
              value={String(get('max_parallel_routines', 3))}
              onChange={e => update('max_parallel_routines', Number(e.target.value))}
              style={{ width: 70 }}
            />
          </div>

          {/* track_execution_history */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>Registrar histórico de execução</span>
            <Toggle checked={trackHistory} onChange={v => update('track_execution_history', v)} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
            <button
              className="btn bp"
              style={{ fontSize: 10.5, padding: '4px 10px' }}
              disabled={saveMut.isPending}
              onClick={() => saveMut.mutate(localConfig)}
            >
              {saveMut.isPending ? 'Salvando...' : 'Salvar'}
            </button>
            {saveMut.isError && (
              <span style={{ fontSize: 10.5, color: 'var(--urg)' }}>Erro ao salvar.</span>
            )}
            {saveMut.isSuccess && !saveMut.isPending && (
              <span style={{ fontSize: 10.5, color: 'var(--ok)' }}>Salvo.</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main RoutineConfigSection ────────────────────────────────────────────────

type CreateMode = 'ai' | 'manual' | null

export default function RoutineConfigSection({ domain }: { domain: string }) {
  const { clientId } = useAuth()
  const qc = useQueryClient()

  const [createMode, setCreateMode] = useState<CreateMode>(null)
  const [previewRoutine, setPreviewRoutine] = useState<CustomRoutine | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const { data: catalogRoutines = [], isLoading: catalogLoading } = useQuery({
    queryKey: ['routines', domain, clientId ?? ''],
    queryFn: () => fetchRoutines(clientId!, domain),
    enabled: !!clientId,
    staleTime: 120_000,
  })

  const { data: customRoutines = [], isLoading: customLoading } = useQuery({
    queryKey: ['custom-routines', domain, clientId ?? ''],
    queryFn: () => fetchCustomRoutines(clientId!),
    enabled: !!clientId,
    staleTime: 120_000,
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => toggleRoutine(id, clientId!, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['routines', domain, clientId ?? ''] }),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteCustomRoutine(id, clientId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['custom-routines', domain, clientId ?? ''] }),
  })

  async function handleSubmitForApproval() {
    if (!previewRoutine || !clientId) return
    setSubmitting(true)
    try {
      await submitRoutineForApproval(clientId, previewRoutine.id, previewRoutine.name, previewRoutine.steps)
      qc.invalidateQueries({ queryKey: ['custom-routines', domain, clientId] })
      setPreviewRoutine(null)
    } finally {
      setSubmitting(false)
    }
  }

  const isLoading = catalogLoading || customLoading

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>

      <GlobalConfigPanel domain={domain} />

      {/* ── Built-in routines ── */}
      <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 9 }}>
        Rotinas disponíveis
      </div>

      {isLoading && <div style={{ fontSize: 12, color: 'var(--mu)', padding: '8px 0' }}>Carregando…</div>}

      {!isLoading && catalogRoutines.length === 0 && (
        <div style={{ fontSize: 11.5, color: 'var(--mu)', padding: '8px 0', fontStyle: 'italic' }}>
          Nenhuma rotina disponível para este espaço ainda.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {catalogRoutines.map(r => (
          <BuiltInRoutineRow
            key={r.id}
            routine={r}
            clientId={clientId!}
            domain={domain}
            onToggle={(id, enabled) => toggleMut.mutate({ id, enabled })}
          />
        ))}
      </div>

      {/* ── Custom routines ── */}
      <div style={{ marginTop: 18, marginBottom: 9, display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.06em', flex: 1 }}>
          Minhas rotinas
        </div>
      </div>

      {customRoutines.length === 0 && !createMode && !previewRoutine && (
        <div style={{ fontSize: 11.5, color: 'var(--mu)', padding: '6px 0', fontStyle: 'italic' }}>
          Crie rotinas personalizadas para automatizar processos do seu negócio.
        </div>
      )}

      {/* Preview card (post-creation, pre-approval) */}
      {previewRoutine && (
        <div style={{ marginBottom: 10 }}>
          <RoutinePreviewCard
            name={previewRoutine.name}
            description={previewRoutine.description}
            triggerType={previewRoutine.trigger_type}
            triggerConfig={previewRoutine.trigger_config}
            steps={previewRoutine.steps}
            createdByAi={previewRoutine.created_by_ai}
            submitting={submitting}
            onEdit={() => setPreviewRoutine(null)}
            onSubmit={handleSubmitForApproval}
          />
        </div>
      )}

      {/* Existing custom routines */}
      {!previewRoutine && customRoutines.map(r => (
        <CustomRoutineRow
          key={r.id}
          routine={r}
          onDelete={id => deleteMut.mutate(id)}
          onPreview={setPreviewRoutine}
        />
      ))}

      {/* Quick builder (manual mode) */}
      {createMode === 'manual' && !previewRoutine && (
        <div style={{ marginTop: 8, padding: '12px', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)' }}>
          <QuickBuilder
            clientId={clientId!}
            onCreated={routine => { setCreateMode(null); setPreviewRoutine(routine) }}
            onCancel={() => setCreateMode(null)}
          />
        </div>
      )}

      {/* AI creation hint */}
      {createMode === 'ai' && !previewRoutine && (
        <div style={{ marginTop: 8, padding: '12px', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', fontSize: 11.5, color: 'var(--mu)', lineHeight: 1.6 }}>
          💬 Abra o chat e diga ao Blu o que você quer automatizar. Exemplo: <em>"Quero criar uma rotina que toda segunda verifica meu estoque e faz um pedido automático de café quando estiver baixo."</em>
          <div style={{ marginTop: 8 }}>
            <button className="btn bs" style={{ fontSize: 10.5, padding: '4px 10px' }} onClick={() => setCreateMode(null)}>Fechar</button>
          </div>
        </div>
      )}

      {/* Create buttons */}
      {!createMode && !previewRoutine && (
        <div style={{ marginTop: 10, display: 'flex', gap: 7 }}>
          <button className="btn bp" style={{ fontSize: 10.5, padding: '5px 12px' }} onClick={() => setCreateMode('ai')}>
            ✦ Criar com IA
          </button>
          <button className="btn bs" style={{ fontSize: 10.5, padding: '5px 12px' }} onClick={() => setCreateMode('manual')}>
            + Manual
          </button>
        </div>
      )}
    </div>
  )
}
