import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './useAuth';
import { getClientContext, saveOnboardingData } from '@/services/onboardingService';
import type {
    OnboardingData,
    CompanyProfile,
    TeamStructure,
    Policies,
} from '@/types/onboarding';
import { emptyOnboardingData } from '@/types/onboarding';

export const ONBOARDING_STEPS = [
    { key: 'company_profile', label: 'Perfil da Empresa', description: 'Identidade e missão' },
    { key: 'team_structure', label: 'Equipe', description: 'Contatos e horários' },
    { key: 'policies', label: 'Políticas', description: 'Regras e diretrizes' },
] as const;

export type StepKey = (typeof ONBOARDING_STEPS)[number]['key'];

export function useOnboarding() {
    const { clientId } = useAuth();

    const [activeStep, setActiveStep] = useState(0);
    const [data, setData] = useState<OnboardingData>(emptyOnboardingData);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);
    const [saveSuccess, setSaveSuccess] = useState(false);

    useEffect(() => {
        if (!clientId) return;
        let cancelled = false;

        (async () => {
            setLoading(true);
            const existing = await getClientContext(clientId);
            if (!cancelled && existing) {
                setData(prev => ({
                    company_profile: { ...prev.company_profile, ...existing.company_profile },
                    team_structure: { ...prev.team_structure, ...existing.team_structure },
                    policies: { ...prev.policies, ...existing.policies },
                }));
            }
            if (!cancelled) setLoading(false);
        })();

        return () => { cancelled = true; };
    }, [clientId]);

    const updateCompanyProfile = useCallback(
        (updates: Partial<CompanyProfile>) =>
            setData(prev => ({ ...prev, company_profile: { ...prev.company_profile, ...updates } })),
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

    const save = useCallback(async () => {
        if (!clientId) return false;
        setSaving(true);
        setSaveError(null);
        setSaveSuccess(false);
        const result = await saveOnboardingData(clientId, data);
        setSaving(false);

        if (result.success) {
            setSaveSuccess(true);
            return true;
        } else {
            setSaveError(result.error || 'Tente novamente.');
            return false;
        }
    }, [clientId, data]);

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
        saveError,
        saveSuccess,
        isFirstStep,
        isLastStep,
        goNext,
        goBack,
        goTo,
        save,
        updateCompanyProfile,
        updateTeamStructure,
        updatePolicies,
    };
}
