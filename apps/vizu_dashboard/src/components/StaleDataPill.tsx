import React from 'react';
import { Badge, Tooltip, Icon } from '@chakra-ui/react';
import { FiClock, FiAlertTriangle } from 'react-icons/fi';

/**
 * StaleDataPill — Phase 1 / K1.5 (BLU-MVP-022)
 *
 * Renders a "Última atualização: há X h" pill next to dimension KPI titles.
 * When the underlying source (MV, last sync, etc.) is older than `staleAfterHours`
 * (default 25h per roadmap §10), the pill turns warning-coloured.
 *
 * Pass `lastUpdatedAt` as an ISO string or Date. If null/undefined, the pill
 * is hidden (callers should render `<EmptyStateCard variant="disconnected" />`
 * when appropriate).
 */

export interface StaleDataPillProps {
  lastUpdatedAt: string | Date | null | undefined;
  staleAfterHours?: number;
  label?: string;
}

function formatRelative(deltaMs: number): string {
  const minutes = Math.floor(deltaMs / 60_000);
  if (minutes < 1) return 'agora';
  if (minutes < 60) return `há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `há ${hours} h`;
  const days = Math.floor(hours / 24);
  return `há ${days} d`;
}

export const StaleDataPill: React.FC<StaleDataPillProps> = ({
  lastUpdatedAt,
  staleAfterHours = 25,
  label = 'Última atualização',
}) => {
  if (!lastUpdatedAt) return null;
  const ts = lastUpdatedAt instanceof Date ? lastUpdatedAt : new Date(lastUpdatedAt);
  const ms = Date.now() - ts.getTime();
  if (!Number.isFinite(ms) || ms < 0) return null;

  const stale = ms > staleAfterHours * 3_600_000;
  const text = `${label}: ${formatRelative(ms)}`;

  return (
    <Tooltip label={ts.toLocaleString('pt-BR')} hasArrow>
      <Badge
        colorScheme={stale ? 'orange' : 'gray'}
        variant="subtle"
        display="inline-flex"
        alignItems="center"
        gap={1}
        px={2}
        py={0.5}
        borderRadius="full"
        fontWeight="medium"
        textTransform="none"
      >
        <Icon as={stale ? FiAlertTriangle : FiClock} boxSize={3} />
        {text}
      </Badge>
    </Tooltip>
  );
};
