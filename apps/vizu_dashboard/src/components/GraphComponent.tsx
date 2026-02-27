import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Box, Text } from '@chakra-ui/react';

interface ChartDataPoint {
  name?: string;
  data?: string;
  [key: string]: string | number | undefined;
}

interface GraphComponentProps {
  data: ChartDataPoint[];
  dataKey: string;
  lineColor?: string;
  showGrid?: boolean;
  height?: number | string;
  axisColor?: string;
}

export const GraphComponent: React.FC<GraphComponentProps> = ({
  data,
  dataKey,
  lineColor = '#FFA500',
  showGrid = false,
  height = 250,
  axisColor = '#333', // Default dark for light backgrounds
}) => {
  // DEBUG: Log incoming data
  console.log('📊 GraphComponent received:', { dataLength: data?.length, dataKey, sample: data?.[0] });

  // Validate data - ensure we have valid data points
  const validData = data?.filter(item => item && item.name !== undefined && item[dataKey] !== undefined) || [];
  console.log('📊 GraphComponent validData:', { validDataLength: validData.length, sample: validData[0] });

  if (validData.length === 0) {
    return (
      <Box width="100%" height={height} display="flex" alignItems="center" justifyContent="center">
        <Text color="gray.500" fontSize="sm">Sem dados para exibir</Text>
      </Box>
    );
  }

  // Format large numbers for better readability
  const formatYAxis = (value: number) => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
    return value.toFixed(0);
  };

  // Format tooltip values
  const formatTooltipValue = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      maximumFractionDigits: 2,
    }).format(value);
  };

  return (
    <Box width="100%" height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={validData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />}
          <XAxis
            dataKey="name"
            stroke={axisColor}
            strokeWidth={1}
            tickFormatter={(value) => {
              // Format month labels (e.g., "2023-01" -> "Jan/23")
              if (typeof value === 'string' && value.match(/^\d{4}-\d{2}$/)) {
                const [year, month] = value.split('-');
                const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                return `${months[parseInt(month, 10) - 1]}/${year.slice(2)}`;
              }
              return String(value).toUpperCase();
            }}
            tick={{ fontSize: 11, fontFamily: 'Inter', fill: axisColor }}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke={axisColor}
            tickFormatter={formatYAxis}
            tick={{ fontSize: 10, fontFamily: 'Inter', fill: axisColor }}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(0,0,0,0.85)',
              border: 'none',
              borderRadius: '8px',
              fontFamily: 'Inter',
              fontSize: '13px',
              padding: '10px 14px',
            }}
            itemStyle={{ color: 'white' }}
            labelStyle={{ color: 'white', fontWeight: 'bold', marginBottom: '4px' }}
            formatter={(value: number) => [formatTooltipValue(value), dataKey]}
            labelFormatter={(label) => {
              if (typeof label === 'string' && label.match(/^\d{4}-\d{2}$/)) {
                const [year, month] = label.split('-');
                const months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
                return `${months[parseInt(month, 10) - 1]} ${year}`;
              }
              return label;
            }}
          />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={lineColor}
            strokeWidth={3}
            dot={{ fill: lineColor, strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, fill: lineColor, stroke: 'white', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
};
