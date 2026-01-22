import React from 'react';
import { LineChart, Line, XAxis, Tooltip } from 'recharts';
import { Box } from '@chakra-ui/react';

interface GraphComponentProps {
  data: any[];
  dataKey: string;
  lineColor?: string;
}

export const GraphComponent: React.FC<GraphComponentProps> = ({
  data,
  dataKey,
  lineColor = '#FFA500',
}) => {
  return (
    <Box width="100%" height="100%">
      <LineChart data={data} width={400} height={250} margin={{ top: 5, right: 40, left: 40, bottom: 5 }}>
        <XAxis
          dataKey="name"
          stroke="black"
          strokeWidth={3}
          tickFormatter={(value) => value.toUpperCase()}
          style={{
            fontSize: '14px',
            fontWeight: 400,
            fontFamily: 'Inter',
          }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: 'rgba(0,0,0,0.7)', border: 'none', borderRadius: '4px', fontFamily: 'Inter', fontSize: '14px' }}
          itemStyle={{ color: 'white', textTransform: 'uppercase' }}
          labelStyle={{ color: 'white', textTransform: 'uppercase' }}
        />
        <Line type="monotone" dataKey={dataKey} stroke={lineColor} strokeWidth={8} dot={false} />
      </LineChart>
    </Box>
  );
};
