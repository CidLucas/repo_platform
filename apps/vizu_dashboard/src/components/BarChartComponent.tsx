import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Box, Text } from '@chakra-ui/react';

interface BarChartComponentProps {
  // Accept optional values since upstream data may not always include value;
  // runtime filtering removes undefined entries.
  data: { name: string; value?: number; color?: string }[];
  dataKey?: string;
  height?: number | string;
  axisColor?: string;
  showLabels?: boolean;
  colors?: string[]; // Array of colors for each bar
}

// Default tier colors
const DEFAULT_COLORS = ['#4CAF50', '#FFC107', '#FF5722', '#2196F3']; // Green, Yellow, Orange, Blue

export const BarChartComponent: React.FC<BarChartComponentProps> = ({
  data,
  dataKey = 'value',
  height = 200,
  axisColor = '#333',
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- reserved for future use
  showLabels: _showLabels = true,
  colors = DEFAULT_COLORS,
}) => {
  // Validate data
  const validData = data?.filter(item => item && item.name !== undefined && item[dataKey as keyof typeof item] !== undefined) || [];

  if (validData.length === 0) {
    return (
      <Box width="100%" height={height} display="flex" alignItems="center" justifyContent="center">
        <Text color="gray.500" fontSize="sm">Sem dados para exibir</Text>
      </Box>
    );
  }

  // Format tooltip values
  const formatTooltipValue = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <Box width="100%" height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={validData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
          <XAxis
            dataKey="name"
            stroke={axisColor}
            tick={{ fontSize: 11, fontFamily: 'Inter', fill: axisColor }}
            tickLine={false}
            axisLine={{ stroke: axisColor, strokeOpacity: 0.3 }}
          />
          <YAxis
            stroke={axisColor}
            tick={{ fontSize: 10, fontFamily: 'Inter', fill: axisColor }}
            tickLine={false}
            axisLine={false}
            width={35}
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
            formatter={(value: number) => [formatTooltipValue(value), 'Fornecedores']}
          />
          <Bar dataKey={dataKey} radius={[4, 4, 0, 0]}>
            {validData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || colors[index % colors.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );
};
