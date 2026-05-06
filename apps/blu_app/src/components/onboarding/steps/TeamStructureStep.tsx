import { Plus, Trash2 } from 'lucide-react';
import { Input } from '@/components/primitives/Input';
import type { TeamStructure, TeamMember } from '@/types/onboarding';

interface Props {
    data: TeamStructure;
    onChange: (updates: Partial<TeamStructure>) => void;
}

const CHANNEL_TYPES = ['urgente', 'normal', 'formal', 'async'];

const inputClass =
    'w-full bg-elevated border border-border rounded px-3 py-1.5 text-white text-body-sm placeholder-gray-400 ' +
    'focus:outline-none focus:border-blu-500 hover:border-gray-400 transition-colors';

export function TeamStructureStep({ data, onChange }: Props) {
    const addContact = () => {
        onChange({
            key_contacts: [
                ...data.key_contacts,
                { role: '', name: null, responsibility: null, contact_preference: null },
            ],
        });
    };

    const updateContact = (index: number, field: keyof TeamMember, value: string) => {
        const updated = [...data.key_contacts];
        updated[index] = { ...updated[index], [field]: value || null };
        onChange({ key_contacts: updated });
    };

    const removeContact = (index: number) => {
        onChange({ key_contacts: data.key_contacts.filter((_, i) => i !== index) });
    };

    const updateChannel = (type: string, value: string) => {
        const updated = { ...data.communication_channels };
        if (value) updated[type] = value;
        else delete updated[type];
        onChange({ communication_channels: updated });
    };

    return (
        <div className="flex flex-col gap-5">
            <Input
                label="Contato Principal"
                placeholder="Ex: João Silva — Gerente de Operações"
                hint="Nome e cargo do ponto focal"
                value={data.main_contact ?? ''}
                onChange={e => onChange({ main_contact: e.target.value || null })}
            />

            <Input
                label="Horário de Funcionamento"
                placeholder="Ex: Seg-Sex 8h-18h (BRT)"
                value={data.business_hours ?? ''}
                onChange={e => onChange({ business_hours: e.target.value || null })}
            />

            <Input
                label="Sede"
                placeholder="Ex: São Paulo, SP"
                value={data.headquarters ?? ''}
                onChange={e => onChange({ headquarters: e.target.value || null })}
            />

            <hr className="border-border" />

            {/* Key Contacts */}
            <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                    <span className="text-body-sm font-medium text-gray-200">Contatos-chave</span>
                    <button
                        type="button"
                        onClick={addContact}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-border hover:border-blu-500 text-gray-300 hover:text-white text-caption transition-colors"
                    >
                        <Plus className="w-3.5 h-3.5" />
                        Adicionar
                    </button>
                </div>

                <div className="flex flex-col gap-3">
                    {data.key_contacts.map((contact, i) => (
                        <div key={i} className="p-3 rounded-lg border border-border bg-elevated/50 flex flex-col gap-3">
                            <div className="flex justify-end">
                                <button
                                    type="button"
                                    onClick={() => removeContact(i)}
                                    className="p-1 rounded text-gray-400 hover:text-urgent hover:bg-urgent/10 transition-colors"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="flex flex-col gap-1">
                                    <label className="text-caption text-gray-400">Nome</label>
                                    <input className={inputClass} placeholder="Nome" value={contact.name ?? ''} onChange={e => updateContact(i, 'name', e.target.value)} />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-caption text-gray-400">Cargo / Função</label>
                                    <input className={inputClass} placeholder="Ex: CTO" value={contact.role} onChange={e => updateContact(i, 'role', e.target.value)} />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-caption text-gray-400">Responsabilidade</label>
                                    <input className={inputClass} placeholder="Ex: Decisões técnicas" value={contact.responsibility ?? ''} onChange={e => updateContact(i, 'responsibility', e.target.value)} />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-caption text-gray-400">Preferência de Contato</label>
                                    <input className={inputClass} placeholder="Ex: Slack para urgências" value={contact.contact_preference ?? ''} onChange={e => updateContact(i, 'contact_preference', e.target.value)} />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <hr className="border-border" />

            {/* Communication Channels */}
            <div className="flex flex-col gap-3">
                <span className="text-body-sm font-medium text-gray-200">Canais de Comunicação</span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {CHANNEL_TYPES.map(type => (
                        <div key={type} className="flex flex-col gap-1">
                            <label className="text-caption text-gray-400 capitalize">{type}</label>
                            <input
                                className={inputClass}
                                placeholder={`Ex: ${type === 'urgente' ? 'WhatsApp' : type === 'formal' ? 'Email' : 'Slack'}`}
                                value={data.communication_channels[type] ?? ''}
                                onChange={e => updateChannel(type, e.target.value)}
                            />
                        </div>
                    ))}
                </div>
            </div>

            <hr className="border-border" />

            {/* Escalation Path */}
            <Input
                label="Caminho de Escalação"
                placeholder="Ex: Suporte → Gerente → Diretor (separe por vírgula)"
                hint="Separe cada nível por vírgula"
                value={data.escalation_path.join(', ')}
                onChange={e =>
                    onChange({
                        escalation_path: e.target.value
                            .split(',')
                            .map(s => s.trim())
                            .filter(Boolean),
                    })
                }
            />
        </div>
    );
}
