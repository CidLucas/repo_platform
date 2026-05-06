import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { Input } from '@/components/primitives/Input';
import { Select } from '@/components/primitives/Select';
import type { CompanyProfile } from '@/types/onboarding';

interface Props {
    data: CompanyProfile;
    onChange: (updates: Partial<CompanyProfile>) => void;
}

const INDUSTRIES = [
    'Tecnologia / SaaS',
    'E-commerce / Varejo',
    'Serviços Financeiros',
    'Saúde',
    'Educação',
    'Alimentos e Bebidas',
    'Indústria / Manufatura',
    'Agronegócio',
    'Logística / Transporte',
    'Serviços Ambientais',
    'Consultoria / Serviços Profissionais',
    'Marketing / Publicidade',
    'Imobiliário / Construção',
    'Energia',
    'Outro',
];

const ARCHETYPES = [
    'B2B SaaS', 'B2C SaaS', 'E-commerce', 'Marketplace',
    'Serviços Profissionais', 'Consultoria', 'Indústria',
    'Agro', 'Fintech', 'Healthtech', 'Edtech', 'Outro',
];

const EMPLOYEE_RANGES = ['1-10', '11-50', '51-200', '201-500', '501+'];

const textareaClass =
    'w-full bg-elevated border border-border rounded px-3 py-2 text-white text-body-sm placeholder-gray-400 ' +
    'focus:outline-none focus:border-blu-500 hover:border-gray-400 transition-colors resize-none';

export function CompanyProfileStep({ data, onChange }: Props) {
    const [newValue, setNewValue] = useState('');

    const addCoreValue = () => {
        const trimmed = newValue.trim();
        if (trimmed && !data.core_values.includes(trimmed)) {
            onChange({ core_values: [...data.core_values, trimmed] });
            setNewValue('');
        }
    };

    const removeCoreValue = (val: string) => {
        onChange({ core_values: data.core_values.filter(v => v !== val) });
    };

    return (
        <div className="flex flex-col gap-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                    label="Nome Fantasia"
                    placeholder="Ex: Blu"
                    value={data.trading_name ?? ''}
                    onChange={e => onChange({ trading_name: e.target.value || null })}
                />
                <Input
                    label="Razão Social"
                    placeholder="Ex: Blu Tecnologia Ltda"
                    value={data.legal_name ?? ''}
                    onChange={e => onChange({ legal_name: e.target.value || null })}
                />
            </div>

            <Input
                label="Slogan / Tagline"
                placeholder="Ex: Inteligência que transforma dados em decisão"
                value={data.tagline ?? ''}
                onChange={e => onChange({ tagline: e.target.value || null })}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Select
                    label="Setor / Indústria"
                    value={data.industry ?? ''}
                    onChange={e => onChange({ industry: e.target.value || null })}
                >
                    <option value="">Selecione...</option>
                    {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                </Select>

                <Select
                    label="Arquétipo de Negócio"
                    value={data.business_archetype ?? ''}
                    onChange={e => onChange({ business_archetype: e.target.value || null })}
                >
                    <option value="">Selecione...</option>
                    {ARCHETYPES.map(a => <option key={a} value={a}>{a}</option>)}
                </Select>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-caption text-gray-200 font-medium">Missão</label>
                <textarea
                    className={textareaClass}
                    rows={2}
                    placeholder="Qual é a missão da empresa?"
                    value={data.mission ?? ''}
                    onChange={e => onChange({ mission: e.target.value || null })}
                />
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-caption text-gray-200 font-medium">Visão</label>
                <textarea
                    className={textareaClass}
                    rows={2}
                    placeholder="Onde a empresa quer chegar?"
                    value={data.vision ?? ''}
                    onChange={e => onChange({ vision: e.target.value || null })}
                />
            </div>

            {/* Core Values */}
            <div className="flex flex-col gap-2">
                <label className="text-caption text-gray-200 font-medium">Valores Fundamentais</label>
                <div className="flex gap-2">
                    <input
                        className="flex-1 bg-elevated border border-border rounded px-3 py-2 text-white text-body-sm placeholder-gray-400 focus:outline-none focus:border-blu-500 hover:border-gray-400 transition-colors"
                        placeholder="Adicionar um valor (ex: Inovação)"
                        value={newValue}
                        onChange={e => setNewValue(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCoreValue(); } }}
                    />
                    <button
                        type="button"
                        onClick={addCoreValue}
                        className="p-2 rounded bg-elevated border border-border hover:border-blu-500 text-gray-300 hover:text-white transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                    </button>
                </div>
                {data.core_values.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-1">
                        {data.core_values.map(val => (
                            <span
                                key={val}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blu-500/15 border border-blu-500/30 text-blu-300 text-caption"
                            >
                                {val}
                                <button
                                    type="button"
                                    onClick={() => removeCoreValue(val)}
                                    className="hover:text-white transition-colors"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                            </span>
                        ))}
                    </div>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Input
                    label="Ano de Fundação"
                    type="number"
                    placeholder="Ex: 2020"
                    value={data.founding_year ?? ''}
                    onChange={e => onChange({ founding_year: e.target.value ? Number(e.target.value) : null })}
                />
                <Input
                    label="Cidade Sede"
                    placeholder="Ex: São Paulo, SP"
                    value={data.headquarters_city ?? ''}
                    onChange={e => onChange({ headquarters_city: e.target.value || null })}
                />
                <Select
                    label="Nº de Funcionários"
                    hint="Faixa aproximada"
                    value={data.employee_count_range ?? ''}
                    onChange={e => onChange({ employee_count_range: e.target.value || null })}
                >
                    <option value="">Selecione...</option>
                    {EMPLOYEE_RANGES.map(r => <option key={r} value={r}>{r}</option>)}
                </Select>
            </div>
        </div>
    );
}
