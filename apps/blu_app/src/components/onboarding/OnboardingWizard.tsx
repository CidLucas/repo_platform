import { Check, ChevronRight } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/primitives/Button';
import { Spinner } from '@/components/primitives/Spinner';
import { useOnboarding, ONBOARDING_STEPS } from '@/hooks/useOnboarding';
import { CompanyProfileStep } from './steps/CompanyProfileStep';
import { TeamStructureStep } from './steps/TeamStructureStep';
import { PoliciesStep } from './steps/PoliciesStep';

export function OnboardingWizard() {
    const {
        activeStep,
        currentStepKey,
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
    } = useOnboarding();

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
                <Spinner />
                <p className="text-body-sm text-gray-400">Carregando configurações...</p>
            </div>
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
        <div className="flex flex-col gap-8">
            {/* Stepper */}
            <nav aria-label="Etapas" className="flex items-center gap-0">
                {ONBOARDING_STEPS.map((step, index) => {
                    const isComplete = index < activeStep;
                    const isActive = index === activeStep;

                    return (
                        <div key={step.key} className="flex items-center flex-1 last:flex-none">
                            <button
                                type="button"
                                onClick={() => goTo(index)}
                                className="flex items-center gap-3 group"
                            >
                                {/* Circle */}
                                <div
                                    className={cn(
                                        'w-7 h-7 rounded-full flex items-center justify-center border-2 transition-colors text-caption font-semibold flex-shrink-0',
                                        isComplete
                                            ? 'bg-blu-500 border-blu-500 text-white'
                                            : isActive
                                            ? 'border-blu-500 text-blu-400 bg-transparent'
                                            : 'border-border text-gray-500 bg-transparent',
                                    )}
                                >
                                    {isComplete ? <Check className="w-3.5 h-3.5" /> : index + 1}
                                </div>

                                {/* Label */}
                                <div className="hidden sm:flex flex-col items-start">
                                    <span
                                        className={cn(
                                            'text-body-sm font-medium leading-tight',
                                            isActive ? 'text-white' : isComplete ? 'text-gray-300' : 'text-gray-500',
                                        )}
                                    >
                                        {step.label}
                                    </span>
                                    <span className="text-caption text-gray-500">{step.description}</span>
                                </div>
                            </button>

                            {/* Connector */}
                            {index < ONBOARDING_STEPS.length - 1 && (
                                <ChevronRight className="w-4 h-4 text-border mx-3 flex-shrink-0 flex-1" />
                            )}
                        </div>
                    );
                })}
            </nav>

            {/* Step Content */}
            <div className="bg-elevated border border-border rounded-xl p-6">
                {renderStep()}
            </div>

            {/* Feedback */}
            {saveError && (
                <p className="text-body-sm text-urgent" role="alert">
                    {saveError}
                </p>
            )}
            {saveSuccess && !saving && (
                <p className="text-body-sm text-ok" role="status">
                    Configurações salvas com sucesso.
                </p>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between">
                <Button
                    variant="secondary"
                    onClick={goBack}
                    disabled={isFirstStep}
                >
                    Voltar
                </Button>

                <div className="flex items-center gap-3">
                    <Button
                        variant="ghost"
                        onClick={save}
                        loading={saving && !isLastStep}
                        disabled={saving}
                    >
                        Salvar rascunho
                    </Button>

                    <Button
                        variant="primary"
                        onClick={handleNext}
                        loading={saving && isLastStep}
                        disabled={saving}
                    >
                        {isLastStep ? 'Salvar e Concluir' : 'Próximo'}
                    </Button>
                </div>
            </div>
        </div>
    );
}
