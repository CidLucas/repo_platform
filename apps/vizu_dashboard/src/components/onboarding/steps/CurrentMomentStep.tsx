import {
    VStack,
    FormControl,
    FormLabel,
    Textarea,
    Select,
    SimpleGrid,
    FormHelperText,
    Box,
    Text,
    HStack,
    Input,
    IconButton,
    Button,
    Divider,
} from '@chakra-ui/react';
import { FiPlus, FiTrash2 } from 'react-icons/fi';
import { useState } from 'react';
import type { CurrentMoment } from '../../../types/onboarding';

interface Props {
    data: CurrentMoment;
    onChange: (updates: Partial<CurrentMoment>) => void;
}

const STAGES = [
    { value: 'startup', label: 'Startup / Validação' },
    { value: 'growth', label: 'Crescimento' },
    { value: 'scaling', label: 'Escala' },
    { value: 'maturity', label: 'Maturidade' },
];

/** Reusable textarea-list: each line = one item */
function ListField({
    label,
    helper,
    items,
    onChange,
    placeholder,
}: {
    label: string;
    helper?: string;
    items: string[];
    onChange: (items: string[]) => void;
    placeholder: string;
}) {
    return (
        <FormControl>
            <FormLabel fontSize="sm">{label}</FormLabel>
            <Textarea
                placeholder={placeholder}
                rows={3}
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
                        e.target.value
                            .split('\n')
                            .map(s => s.trim())
                            .filter(Boolean)
                    )
                }
            />
            {helper && <FormHelperText>{helper}</FormHelperText>}
        </FormControl>
    );
}

export default function CurrentMomentStep({ data, onChange }: Props) {
    const [newMetricKey, setNewMetricKey] = useState('');
    const [newMetricValue, setNewMetricValue] = useState('');

    const addMetric = () => {
        const key = newMetricKey.trim();
        const val = newMetricValue.trim();
        if (key && val) {
            onChange({ key_metrics: { ...data.key_metrics, [key]: val } });
            setNewMetricKey('');
            setNewMetricValue('');
        }
    };

    const removeMetric = (key: string) => {
        const updated = { ...data.key_metrics };
        delete updated[key];
        onChange({ key_metrics: updated });
    };

    return (
        <VStack spacing={5} align="stretch">
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl>
                    <FormLabel fontSize="sm">Estágio da Empresa</FormLabel>
                    <Select
                        placeholder="Selecione..."
                        value={data.stage ?? ''}
                        onChange={e => onChange({ stage: e.target.value || null })}
                    >
                        {STAGES.map(s => (
                            <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                    </Select>
                </FormControl>

                <FormControl>
                    <FormLabel fontSize="sm">Período de Referência</FormLabel>
                    <Input
                        placeholder="Ex: Q2 2026"
                        value={data.period ?? ''}
                        onChange={e => onChange({ period: e.target.value || null })}
                    />
                </FormControl>
            </SimpleGrid>

            <ListField
                label="Prioridades Atuais"
                helper="Uma prioridade por linha (top 3-5)"
                items={data.current_priorities}
                onChange={items => onChange({ current_priorities: items })}
                placeholder={"Aumentar NPS em 10 pontos\nLançar produto v2\nExpandir para o Sudeste"}
            />

            <ListField
                label="Desafios Atuais"
                helper="Um desafio por linha"
                items={data.current_challenges}
                onChange={items => onChange({ current_challenges: items })}
                placeholder={"Alta rotatividade no time de vendas\nCusto de aquisição crescente"}
            />

            <ListField
                label="Conquistas Recentes"
                items={data.recent_wins}
                onChange={items => onChange({ recent_wins: items })}
                placeholder={"Fechamos contrato com empresa X\nCrescimento de 20% no MRR"}
            />

            <Divider />

            {/* Key Metrics */}
            <Box>
                <Text fontSize="sm" fontWeight="medium" mb={3}>Métricas-chave (KPIs)</Text>
                <VStack spacing={2} align="stretch">
                    {Object.entries(data.key_metrics).map(([key, val]) => (
                        <HStack key={key}>
                            <Input size="sm" value={key} isReadOnly flex={1} />
                            <Input size="sm" value={String(val)} isReadOnly flex={1} />
                            <IconButton
                                aria-label="Remover métrica"
                                icon={<FiTrash2 />}
                                size="xs"
                                variant="ghost"
                                colorScheme="red"
                                onClick={() => removeMetric(key)}
                            />
                        </HStack>
                    ))}
                    <HStack>
                        <Input
                            size="sm"
                            placeholder="Métrica (ex: NPS)"
                            value={newMetricKey}
                            onChange={e => setNewMetricKey(e.target.value)}
                            flex={1}
                        />
                        <Input
                            size="sm"
                            placeholder="Valor (ex: 72)"
                            value={newMetricValue}
                            onChange={e => setNewMetricValue(e.target.value)}
                            flex={1}
                        />
                        <Button size="sm" leftIcon={<FiPlus />} onClick={addMetric} variant="outline">
                            Adicionar
                        </Button>
                    </HStack>
                </VStack>
            </Box>

            <Divider />

            <ListField
                label="Campanhas Ativas"
                items={data.active_campaigns}
                onChange={items => onChange({ active_campaigns: items })}
                placeholder={"Black Friday 2026\nCampanha de indicação"}
            />

            <ListField
                label="Próximos Eventos"
                items={data.upcoming_events}
                onChange={items => onChange({ upcoming_events: items })}
                placeholder={"Keynote produto — 15/05\nFeira do setor — Jun/2026"}
            />
        </VStack>
    );
}
