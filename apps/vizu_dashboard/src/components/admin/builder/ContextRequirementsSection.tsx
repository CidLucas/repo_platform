import {
    Box,
    Button,
    FormControl,
    FormLabel,
    Input,
    Select,
    Switch,
    HStack,
    VStack,
    IconButton,
    Text,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
} from '@chakra-ui/react';
import { FiPlus, FiTrash2, FiArrowUp, FiArrowDown } from 'react-icons/fi';
import { useState } from 'react';
import type { ContextFieldDefinition } from '../../../services/agentBuilderService';

interface ContextRequirementsSectionProps {
    fields: ContextFieldDefinition[];
    addContextField: (field: ContextFieldDefinition) => void;
    updateContextField: (index: number, field: ContextFieldDefinition) => void;
    removeContextField: (index: number) => void;
    reorderContextFields: (fromIndex: number, toIndex: number) => void;
}

const FIELD_TYPES = ['text', 'bool', 'select'];

const EMPTY_FIELD: ContextFieldDefinition = {
    field: '',
    type: 'text',
    required: true,
    label: '',
    prompt_hint: '',
};

export const ContextRequirementsSection = ({
    fields,
    addContextField,
    updateContextField,
    removeContextField,
    reorderContextFields,
}: ContextRequirementsSectionProps) => {
    const [newField, setNewField] = useState<ContextFieldDefinition>({ ...EMPTY_FIELD });

    const handleAdd = () => {
        if (!newField.field.trim() || !newField.label.trim()) return;
        addContextField({ ...newField });
        setNewField({ ...EMPTY_FIELD });
    };

    return (
        <Box>
            <Text fontSize="sm" color="gray.600" mb={4}>
                Define context fields that the Config Helper will ask users before the agent session starts.
            </Text>

            {fields.length > 0 && (
                <Box overflowX="auto" mb={6}>
                    <Table size="sm" variant="simple">
                        <Thead>
                            <Tr>
                                <Th>Field Slug</Th>
                                <Th>Label</Th>
                                <Th>Type</Th>
                                <Th>Required</Th>
                                <Th>Prompt Hint</Th>
                                <Th>Actions</Th>
                            </Tr>
                        </Thead>
                        <Tbody>
                            {fields.map((field, index) => (
                                <Tr key={index}>
                                    <Td>
                                        <Input
                                            size="sm"
                                            value={field.field}
                                            onChange={(e) =>
                                                updateContextField(index, { ...field, field: e.target.value })
                                            }
                                        />
                                    </Td>
                                    <Td>
                                        <Input
                                            size="sm"
                                            value={field.label}
                                            onChange={(e) =>
                                                updateContextField(index, { ...field, label: e.target.value })
                                            }
                                        />
                                    </Td>
                                    <Td>
                                        <Select
                                            size="sm"
                                            value={field.type}
                                            onChange={(e) =>
                                                updateContextField(index, { ...field, type: e.target.value })
                                            }
                                        >
                                            {FIELD_TYPES.map((t) => (
                                                <option key={t} value={t}>{t}</option>
                                            ))}
                                        </Select>
                                    </Td>
                                    <Td>
                                        <Switch
                                            size="sm"
                                            isChecked={field.required}
                                            onChange={(e) =>
                                                updateContextField(index, { ...field, required: e.target.checked })
                                            }
                                            colorScheme="green"
                                        />
                                    </Td>
                                    <Td>
                                        <Input
                                            size="sm"
                                            value={field.prompt_hint ?? ''}
                                            onChange={(e) =>
                                                updateContextField(index, { ...field, prompt_hint: e.target.value })
                                            }
                                            placeholder="Hint for the agent"
                                        />
                                    </Td>
                                    <Td>
                                        <HStack spacing={1}>
                                            <IconButton
                                                aria-label="Move up"
                                                icon={<FiArrowUp />}
                                                size="xs"
                                                variant="ghost"
                                                isDisabled={index === 0}
                                                onClick={() => reorderContextFields(index, index - 1)}
                                            />
                                            <IconButton
                                                aria-label="Move down"
                                                icon={<FiArrowDown />}
                                                size="xs"
                                                variant="ghost"
                                                isDisabled={index === fields.length - 1}
                                                onClick={() => reorderContextFields(index, index + 1)}
                                            />
                                            <IconButton
                                                aria-label="Remove"
                                                icon={<FiTrash2 />}
                                                size="xs"
                                                variant="ghost"
                                                colorScheme="red"
                                                onClick={() => removeContextField(index)}
                                            />
                                        </HStack>
                                    </Td>
                                </Tr>
                            ))}
                        </Tbody>
                    </Table>
                </Box>
            )}

            <Box p={4} borderWidth="1px" borderColor="gray.200" borderRadius="md" bg="gray.50">
                <Text fontWeight="medium" fontSize="sm" mb={3}>Add new field</Text>
                <VStack spacing={3}>
                    <HStack w="full" spacing={3}>
                        <FormControl flex={1}>
                            <FormLabel fontSize="xs">Field Slug</FormLabel>
                            <Input
                                size="sm"
                                value={newField.field}
                                onChange={(e) => setNewField((p) => ({ ...p, field: e.target.value }))}
                                placeholder="e.g., company_name"
                            />
                        </FormControl>
                        <FormControl flex={1}>
                            <FormLabel fontSize="xs">Label</FormLabel>
                            <Input
                                size="sm"
                                value={newField.label}
                                onChange={(e) => setNewField((p) => ({ ...p, label: e.target.value }))}
                                placeholder="e.g., Company Name"
                            />
                        </FormControl>
                        <FormControl flex={0.5}>
                            <FormLabel fontSize="xs">Type</FormLabel>
                            <Select
                                size="sm"
                                value={newField.type}
                                onChange={(e) => setNewField((p) => ({ ...p, type: e.target.value }))}
                            >
                                {FIELD_TYPES.map((t) => (
                                    <option key={t} value={t}>{t}</option>
                                ))}
                            </Select>
                        </FormControl>
                    </HStack>
                    <HStack w="full" spacing={3}>
                        <FormControl flex={1}>
                            <FormLabel fontSize="xs">Prompt Hint</FormLabel>
                            <Input
                                size="sm"
                                value={newField.prompt_hint ?? ''}
                                onChange={(e) => setNewField((p) => ({ ...p, prompt_hint: e.target.value }))}
                                placeholder="How the agent should ask for this field"
                            />
                        </FormControl>
                        <FormControl flex={0.3}>
                            <FormLabel fontSize="xs">Required</FormLabel>
                            <Switch
                                isChecked={newField.required}
                                onChange={(e) => setNewField((p) => ({ ...p, required: e.target.checked }))}
                                colorScheme="green"
                            />
                        </FormControl>
                    </HStack>
                    <Button
                        leftIcon={<FiPlus />}
                        size="sm"
                        variant="outline"
                        onClick={handleAdd}
                        isDisabled={!newField.field.trim() || !newField.label.trim()}
                        alignSelf="flex-start"
                    >
                        Add Field
                    </Button>
                </VStack>
            </Box>
        </Box>
    );
};

export default ContextRequirementsSection;
