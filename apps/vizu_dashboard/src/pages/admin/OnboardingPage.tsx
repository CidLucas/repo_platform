import { Box, Text, VStack } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import OnboardingWizard from '../../components/onboarding/OnboardingWizard';

function OnboardingPage() {
    return (
        <AdminLayout>
            <Box p={8} maxW="900px" mx="auto">
                <VStack spacing={2} mb={8} align="start">
                    <Text
                        fontSize="24px"
                        fontWeight="semibold"
                        color="white"
                        letterSpacing="-0.3px"
                    >
                        Personalizar Agente
                    </Text>
                    <Text fontSize="14px" color="whiteAlpha.600" lineHeight="20px">
                        Configure as informações da sua empresa para que o agente responda de
                        forma personalizada. Quanto mais contexto você fornecer, melhores serão
                        as respostas.
                    </Text>
                </VStack>

                <OnboardingWizard />
            </Box>
        </AdminLayout>
    );
}

export default OnboardingPage;
