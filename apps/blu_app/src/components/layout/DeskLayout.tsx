import { type ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { useDrawer } from '@/hooks/useDrawer'
import { LeftDrawer, LeftDrawerPill } from '@/components/drawers/LeftDrawer'
import { RightDrawer, RightDrawerPill } from '@/components/drawers/RightDrawer'
import { RightPanelCard } from '@/components/layout/RightPanelCard'
import { BackToLobby } from '@/components/navigation/BackToLobby'
import { RoomErrorBoundary } from './RoomErrorBoundary'
import { KnowledgeGapAlert } from '@/components/knowledge/KnowledgeGapAlert'
import type { AgentSlug } from '@/types/agent'

interface DeskLayoutProps {
  /** Page title shown in room header */
  title: string
  /** Subtitle / agent slug displayed under title */
  subtitle?: string
  /** Agent orb or icon displayed in the header */
  agentIcon?: ReactNode
  /** When provided, renders a KnowledgeGapAlert below the header if the agent is partial/blocked */
  agentSlug?: AgentSlug

  // ── Left drawer ──────────────────────────────────────────
  leftTitle?: string
  leftContent?: ReactNode
  leftPillLabel?: string
  leftPillIcon?: ReactNode
  leftHeaderActions?: ReactNode

  // ── Main desk surface (centre) ───────────────────────────
  children: ReactNode

  // ── Right drawer ─────────────────────────────────────────
  rightTitle?: string
  rightContent?: ReactNode
  rightPillLabel?: string
  rightPillIcon?: ReactNode
  rightHeaderActions?: ReactNode

  // ── Corkboard (full-width below desk) ───────────────────
  corkboard?: ReactNode

  // ── UnderDesk ────────────────────────────────────────────
  underDesk?: ReactNode

  /** Agent accent color — propagated to right panel cards */
  accentColor?: string

  className?: string
}

/**
 * Universal three-column room layout for all 6 agent rooms.
 *
 * Breakpoints:
 *   base (mobile)  → single column; drawers as bottom-sheet pills
 *   md (tablet)    → left drawer visible; right as pill
 *   lg (desktop)   → three columns (left 1/4 · desk 2/4 · right 1/4)
 *   xl (large)     → same, outer AgentNav already adds 240px from AppShell
 */
export function DeskLayout({
  title,
  subtitle,
  agentIcon,
  agentSlug,
  leftTitle = 'Painel',
  leftContent,
  leftPillLabel,
  leftPillIcon,
  leftHeaderActions,
  children,
  rightTitle = 'Histórico',
  rightContent,
  rightPillLabel,
  rightPillIcon,
  rightHeaderActions,
  corkboard,
  underDesk,
  accentColor,
  className,
}: DeskLayoutProps) {
  const drawer = useDrawer()

  return (
    <RoomErrorBoundary>
    <div className={cn('h-full pt-20 pb-4 flex flex-col', className)}>
      {/* ── Room header ──────────────────────────────────── */}
      <header className="px-4 mb-4">
        <BackToLobby className="mb-2" />
        <div className="flex items-center gap-3">
          {agentIcon && (
            <span className="shrink-0">{agentIcon}</span>
          )}
          <div>
            <h1 className="font-display text-display-md text-white leading-tight">{title}</h1>
            {subtitle && (
              <p className="text-caption text-gray-400">{subtitle}</p>
            )}
          </div>
        </div>
        {agentSlug && (
          <KnowledgeGapAlert agentSlug={agentSlug} className="mt-3" />
        )}
      </header>

      {/* ── Body ─────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left drawer — desktop panel hidden; mobile bottom sheet kept */}
        {leftContent && (
          <LeftDrawer
            title={leftTitle}
            mobileOpen={drawer.isLeftOpen}
            onMobileClose={drawer.close}
            headerActions={leftHeaderActions}
            showDesktopPanel={false}
          >
            {leftContent}
          </LeftDrawer>
        )}

        {/* Centre — 2/3 on desktop, full width on mobile */}
        <main className="flex-1 lg:flex-[2] min-h-0 overflow-y-auto scroll-container">
          <div className="max-w-7xl mx-auto px-4 space-y-4 py-2">
            {children}

            {corkboard && (
              <section>
                <p className="text-section-label mb-3">Insights</p>
                {corkboard}
              </section>
            )}

            {underDesk}
          </div>
        </main>

        {/* Right drawer — desktop panel hidden; mobile bottom sheet kept */}
        {rightContent && (
          <RightDrawer
            title={rightTitle}
            mobileOpen={drawer.isRightOpen}
            onMobileClose={drawer.close}
            headerActions={rightHeaderActions}
            showDesktopPanel={false}
          >
            {rightContent}
          </RightDrawer>
        )}

        {/* ── Desktop right sidebar (1/3): 2 stacked expandable cards ── */}
        {(leftContent || rightContent) && (
          <aside className="hidden lg:flex flex-col flex-[1] border-l border-border bg-gray-900 gap-3 p-3 overflow-y-auto">
            {leftContent && (
              <RightPanelCard title={leftTitle} headerActions={leftHeaderActions} accentColor={accentColor}>
                {leftContent}
              </RightPanelCard>
            )}
            {rightContent && (
              <RightPanelCard title={rightTitle} headerActions={rightHeaderActions} accentColor={accentColor}>
                {rightContent}
              </RightPanelCard>
            )}
          </aside>
        )}
      </div>

      {/* ── Mobile drawer pills (fixed at bottom) ────────── */}
      {(leftContent || rightContent) && (
        <div
          className={cn(
            'lg:hidden fixed bottom-0 left-0 right-0 z-raised',
            'flex items-center justify-center gap-3 px-4 pb-4 pt-2',
            'bg-gradient-to-t from-base via-base/90 to-transparent pointer-events-none'
          )}
        >
          <div className="flex items-center gap-3 pointer-events-auto">
            {leftContent && (
              <LeftDrawerPill
                label={leftPillLabel ?? leftTitle}
                icon={leftPillIcon}
                onClick={drawer.openLeft}
              />
            )}
            {rightContent && (
              <RightDrawerPill
                label={rightPillLabel ?? rightTitle}
                icon={rightPillIcon}
                onClick={drawer.openRight}
              />
            )}
          </div>
        </div>
      )}
    </div>
    </RoomErrorBoundary>
  )
}
