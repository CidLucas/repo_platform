import {
    Box,
    VStack,
    HStack,
    Button,
    Spinner,
    Text,
    Step,
    StepIcon,
    StepIndicator,
    StepNumber,
    StepSeparator,
    StepStatus,
    StepTitle,
    StepDescription,
    Stepper,
} from '@chakra-ui/react';
import { useOnboarding, ONBOARDING_STEPS } from '../../hooks/useOnboarding';
import CompanyProfileStep from './steps/CompanyProfileStep';
import TeamStructureStep from './steps/TeamStructureStep';
import PoliciesStep from './steps/PoliciesStep';

export default function OnboardingWizard() {
    const {
        activeStep,
        currentStepKey,
        data,
        loading,
        saving,
        isFirstStep,
        isLastStep,
        goNext,
        goBack,
        goTo,
        save,
        updateCompanyProfile,
        updateTeamStructure,
        updatePolicies,
    } = useOnboarding();

    if (loading) {
        return (
            <Box textAlign="center" py={16}>
                <Spinner size="xl" />
                <Text mt={4} color="gray.500">Carregando configurações...</Text>
            </Box>
        );
    }

    const handleNext = async () => {
        if (isLastStep) {
            await save();
        } else {
            goNext();
        }
    };

    const renderStep = () => {
        switch (currentStepKey) {
            case 'company_profile':
                return <CompanyProfileStep data={data.company_profile} onChange={updateCompanyProfile} />;
            case 'team_structure':
                return <TeamStructureStep data={data.team_structure} onChange={updateTeamStructure} />;
            case 'policies':
                return <PoliciesStep data={data.policies} onChange={updatePolicies} />;
            default:
                return null;
        }
    };

    return (
        <VStack spacing={8} align="stretch">
            {/* Stepper */}
            <Stepper index={activeStep} colorScheme="blue" size="sm">
                {ONBOARDING_STEPS.map((step, index) => (
                    <Step key={step.key} onClick={() => goTo(index)} style={{ cursor: 'pointer' }}>
                        <StepIndicator>
                            <StepStatus
                                complete={<StepIcon />}
                                incomplete={<StepNumber />}
                                active={<StepNumber />}
                            />
                        </StepIndicator>
                        <Box flexShrink={0}>
                            <StepTitle>{step.label}</StepTitle>
                            <StepDescription>{step.description}</StepDescription>
                        </Box>
                        <StepSeparator />
                    </Step>
                ))}
            </Stepper>

            {/* Step Content */}
            <Box
                bg="white"
                borderRadius="xl"
                border="1px solid"
                borderColor="gray.200"
                p={6}
            >
                {renderStep()}
            </Box>

            {/* Navigation */}
            <HStack justify="space-between">
                <Button
                    variant="outline"
                    onClick={goBack}
                    isDisabled={isFirstStep}
                >
                    Voltar
                </Button>

                <HStack spacing={3}>
                    <Button
                        variant="ghost"
                        onClick={save}
                        isLoading={saving}
                        loadingText="Salvando..."
                    >
                        Salvar rascunho
                    </Button>

                    <Button
                        colorScheme="blue"
                        onClick={handleNext}
                        isLoading={saving && isLastStep}
                        loadingText="Salvando..."
                    >
                        {isLastStep ? 'Salvar e Concluir' : 'Próximo'}
                    </Button>
                </HStack>
            </HStack>
        </VStack>
    );
}
