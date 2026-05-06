import { OnboardingWizard } from '@/components/onboarding/OnboardingWizard';

export function OnboardingPage() {
    return (
        <div className="p-6 md:p-8 max-w-3xl mx-auto">
            <div className="flex flex-col gap-1 mb-8">
                <h1 className="text-xl font-semibold text-white tracking-tight">
                    Personalizar Agente
                </h1>
                <p className="text-body-sm text-gray-400 leading-relaxed">
                    Configure as informações da sua empresa para que o agente responda de
                    forma personalizada. Quanto mais contexto você fornecer, melhores serão
                    as respostas.
                </p>
            </div>

            <OnboardingWizard />
        </div>
    );
}
