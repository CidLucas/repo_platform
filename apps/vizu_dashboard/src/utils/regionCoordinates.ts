export interface RegionCoordinates {
  lat: number;
  lng: number;
}

export const BRAZIL_REGION_COORDS: Record<string, RegionCoordinates> = {
  'São Paulo': { lat: -23.5505, lng: -46.6333 },
  'Rio de Janeiro': { lat: -22.9068, lng: -43.1729 },
  'Minas Gerais': { lat: -19.9167, lng: -43.9345 },
  'Bahia': { lat: -12.9714, lng: -38.5014 },
  'Paraná': { lat: -25.4284, lng: -49.2733 },
  'Rio Grande do Sul': { lat: -30.0346, lng: -51.2177 },
  'Santa Catarina': { lat: -27.5954, lng: -48.548 },
  'Goiás': { lat: -16.6869, lng: -49.2648 },
  'Pernambuco': { lat: -8.0476, lng: -34.877 },
  'Ceará': { lat: -3.7172, lng: -38.5433 },
  'Pará': { lat: -1.4558, lng: -48.4902 },
  'Maranhão': { lat: -2.5387, lng: -44.2825 },
  'Amazonas': { lat: -3.119, lng: -60.0217 },
  'Mato Grosso': { lat: -15.601, lng: -56.0974 },
  'Mato Grosso do Sul': { lat: -20.4428, lng: -54.6462 },
  'Espírito Santo': { lat: -20.3155, lng: -40.3128 },
  'Paraíba': { lat: -7.1195, lng: -34.845 },
  'Rio Grande do Norte': { lat: -5.7945, lng: -35.211 },
  'Alagoas': { lat: -9.6658, lng: -35.735 },
  'Sergipe': { lat: -10.9472, lng: -37.0731 },
  'Piauí': { lat: -5.0892, lng: -42.8016 },
  'Tocantins': { lat: -10.1753, lng: -48.2982 },
  'Rondônia': { lat: -8.7612, lng: -63.9004 },
  'Acre': { lat: -9.0238, lng: -70.812 },
  'Amapá': { lat: 0.9019, lng: -51.9653 },
  'Roraima': { lat: 2.8235, lng: -60.6758 },
  'Distrito Federal': { lat: -15.7939, lng: -47.8828 },
};

export const DEFAULT_BRAZIL_CENTER: RegionCoordinates = {
  lat: -14.235,
  lng: -51.9253,
};

export function getRegionCoordinates(regionName: string): RegionCoordinates {
  return BRAZIL_REGION_COORDS[regionName] || DEFAULT_BRAZIL_CENTER;
}
