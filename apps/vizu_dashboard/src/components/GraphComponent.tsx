import React from 'react';
import { LineChart, Line, XAxis, Tooltip } from 'recharts'; // Removed ResponsiveContainer
import { Box } from '@chakra-ui/react';

interface GraphComponentProps {
  data: any[];
  dataKey: string;
  lineColor?: string;
}

export const GraphComponent: React.FC<GraphComponentProps> = ({
  data,
  dataKey,
  lineColor = '#FFA500', // Default to orange
}) => {
  return (
    <Box width="100%" height="100%">
      <LineChart data={data} width="100%" height={250} margin={{ top: 5, right: 40, left: 40, bottom: 5 }} padding={{ top: 150 }}> {/* Removed ResponsiveContainer, added padding */}
        {/* Removed CartesianGrid */}
        <XAxis
          dataKey="name"
          stroke="black" // Black stroke
          strokeWidth={3} // 3px thick
          tickFormatter={(value) => value.toUpperCase()} // Uppercase labels
          style={{
            fontSize: '14px',
            fontWeight: 400,
            fontFamily: 'Inter',
          }}
          // Removed y={300}
        />
        {/* Removed YAxis */}
        <Tooltip
          contentStyle={{ backgroundColor: 'rgba(0,0,0,0.7)', border: 'none', borderRadius: '4px', fontFamily: 'Inter', fontSize: '14px' }}
          itemStyle={{ color: 'white', textTransform: 'uppercase' }}
          labelStyle={{ color: 'white', textTransform: 'uppercase' }}
        />
        <Line type="monotone" dataKey={dataKey} stroke={lineColor} strokeWidth={8} dot={false} /> {/* Orange line, 8px thick */}
      </LineChart>
    </Box>
  );
};
