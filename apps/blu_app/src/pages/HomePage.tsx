import { RoomContainer } from '@/components/layout/RoomContainer'
import { DecidirAgora } from '@/components/home/DecidirAgora'
import { PlanoDeHoje } from '@/components/home/PlanoDeHoje'
import { VisaoSemana } from '@/components/home/VisaoSemana'
import { InsightsPanel } from '@/components/home/InsightsPanel'
import { NumbersPanel } from '@/components/home/NumbersPanel'
import { AgentStatusRow } from '@/components/home/AgentStatusRow'

/**
 * Home — Command Center
 *
 * Mobile:   DecidirAgora → PlanoDeHoje → VisaoSemana → InsightsPanel → NumbersPanel
 * lg:       [DecidirAgora (2/3, max-520)] [PlanoDeHoje+VisaoSemana (1/3)]
 *           → InsightsPanel (full width below)
 * xl:       [DecidirAgora (1/3)] [PlanoDeHoje+VisaoSemana (1/3)] [Insights (1/3)]
 *
 * Grid trick:
 *   - 3-column grid on lg/xl
 *   - DecidirAgora: lg:col-span-2  xl:col-span-1
 *   - PlanoDeHoje+Visao: col-span-1 (both lg and xl)
 *   - InsightsPanel: lg:col-span-3  xl:col-span-1
 */
export function HomePage() {
  return (
    <RoomContainer className="space-y-6">
      {/* Agent status row — desktop only */}
      <AgentStatusRow />

      {/* Numbers bar — full width, collapsed accordion */}
      <NumbersPanel />

      {/* Responsive grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* DecidirAgora: 2 cols on lg, 1 col on xl */}
        <div className="lg:col-span-2 xl:col-span-1">
          <div className="xl:max-w-[520px]">
            <DecidirAgora />
          </div>
        </div>

        {/* PlanoDeHoje + VisaoSemana: always 1 col */}
        <div className="space-y-6">
          <PlanoDeHoje />
          <VisaoSemana />
        </div>

        {/* InsightsPanel: full width on lg, 1 col on xl */}
        <div className="lg:col-span-3 xl:col-span-1">
          <InsightsPanel />
        </div>
      </div>
    </RoomContainer>
  )
}
