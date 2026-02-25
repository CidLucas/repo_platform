import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useEffect } from 'react';

// Fix for default icon issue with Webpack/Vite
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
});

interface GeoCluster {
  location: string;
  count: number;
  total_revenue: number;
  coordinates: [number, number];
}

interface MapComponentProps {
  center?: [number, number];
  zoom?: number;
  clusters?: GeoCluster[];
  maxCount?: number;
}

// Component to handle map centering after initial render
const MapCenterController: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();

  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);

  return null;
};

export const MapComponent: React.FC<MapComponentProps> = ({
  center = [-14.2350, -51.9253], // Default to Brazil center
  zoom = 7,
  clusters = [],
  maxCount = 1,
}) => {
  // Calculate circle radius based on count (proportional to square root for better visual)
  const getRadius = (count: number): number => {
    const minRadius = 10;
    const maxRadius = 50;
    const normalized = Math.sqrt(count / maxCount);
    return minRadius + (maxRadius - minRadius) * normalized;
  };

  // Color scale from light to dark blue based on revenue
  const getColor = (revenue: number): string => {
    const maxRevenue = Math.max(...clusters.map(c => c.total_revenue), 1);
    const normalized = revenue / maxRevenue;

    if (normalized > 0.75) return '#1e40af'; // dark blue
    if (normalized > 0.5) return '#3b82f6';  // blue
    if (normalized > 0.25) return '#60a5fa'; // light blue
    return '#93c5fd'; // very light blue
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <MapContainer
      center={center}
      zoom={zoom}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom={true}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        maxZoom={18}
      />
      <MapCenterController center={center} zoom={zoom} />

      {clusters.map((cluster, index) => (
        <CircleMarker
          key={index}
          center={cluster.coordinates}
          radius={getRadius(cluster.count)}
          pathOptions={{
            fillColor: getColor(cluster.total_revenue),
            fillOpacity: 0.6,
            color: '#1e3a8a',
            weight: 2,
          }}
        >
          <Popup>
            <div style={{ minWidth: '180px' }}>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: 'bold' }}>
                {cluster.location}
              </h3>
              <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
                <p style={{ margin: '4px 0' }}>
                  <strong>Clientes:</strong> {cluster.count.toLocaleString('pt-BR')}
                </p>
                <p style={{ margin: '4px 0' }}>
                  <strong>Receita Total:</strong> {formatCurrency(cluster.total_revenue)}
                </p>
                <p style={{ margin: '4px 0' }}>
                  <strong>Ticket Médio:</strong> {formatCurrency(cluster.total_revenue / cluster.count)}
                </p>
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
};
