import { useState, useEffect, useCallback } from 'react';
import { useToast } from '@chakra-ui/react';
import { useAuth } from './useAuth';
import { getClientContext, saveOnboardingData } from '../services/onboardingService';
import type {
    OnboardingData,
    CompanyProfile,
    CurrentMoment,
    TeamStructure,
    Policies,
} from '../types/onboarding';
import {
    emptyOnboardingData,
} from '../types/onboarding';

export const ONBOARDING_STEPS = [
    { key: 'company_profile', label: 'Perfil da Empresa', description: 'Identidade e missão' },
    { key: 'team_structure', label: 'Equipe', description: 'Contatos e horários' },
    { key: 'current_moment', label: 'Momento Atual', description: 'Prioridades e desafios' },
    { key: 'policies', label: 'Políticas', description: 'Regras e diretrizes' },
] as const;

export type StepKey = (typeof ONBOARDING_STEPS)[number]['key'];

export function useOnboarding() {
    const { clientId } = useAuth();
    const toast = useToast();

    const [activeStep, setActiveStep] = useState(0);
    const [data, setData] = useState<OnboardingData>(emptyOnboardingData);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Load existing data on mount
    useEffect(() => {
        if (!clientId) return;
        let cancelled = false;

        (async () => {
            setLoading(true);
            const existing = await getClientContext(clientId);
            if (!cancelled && existing) {
                setData(prev => ({
                    company_profile: { ...prev.company_profile, ...existing.company_profile },
                    current_moment: { ...prev.current_moment, ...existing.current_moment },
                    team_structure: { ...prev.team_structure, ...existing.team_structure },
                    policies: { ...prev.policies, ...existing.policies },
                }));
            }
            if (!cancelled) setLoading(false);
        })();

        return () => { cancelled = true; };
    }, [clientId]);

    // Section updaters
    const updateCompanyProfile = useCallback(
        (updates: Partial<CompanyProfile>) =>
            setData(prev => ({ ...prev, company_profile: { ...prev.company_profile, ...updates } })),
        [],
    );

    const updateCurrentMoment = useCallback(
        (updates: Partial<CurrentMoment>) =>
            setData(prev => ({ ...prev, current_moment: { ...prev.current_moment, ...updates } })),
        [],
    );

    const updateTeamStructure = useCallback(
        (updates: Partial<TeamStructure>) =>
            setData(prev => ({ ...prev, team_structure: { ...prev.team_structure, ...updates } })),
        [],
    );

    const updatePolicies = useCallback(
        (updates: Partial<Policies>) =>
            setData(prev => ({ ...prev, policies: { ...prev.policies, ...updates } })),
        [],
    );

    // Save all sections
    const save = useCallback(async () => {
        if (!clientId) return false;
        setSaving(true);
        const result = await saveOnboardingData(clientId, data);
        setSaving(false);

        if (result.success) {
            toast({
                title: 'Configurações salvas',
                description: 'As alterações serão aplicadas ao agente em até 5 minutos.',
                status: 'success',
                duration: 5000,
                isClosable: true,
            });
            return true;
        } else {
            toast({
                title: 'Erro ao salvar',
                description: result.error || 'Tente novamente.',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
            return false;
        }
    }, [clientId, data, toast]);

    // Navigation
    const goNext = useCallback(() => {
        setActiveStep(prev => Math.min(prev + 1, ONBOARDING_STEPS.length - 1));
    }, []);

    const goBack = useCallback(() => {
        setActiveStep(prev => Math.max(prev - 1, 0));
    }, []);

    const goTo = useCallback((step: number) => {
        setActiveStep(step);
    }, []);

    const isFirstStep = activeStep === 0;
    const isLastStep = activeStep === ONBOARDING_STEPS.length - 1;
    const currentStepKey = ONBOARDING_STEPS[activeStep].key;

    return {
        activeStep,
        currentStepKey,
        steps: ONBOARDING_STEPS,
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
        updateCurrentMoment,
        updateTeamStructure,
        updatePolicies,
    };
}
