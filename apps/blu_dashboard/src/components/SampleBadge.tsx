import { Badge } from '@chakra-ui/react';

interface SampleBadgeProps {
  size?: 'xs' | 'sm';
}

export const SampleBadge = ({ size = 'xs' }: SampleBadgeProps) => {
  return (
    <Badge
      bg="#f9731620"
      color="#f97316"
      fontSize={size}
      borderRadius="full"
      px={2}
      py={0.5}
      textTransform="uppercase"
      letterSpacing="wider"
    >
      Exemplo
    </Badge>
  );
};

export default SampleBadge;
