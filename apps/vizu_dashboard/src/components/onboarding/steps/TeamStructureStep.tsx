import {
    VStack,
    FormControl,
    FormLabel,
    Input,
    Select,
    SimpleGrid,
    FormHelperText,
    Box,
    Text,
    HStack,
    IconButton,
    Button,
    Divider,
} from '@chakra-ui/react';
import { FiPlus, FiTrash2 } from 'react-icons/fi';
import type { TeamStructure, TeamMember } from '../../../types/onboarding';

interface Props {
    data: TeamStructure;
    onChange: (updates: Partial<TeamStructure>) => void;
}

const CHANNEL_TYPES = ['urgente', 'normal', 'formal', 'async'];

export default function TeamStructureStep({ data, onChange }: Props) {
    // ---- Key Contacts ----
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

    // ---- Communication Channels ----
    const updateChannel = (type: string, value: string) => {
        const updated = { ...data.communication_channels };
        if (value) {
            updated[type] = value;
        } else {
            delete updated[type];
        }
        onChange({ communication_channels: updated });
    };

    return (
        <VStack spacing={5} align="stretch">
            <FormControl>
                <FormLabel fontSize="sm">Contato Principal</FormLabel>
                <Input
                    placeholder="Ex: João Silva — Gerente de Operações"
                    value={data.main_contact ?? ''}
                    onChange={e => onChange({ main_contact: e.target.value || null })}
                />
                <FormHelperText>Nome e cargo do ponto focal</FormHelperText>
            </FormControl>

            <FormControl>
                <FormLabel fontSize="sm">Horário de Funcionamento</FormLabel>
                <Input
                    placeholder="Ex: Seg-Sex 8h-18h (BRT)"
                    value={data.business_hours ?? ''}
                    onChange={e => onChange({ business_hours: e.target.value || null })}
                />
            </FormControl>

            <FormControl>
                <FormLabel fontSize="sm">Sede</FormLabel>
                <Input
                    placeholder="Ex: São Paulo, SP"
                    value={data.headquarters ?? ''}
                    onChange={e => onChange({ headquarters: e.target.value || null })}
                />
            </FormControl>

            <Divider />

            {/* Key Contacts */}
            <Box>
                <HStack justify="space-between" mb={3}>
                    <Text fontSize="sm" fontWeight="medium">Contatos-chave</Text>
                    <Button leftIcon={<FiPlus />} size="xs" variant="outline" onClick={addContact}>
                        Adicionar
                    </Button>
                </HStack>

                <VStack spacing={3} align="stretch">
                    {data.key_contacts.map((contact, i) => (
                        <Box key={i} p={3} border="1px solid" borderColor="gray.200" borderRadius="md">
                            <HStack justify="flex-end" mb={2}>
                                <IconButton
                                    aria-label="Remover contato"
                                    icon={<FiTrash2 />}
                                    size="xs"
                                    variant="ghost"
                                    colorScheme="red"
                                    onClick={() => removeContact(i)}
                                />
                            </HStack>
                            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
                                <FormControl>
                                    <FormLabel fontSize="xs">Nome</FormLabel>
                                    <Input
                                        size="sm"
                                        placeholder="Nome"
                                        value={contact.name ?? ''}
                                        onChange={e => updateContact(i, 'name', e.target.value)}
                                    />
                                </FormControl>
                                <FormControl>
                                    <FormLabel fontSize="xs">Cargo / Função</FormLabel>
                                    <Input
                                        size="sm"
                                        placeholder="Ex: CTO"
                                        value={contact.role}
                                        onChange={e => updateContact(i, 'role', e.target.value)}
                                    />
                                </FormControl>
                                <FormControl>
                                    <FormLabel fontSize="xs">Responsabilidade</FormLabel>
                                    <Input
                                        size="sm"
                                        placeholder="Ex: Decisões técnicas"
                                        value={contact.responsibility ?? ''}
                                        onChange={e => updateContact(i, 'responsibility', e.target.value)}
                                    />
                                </FormControl>
                                <FormControl>
                                    <FormLabel fontSize="xs">Preferência de Contato</FormLabel>
                                    <Input
                                        size="sm"
                                        placeholder="Ex: Slack para urgências"
                                        value={contact.contact_preference ?? ''}
                                        onChange={e => updateContact(i, 'contact_preference', e.target.value)}
                                    />
                                </FormControl>
                            </SimpleGrid>
                        </Box>
                    ))}
                </VStack>
            </Box>

            <Divider />

            {/* Communication Channels */}
            <Box>
                <Text fontSize="sm" fontWeight="medium" mb={3}>Canais de Comunicação</Text>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
                    {CHANNEL_TYPES.map(type => (
                        <FormControl key={type}>
                            <FormLabel fontSize="xs" textTransform="capitalize">{type}</FormLabel>
                            <Input
                                size="sm"
                                placeholder={`Ex: ${type === 'urgente' ? 'WhatsApp' : type === 'formal' ? 'Email' : 'Slack'}`}
                                value={data.communication_channels[type] ?? ''}
                                onChange={e => updateChannel(type, e.target.value)}
                            />
                        </FormControl>
                    ))}
                </SimpleGrid>
            </Box>

            <Divider />

            {/* Escalation Path */}
            <FormControl>
                <FormLabel fontSize="sm">Caminho de Escalação</FormLabel>
                <Input
                    placeholder="Ex: Suporte → Gerente → Diretor (separe por vírgula)"
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
                <FormHelperText>Separe cada nível por vírgula</FormHelperText>
            </FormControl>
        </VStack>
    );
}
