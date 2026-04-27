import React from 'react';
import { Select, type SelectProps } from '@chakra-ui/react';
import type { StandardPeriod } from '../services/analyticsService';

/**
 * Standardized period selector used across dimension pages (BLU-MVP-004 / K1.4).
 *
 * Supports the canonical period vocabulary: 7d | 30d | 90d | mtd | ytd | custom.
 * `custom` is exposed but the custom date range modal is a Phase 1 follow-up;
 * for now selecting it falls back to the default window in the RPC layer
 * (analytics_v2._resolve_period treats 'custom' as 30d).
 *
 * Backwards compatibility: PedidosPage and useDashboardIndicators still use
 * the legacy week|month|quarter|year vocabulary which the RPC layer also
 * accepts. New pages should use this component + StandardPeriod type.
 */

export interface PeriodOption {
  value: StandardPeriod;
  label: string;
}

export const STANDARD_PERIOD_OPTIONS: PeriodOption[] = [
  { value: '7d', label: 'Últimos 7 dias' },
  { value: '30d', label: 'Últimos 30 dias' },
  { value: '90d', label: 'Últimos 90 dias' },
  { value: 'mtd', label: 'Mês até hoje' },
  { value: 'ytd', label: 'Ano até hoje' },
  { value: 'custom', label: 'Período personalizado' },
];

export interface PeriodSelectorProps extends Omit<SelectProps, 'value' | 'onChange'> {
  value: StandardPeriod;
  onChange: (value: StandardPeriod) => void;
  /** Hide options not yet supported (e.g. 'custom' until the modal lands). */
  excludeOptions?: StandardPeriod[];
}

export const PeriodSelector: React.FC<PeriodSelectorProps> = ({
  value,
  onChange,
  excludeOptions = ['custom'],
  width = '180px',
  bg = 'white',
  ...rest
}) => {
  const options = STANDARD_PERIOD_OPTIONS.filter(o => !excludeOptions.includes(o.value));
  return (
    <Select
      value={value}
      onChange={(e) => onChange(e.target.value as StandardPeriod)}
      width={width}
      bg={bg}
      color="gray.800"
      {...rest}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </Select>
  );
};
