import { describe, expect, it } from 'vitest';

import {
  ORDER_STATUS_BUCKETS,
  summarizeOrderStatusBreakdown,
} from './analyticsService';

describe('summarizeOrderStatusBreakdown', () => {
  it('returns zeroed summary for null/empty input', () => {
    expect(summarizeOrderStatusBreakdown(null)).toEqual({
      completed: 0,
      pending: 0,
      other: 0,
      total: 0,
    });
    expect(summarizeOrderStatusBreakdown([])).toEqual({
      completed: 0,
      pending: 0,
      other: 0,
      total: 0,
    });
  });

  it('maps known statuses to correct buckets and sums total', () => {
    const summary = summarizeOrderStatusBreakdown([
      { status: 'valid', count: 5 },
      { status: 'completed', count: 2 },
      { status: 'review', count: 3 },
      { status: 'aguardando', count: 1 },
      { status: 'mystery_status', count: 4 },
    ]);
    expect(summary.completed).toBe(7);
    expect(summary.pending).toBe(4);
    expect(summary.other).toBe(4);
    expect(summary.total).toBe(15);
  });

  it('is case-insensitive on the status key', () => {
    const summary = summarizeOrderStatusBreakdown([
      { status: 'VALID', count: 3 },
      { status: 'Pending', count: 2 },
    ]);
    expect(summary.completed).toBe(3);
    expect(summary.pending).toBe(2);
    expect(summary.other).toBe(0);
  });

  it('classifies all known bucket keys without leaking to other', () => {
    for (const [status, expected] of Object.entries(ORDER_STATUS_BUCKETS)) {
      const summary = summarizeOrderStatusBreakdown([{ status, count: 1 }]);
      expect(summary[expected]).toBe(1);
      expect(summary.total).toBe(1);
    }
  });
});
