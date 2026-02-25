/**
 * Shared TypeScript types for the Vizu Dashboard
 */

// =============================================================================
// Chart/Graph Types
// =============================================================================

/** Standard data point for line and bar charts */
export interface ChartDataPoint {
  name: string;
  value: number;
  color?: string;
}

/** Time series data point with date */
export interface TimeSeriesDataPoint {
  data: string; // ISO date string
  [key: string]: string | number;
}

/** Graph configuration for carousel */
export interface GraphConfig {
  data: ChartDataPoint[] | TimeSeriesDataPoint[];
  dataKey: string;
  lineColor?: string;
  title: string;
  description?: string;
  chartType?: 'line' | 'bar';
  barColors?: string[];
}

// =============================================================================
// Map Types
// =============================================================================

export interface MapMarker {
  position: [number, number];
  popupText: string;
}

export interface MapData {
  center: [number, number];
  zoom: number;
  markers: MapMarker[];
}

// =============================================================================
// Dashboard Card Types
// =============================================================================

export interface InsightBullet {
  text: string;
  type: 'positive' | 'negative' | 'neutral' | 'warning' | 'star';
  detail?: string;
}

export interface KpiItem {
  label: string;
  content: React.ReactNode;
}

// =============================================================================
// Pedido Modal Types (display format - transformed from PedidoDetailResponse)
// =============================================================================

export interface PedidoModalData {
  id: string;
  clientName: string;
  status: string;
  quantidadeItens: string;
  valorUnitario: string;
  frete: string;
  valorTotal: string;
  enderecoEntrega: string;
  cnpjFaturamento: string;
  descricaoProdutos: string;
  mapData?: MapData;
}

// =============================================================================
// Generic Types
// =============================================================================

/** Generic record with string keys */
export type StringRecord = Record<string, string>;

/** Generic callback type */
export type VoidCallback = () => void;
