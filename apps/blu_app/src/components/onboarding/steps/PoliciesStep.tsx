import type { Policies } from '@/types/onboarding';

interface Props {
    data: Policies;
    onChange: (updates: Partial<Policies>) => void;
}

const textareaClass =
    'w-full bg-elevated border border-border rounded px-3 py-2 text-white text-body-sm placeholder-gray-400 ' +
    'focus:outline-none focus:border-blu-500 hover:border-gray-400 transition-colors resize-none';

function ListField({
    label,
    hint,
    items,
    onChange,
    placeholder,
    rows = 3,
}: {
    label: string;
    hint?: string;
    items: string[];
    onChange: (items: string[]) => void;
    placeholder: string;
    rows?: number;
}) {
    return (
        <div className="flex flex-col gap-1">
            <label className="text-caption text-gray-200 font-medium">{label}</label>
            <textarea
                className={textareaClass}
                rows={rows}
                placeholder={placeholder}
                value={items.join('\n')}
                onChange={e =>
                    onChange(
                        e.target.value
                            .split('\n')
                            .filter(line => line.trim() !== '' || e.target.value.endsWith('\n'))
                    )
                }
                onBlur={e =>
                    onChange(
                        e.target.value.split('\n').map(s => s.trim()).filter(Boolean)
                    )
                }
            />
            {hint && <p className="text-caption-sm text-gray-400">{hint}</p>}
        </div>
    );
}

export function PoliciesStep({ data, onChange }: Props) {
    return (
        <div className="flex flex-col gap-5">
            <p className="text-caption text-gray-400">
                Defina as regras e diretrizes que o agente deve seguir. Cada item em uma linha separada.
            </p>

            <ListField
                label="Regras de Comunicação"
                hint="O que o agente pode e não pode dizer"
                items={data.communication_rules}
                onChange={items => onChange({ communication_rules: items })}
                placeholder={"Sempre responder em português formal\nNunca prometer prazos sem confirmação\nNão compartilhar dados financeiros detalhados"}
            />

            <ListField
                label="Limites Operacionais"
                hint="Ações que o agente não deve realizar"
                items={data.operational_limits}
                onChange={items => onChange({ operational_limits: items })}
                placeholder={"Não enviar emails sem aprovação\nNão alterar dados de clientes diretamente\nLimite de 100 linhas por consulta SQL"}
            />

            <ListField
                label="Red Flags / Alertas"
                hint="Situações que devem acionar alerta"
                items={data.red_flags}
                onChange={items => onChange({ red_flags: items })}
                placeholder={"Cliente menciona cancelamento\nReclamação sobre qualidade\nSolicitação de dados sensíveis"}
            />

            <hr className="border-border" />

            <ListField
                label="Regras de Tratamento de Dados"
                hint="Como dados devem ser manipulados"
                items={data.data_handling_rules}
                onChange={items => onChange({ data_handling_rules: items })}
                placeholder={"Nunca exibir CPF/CNPJ completo\nAgregar dados financeiros (não exibir por cliente)\nDados de RH são confidenciais"}
            />

            <div className="flex flex-col gap-1">
                <label className="text-caption text-gray-200 font-medium">Tom com Parceiros / Fornecedores</label>
                <textarea
                    className={textareaClass}
                    rows={2}
                    placeholder="Ex: Manter tom colaborativo e respeitoso, evitar termos que sugiram dependência"
                    value={data.tone_with_partners ?? ''}
                    onChange={e => onChange({ tone_with_partners: e.target.value || null })}
                />
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-caption text-gray-200 font-medium">Notas de Compliance</label>
                <textarea
                    className={textareaClass}
                    rows={2}
                    placeholder="Ex: LGPD — todos os dados pessoais devem ser tratados conforme política interna de privacidade"
                    value={data.compliance_notes ?? ''}
                    onChange={e => onChange({ compliance_notes: e.target.value || null })}
                />
            </div>
        </div>
    );
}
