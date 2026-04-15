import {
    VStack,
    FormControl,
    FormLabel,
    Input,
    Textarea,
    Select,
    SimpleGrid,
    FormHelperText,
    Tag,
    TagLabel,
    TagCloseButton,
    HStack,
    IconButton,
    Wrap,
    WrapItem,
} from '@chakra-ui/react';
import { FiPlus } from 'react-icons/fi';
import { useState } from 'react';
import type { CompanyProfile } from '../../../types/onboarding';

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
    'B2B SaaS',
    'B2C SaaS',
    'E-commerce',
    'Marketplace',
    'Serviços Profissionais',
    'Consultoria',
    'Indústria',
    'Agro',
    'Fintech',
    'Healthtech',
    'Edtech',
    'Outro',
];

const EMPLOYEE_RANGES = ['1-10', '11-50', '51-200', '201-500', '501+'];

export default function CompanyProfileStep({ data, onChange }: Props) {
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
        <VStack spacing={5} align="stretch">
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl>
                    <FormLabel fontSize="sm">Nome Fantasia</FormLabel>
                    <Input
                        placeholder="Ex: Vizu"
                        value={data.trading_name ?? ''}
                        onChange={e => onChange({ trading_name: e.target.value || null })}
                    />
                </FormControl>

                <FormControl>
                    <FormLabel fontSize="sm">Razão Social</FormLabel>
                    <Input
                        placeholder="Ex: Vizu Tecnologia Ltda"
                        value={data.legal_name ?? ''}
                        onChange={e => onChange({ legal_name: e.target.value || null })}
                    />
                </FormControl>
            </SimpleGrid>

            <FormControl>
                <FormLabel fontSize="sm">Slogan / Tagline</FormLabel>
                <Input
                    placeholder="Ex: Inteligência que transforma dados em decisão"
                    value={data.tagline ?? ''}
                    onChange={e => onChange({ tagline: e.target.value || null })}
                />
            </FormControl>

            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl>
                    <FormLabel fontSize="sm">Setor / Indústria</FormLabel>
                    <Select
                        placeholder="Selecione..."
                        value={data.industry ?? ''}
                        onChange={e => onChange({ industry: e.target.value || null })}
                    >
                        {INDUSTRIES.map(i => (
                            <option key={i} value={i}>{i}</option>
                        ))}
                    </Select>
                </FormControl>

                <FormControl>
                    <FormLabel fontSize="sm">Arquétipo de Negócio</FormLabel>
                    <Select
                        placeholder="Selecione..."
                        value={data.business_archetype ?? ''}
                        onChange={e => onChange({ business_archetype: e.target.value || null })}
                    >
                        {ARCHETYPES.map(a => (
                            <option key={a} value={a}>{a}</option>
                        ))}
                    </Select>
                </FormControl>
            </SimpleGrid>

            <FormControl>
                <FormLabel fontSize="sm">Missão</FormLabel>
                <Textarea
                    placeholder="Qual é a missão da empresa?"
                    rows={2}
                    value={data.mission ?? ''}
                    onChange={e => onChange({ mission: e.target.value || null })}
                />
            </FormControl>

            <FormControl>
                <FormLabel fontSize="sm">Visão</FormLabel>
                <Textarea
                    placeholder="Onde a empresa quer chegar?"
                    rows={2}
                    value={data.vision ?? ''}
                    onChange={e => onChange({ vision: e.target.value || null })}
                />
            </FormControl>

            <FormControl>
                <FormLabel fontSize="sm">Valores Fundamentais</FormLabel>
                <HStack>
                    <Input
                        placeholder="Adicionar um valor (ex: Inovação)"
                        value={newValue}
                        onChange={e => setNewValue(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCoreValue(); } }}
                    />
                    <IconButton
                        aria-label="Adicionar valor"
                        icon={<FiPlus />}
                        onClick={addCoreValue}
                        size="md"
                    />
                </HStack>
                <Wrap mt={2}>
                    {data.core_values.map(val => (
                        <WrapItem key={val}>
                            <Tag size="md" colorScheme="blue" borderRadius="full">
                                <TagLabel>{val}</TagLabel>
                                <TagCloseButton onClick={() => removeCoreValue(val)} />
                            </Tag>
                        </WrapItem>
                    ))}
                </Wrap>
            </FormControl>

            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                <FormControl>
                    <FormLabel fontSize="sm">Ano de Fundação</FormLabel>
                    <Input
                        type="number"
                        placeholder="Ex: 2020"
                        value={data.founding_year ?? ''}
                        onChange={e => onChange({ founding_year: e.target.value ? Number(e.target.value) : null })}
                    />
                </FormControl>

                <FormControl>
                    <FormLabel fontSize="sm">Cidade Sede</FormLabel>
                    <Input
                        placeholder="Ex: São Paulo, SP"
                        value={data.headquarters_city ?? ''}
                        onChange={e => onChange({ headquarters_city: e.target.value || null })}
                    />
                </FormControl>

                <FormControl>
                    <FormLabel fontSize="sm">Nº de Funcionários</FormLabel>
                    <Select
                        placeholder="Selecione..."
                        value={data.employee_count_range ?? ''}
                        onChange={e => onChange({ employee_count_range: e.target.value || null })}
                    >
                        {EMPLOYEE_RANGES.map(r => (
                            <option key={r} value={r}>{r}</option>
                        ))}
                    </Select>
                    <FormHelperText>Faixa aproximada</FormHelperText>
                </FormControl>
            </SimpleGrid>
        </VStack>
    );
}
