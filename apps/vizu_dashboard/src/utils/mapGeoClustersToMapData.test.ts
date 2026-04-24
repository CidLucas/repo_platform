import { describe, expect, it } from 'vitest';

import type { GeoClustersResponse } from '../services/analyticsService';
import { mapGeoClustersToMapData } from './mapGeoClustersToMapData';

const sampleResponse: GeoClustersResponse = {
  clusters: [
    {
      location: 'SP',
      count: 12,
      total_revenue: 1000,
      coordinates: [-23.55, -46.63],
    },
    {
      location: 'RJ',
      count: 5,
      total_revenue: 500,
      coordinates: [-22.9, -43.2],
    },
  ],
  center: [-15.5, -47.0],
  max_count: 12,
  total_clusters: 2,
};

describe('mapGeoClustersToMapData', () => {
  it('falls back to Brazil center + zoom 4.5 when input is null', () => {
    const result = mapGeoClustersToMapData(null);
    expect(result.center).toEqual([-14.235, -51.9253]);
    expect(result.zoom).toBe(4.5);
    expect(result.clusters).toEqual([]);
    expect(result.maxCount).toBe(1);
  });

  it('falls back when input is undefined', () => {
    const result = mapGeoClustersToMapData(undefined);
    expect(result.clusters).toEqual([]);
    expect(result.maxCount).toBe(1);
  });

  it('forwards center, clusters and max_count from the response', () => {
    const result = mapGeoClustersToMapData(sampleResponse);
    expect(result.center).toEqual([-15.5, -47.0]);
    expect(result.maxCount).toBe(12);
    expect(result.clusters).toHaveLength(2);
    expect(result.clusters?.[0]?.location).toBe('SP');
    // zoom is constant for now — guard against accidental change.
    expect(result.zoom).toBe(4.5);
  });
});
