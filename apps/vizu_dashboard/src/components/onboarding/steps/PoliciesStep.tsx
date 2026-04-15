import {
    VStack,
    FormControl,
    FormLabel,
    Textarea,
    FormHelperText,
    Divider,
    Text,
    Box,
} from '@chakra-ui/react';
import type { Policies } from '../../../types/onboarding';

interface Props {
    data: Policies;
    onChange: (updates: Partial<Policies>) => void;
}

/** Textarea where each line = one list item */
function ListField({
    label,
    helper,
    items,
    onChange,
    placeholder,
    rows,
}: {
    label: string;
    helper?: string;
    items: string[];
    onChange: (items: string[]) => void;
    placeholder: string;
    rows?: number;
}) {
    return (
        <FormControl>
            <FormLabel fontSize="sm">{label}</FormLabel>
            <Textarea
                placeholder={placeholder}
                rows={rows ?? 3}
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

export default function PoliciesStep({ data, onChange }: Props) {
    return (
        <VStack spacing={5} align="stretch">
            <Box>
                <Text fontSize="xs" color="gray.500" mb={4}>
                    Defina as regras e diretrizes que o agente deve seguir. Cada item em uma linha separada.
                </Text>
            </Box>

            <ListField
                label="Regras de Comunicação"
                helper="O que o agente pode e não pode dizer"
                items={data.communication_rules}
                onChange={items => onChange({ communication_rules: items })}
                placeholder={"Sempre responder em português formal\nNunca prometer prazos sem confirmação\nNão compartilhar dados financeiros detalhados"}
            />

            <ListField
                label="Limites Operacionais"
                helper="Ações que o agente não deve realizar"
                items={data.operational_limits}
                onChange={items => onChange({ operational_limits: items })}
                placeholder={"Não enviar emails sem aprovação\nNão alterar dados de clientes diretamente\nLimite de 100 linhas por consulta SQL"}
            />

            <ListField
                label="Red Flags / Alertas"
                helper="Situações que devem acionar alerta"
                items={data.red_flags}
                onChange={items => onChange({ red_flags: items })}
                placeholder={"Cliente menciona cancelamento\nReclamação sobre qualidade\nSolicitação de dados sensíveis"}
            />

            <Divider />

            <ListField
                label="Regras de Tratamento de Dados"
                helper="Como dados devem ser manipulados"
                items={data.data_handling_rules}
                onChange={items => onChange({ data_handling_rules: items })}
                placeholder={"Nunca exibir CPF/CNPJ completo\nAgregar dados financeiros (não exibir por cliente)\nDados de RH são confidenciais"}
            />

            <FormControl>
                <FormLabel fontSize="sm">Tom com Parceiros / Fornecedores</FormLabel>
                <Textarea
                    placeholder="Ex: Manter tom colaborativo e respeitoso, evitar termos que sugiram dependência"
                    rows={2}
                    value={data.tone_with_partners ?? ''}
                    onChange={e => onChange({ tone_with_partners: e.target.value || null })}
                />
            </FormControl>

            <FormControl>
                <FormLabel fontSize="sm">Notas de Compliance</FormLabel>
                <Textarea
                    placeholder="Ex: LGPD — todos os dados pessoais devem ser tratados conforme política interna de privacidade"
                    rows={2}
                    value={data.compliance_notes ?? ''}
                    onChange={e => onChange({ compliance_notes: e.target.value || null })}
                />
            </FormControl>
        </VStack>
    );
}
