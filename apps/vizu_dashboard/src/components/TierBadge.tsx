import { Badge } from '@chakra-ui/react';
import React from 'react';

interface TierBadgeProps {
  tier: string; // "A", "B", "C", "D"
  size?: 'sm' | 'md' | 'lg';
}

const TIER_COLORS: Record<string, string> = {
  A: '#4CAF50', // Green
  B: '#FFC107', // Yellow
  C: '#FF9800', // Orange
  D: '#F44336', // Red
};

export const TierBadge: React.FC<TierBadgeProps> = ({ tier, size = 'md' }) => {
  const bgColor = TIER_COLORS[tier.toUpperCase()] || '#9E9E9E'; // Default gray

  const fontSize = {
    sm: '12px',
    md: '14px',
    lg: '16px',
  }[size];

  const padding = {
    sm: '4px 8px',
    md: '6px 12px',
    lg: '8px 16px',
  }[size];

  return (
    <Badge
      bg={bgColor}
      color="white"
      fontSize={fontSize}
      fontWeight="bold"
      borderRadius="8px"
      px={padding}
      textTransform="uppercase"
    >
      Tier {tier.toUpperCase()}
    </Badge>
  );
};
