import { useState } from 'react';

export type AnalyticsPeriod = '7d' | '30d' | '90d' | '1y' | 'all';

export interface UseAnalyticsPeriodReturn {
  period: AnalyticsPeriod;
  setPeriod: (period: AnalyticsPeriod) => void;
  periodDays: number;
}

export const useAnalyticsPeriod = (): UseAnalyticsPeriodReturn => {
  const [period, setPeriod] = useState<AnalyticsPeriod>('30d');

  const getPeriodDays = (): number => {
    switch (period) {
      case '7d':
        return 7;
      case '30d':
        return 30;
      case '90d':
        return 90;
      case '1y':
        return 365;
      case 'all':
        return 0; // 0 means no filter
      default:
        return 30;
    }
  };

  return {
    period,
    setPeriod,
    periodDays: getPeriodDays(),
  };
};
