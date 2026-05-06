import { useState } from 'react'
import {
  AreaChart, Area,
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { cn } from '@/utils/cn'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { formatBRL } from '@/utils/format'
import type { TimeSeriesPoint } from '@/types/analytics'

type ChartTab = 'receita' | 'despesas' | 'fluxo'

const TABS: { label: string; value: ChartTab }[] = [
  { label: 'Receita', value: 'receita' },
  { label: 'Despesas', value: 'despesas' },
  { label: 'Fluxo de Caixa', value: 'fluxo' },
]

const TOOLTIP_STYLE = {
  backgroundColor: '#1A2A42',
  border: '1px solid #243552',
  borderRadius: '8px',
  color: '#F0F6FC',
  fontSize: '12px',
  lineHeight: '1.4',
}

function xFmt(val: string | number) {
  try {
    return new Date(String(val)).toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' })
  } catch {
    return String(val)
  }
}

function yFmt(val: string | number) {
  return formatBRL(Number(val))
}

interface ChartContainerProps {
  data?: TimeSeriesPoint[]
  loading?: boolean
  className?: string
}

export function ChartContainer({ data = [], loading, className }: ChartContainerProps) {
  const [tab, setTab] = useState<ChartTab>('receita')

  if (loading) {
    return <SkeletonCard lines={4} className={cn('h-52', className)} />
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Tab strip */}
      <div className="flex border-b border-border" role="tablist" aria-label="Tipo de gráfico">
        {TABS.map((t) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => setTab(t.value)}
            className={cn(
              'px-4 py-2 text-body-sm font-medium transition-colors duration-normal cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blu-500',
              tab === t.value
                ? 'text-white border-b-2 border-blu-500 -mb-px'
                : 'text-gray-400 hover:text-gray-200'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Chart area */}
      <div className="h-48 w-full" role="tabpanel">
        {data.length === 0 ? (
          <EmptyChart />
        ) : (
          <ChartInner tab={tab} data={data} />
        )}
      </div>
    </div>
  )
}

function ChartInner({ tab, data }: { tab: ChartTab; data: TimeSeriesPoint[] }) {
  if (tab === 'receita') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="receitaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#4A90D9" stopOpacity={0.22} />
              <stop offset="95%" stopColor="#4A90D9" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tickFormatter={xFmt}
            tick={{ fill: '#8B9AB0', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={yFmt}
            tick={{ fill: '#8B9AB0', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(val) => [formatBRL(val as number), 'Receita']}
            labelFormatter={xFmt as (label: unknown) => string}
            cursor={{ stroke: '#243552', strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="receita"
            stroke="#4A90D9"
            strokeWidth={2}
            fill="url(#receitaGrad)"
            dot={false}
            activeDot={{ r: 4, fill: '#4A90D9', stroke: '#1A2A42', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  if (tab === 'despesas') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="date"
            tickFormatter={xFmt}
            tick={{ fill: '#8B9AB0', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={yFmt}
            tick={{ fill: '#8B9AB0', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(val) => [formatBRL(val as number), 'Despesas']}
            labelFormatter={xFmt as (label: unknown) => string}
            cursor={{ fill: 'rgba(36,53,82,0.4)' }}
          />
          <Bar
            dataKey="despesas"
            fill="#E07A5F"
            fillOpacity={0.85}
            radius={[3, 3, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // Fluxo de Caixa
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <XAxis
          dataKey="date"
          tickFormatter={xFmt}
          tick={{ fill: '#8B9AB0', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={yFmt}
          tick={{ fill: '#8B9AB0', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={60}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(val, name) => [
            formatBRL(val as number),
            name === 'entrada' ? 'Entrada' : 'Saída',
          ]}
          labelFormatter={xFmt as (label: unknown) => string}
          cursor={{ stroke: '#243552', strokeWidth: 1 }}
        />
        <Line
          type="monotone"
          dataKey="entrada"
          stroke="#5FB8A3"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#5FB8A3', stroke: '#1A2A42', strokeWidth: 2 }}
        />
        <Line
          type="monotone"
          dataKey="saida"
          stroke="#E07A5F"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#E07A5F', stroke: '#1A2A42', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function EmptyChart() {
  return (
    <div className="h-full flex items-center justify-center">
      <p className="text-caption text-gray-500">Sem dados para o período selecionado</p>
    </div>
  )
}
