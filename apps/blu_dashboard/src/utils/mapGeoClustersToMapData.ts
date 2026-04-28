import type { GeoClustersResponse } from '../services/analyticsService';
import type { MapData } from '../types';

/**
 * Default map center when no clusters are present (geographic centroid of Brazil).
 */
const BRAZIL_CENTER: [number, number] = [-14.235, -51.9253];
const DEFAULT_ZOOM = 4.5;

/**
 * Convert a `GeoClustersResponse` into the `MapData` shape consumed by
 * `DashboardCard` / Leaflet wrapper. Used by
 * any future page rendering geo clusters so the
 * mapping stays consistent.
 */
export const mapGeoClustersToMapData = (
  geoClusters: GeoClustersResponse | null | undefined,
): MapData => ({
  center: geoClusters?.center ?? BRAZIL_CENTER,
  zoom: DEFAULT_ZOOM,
  clusters: geoClusters?.clusters ?? [],
  maxCount: geoClusters?.max_count ?? 1,
});
