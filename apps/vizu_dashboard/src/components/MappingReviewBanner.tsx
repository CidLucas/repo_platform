import { Box, HStack, Icon, Text, Button, VStack } from '@chakra-ui/react';
import { FiAlertTriangle, FiArrowRight } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import {
    useConnectorsNeedingReview,
    type ConnectorNeedingReview,
    type MappingReviewReason,
} from '../hooks/useConnectorsNeedingReview';

const REASON_LABEL: Record<MappingReviewReason, string> = {
    discovery_pending: 'Descoberta de colunas pendente',
    needs_review: 'Mapeamento precisa de revisão',
    unmapped: 'Colunas sem mapeamento',
    awaiting_sync: 'Mapeamento pronto — aguardando sincronização',
};

function reasonDetail(item: ConnectorNeedingReview): string {
    switch (item.reason) {
        case 'discovery_pending':
            return 'Ainda não temos o esquema desta fonte.';
        case 'needs_review':
            return `${item.needsReviewCount} coluna(s) precisam da sua confirmação.`;
        case 'unmapped':
            return `${item.unmappedCount} coluna(s) sem destino no esquema canônico.`;
        case 'awaiting_sync':
            return 'Confirme o mapeamento para iniciar a primeira sincronização.';
    }
}

interface MappingReviewBannerProps {
    /** Wrapper margin/padding overrides for layout-specific placement. */
    mx?: number | string;
    mt?: number | string;
    mb?: number | string;
}

/**
 * Banner shown when one or more connectors require user attention on the
 * column mapping page. Hidden when nothing needs review.
 */
export function MappingReviewBanner({ mx = 6, mt = 4, mb = 0 }: MappingReviewBannerProps) {
    const navigate = useNavigate();
    const { items, loading } = useConnectorsNeedingReview();

    if (loading || items.length === 0) return null;

    const first = items[0];
    const extra = items.length - 1;

    return (
        <Box
            mx={mx}
            mt={mt}
            mb={mb}
            px={5}
            py={4}
            borderRadius="10px"
            bg="linear-gradient(90deg, rgba(234,179,8,0.10), rgba(244,114,182,0.08))"
            border="1px solid"
            borderColor="rgba(234,179,8,0.35)"
        >
            <HStack justify="space-between" align="flex-start" spacing={4} flexWrap="wrap">
                <HStack align="flex-start" spacing={3} flex={1} minW="280px">
                    <Box pt="2px">
                        <Icon as={FiAlertTriangle} color="yellow.300" boxSize={5} />
                    </Box>
                    <VStack align="flex-start" spacing={1}>
                        <Text fontSize="sm" fontWeight={600} color="white">
                            {REASON_LABEL[first.reason]} — {first.nomeServico}
                        </Text>
                        <Text fontSize="13px" color="whiteAlpha.700">
                            {reasonDetail(first)}
                            {extra > 0 && (
                                <Box as="span" ml={2} color="whiteAlpha.500">
                                    +{extra} outra{extra > 1 ? 's' : ''} fonte{extra > 1 ? 's' : ''} aguardando.
                                </Box>
                            )}
                        </Text>
                    </VStack>
                </HStack>
                <Button
                    size="sm"
                    rightIcon={<FiArrowRight />}
                    bgGradient="linear(to-r, #3b82f6, #6366f1)"
                    color="white"
                    _hover={{ bgGradient: 'linear(to-r, #4f8df8, #7c7df0)' }}
                    onClick={() =>
                        navigate(`/dashboard/admin/connectors/${first.credentialId}/mapping`)
                    }
                >
                    Revisar mapeamento
                </Button>
            </HStack>
        </Box>
    );
}

export default MappingReviewBanner;
