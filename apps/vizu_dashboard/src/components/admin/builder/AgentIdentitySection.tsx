import {
    Box,
    FormControl,
    FormLabel,
    Input,
    Textarea,
    Select,
    Switch,
    HStack,
    SimpleGrid,
    Text,
} from '@chakra-ui/react';
import type { AgentBuilderFormData } from '../../../hooks/useAgentBuilder';

interface AgentIdentitySectionProps {
    formData: AgentBuilderFormData;
    setField: <K extends keyof AgentBuilderFormData>(field: K, value: AgentBuilderFormData[K]) => void;
}

const CATEGORIES = [
    'data_analysis',
    'report_generation',
    'knowledge_assistant',
    'support',
    'sales',
    'custom',
];

const TIERS = ['BASIC', 'PROFESSIONAL', 'ENTERPRISE', 'ADMIN'];

const ICONS = [
    '📊', '📈', '📋', '🔍', '💡', '🤖', '📝', '💬',
    '📁', '🛠️', '🔬', '🧮', '📚', '🎯', '⚡', '🧠',
];

export const AgentIdentitySection = ({ formData, setField }: AgentIdentitySectionProps) => {
    const slug = formData.name
        .toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_]/g, '');

    return (
        <Box>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl isRequired>
                    <FormLabel>Name</FormLabel>
                    <Input
                        value={formData.name}
                        onChange={(e) => setField('name', e.target.value)}
                        placeholder="e.g., Data Analyst"
                    />
                </FormControl>

                <FormControl>
                    <FormLabel>Slug (auto-generated)</FormLabel>
                    <Input value={slug} isReadOnly bg="gray.50" color="gray.600" />
                </FormControl>

                <FormControl>
                    <FormLabel>Category</FormLabel>
                    <Select
                        value={formData.category}
                        onChange={(e) => setField('category', e.target.value)}
                        placeholder="Select category"
                    >
                        {CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>
                                {cat.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                            </option>
                        ))}
                    </Select>
                </FormControl>

                <FormControl>
                    <FormLabel>Icon</FormLabel>
                    <Select
                        value={formData.icon}
                        onChange={(e) => setField('icon', e.target.value)}
                        placeholder="Select icon"
                    >
                        {ICONS.map((icon) => (
                            <option key={icon} value={icon}>
                                {icon}
                            </option>
                        ))}
                    </Select>
                </FormControl>

                <FormControl>
                    <FormLabel>Tier Required</FormLabel>
                    <Select
                        value={formData.tier_required}
                        onChange={(e) => setField('tier_required', e.target.value)}
                    >
                        {TIERS.map((tier) => (
                            <option key={tier} value={tier}>{tier}</option>
                        ))}
                    </Select>
                </FormControl>

                <FormControl>
                    <FormLabel>Active</FormLabel>
                    <HStack>
                        <Switch
                            isChecked={formData.is_active}
                            onChange={(e) => setField('is_active', e.target.checked)}
                            colorScheme="green"
                        />
                        <Text fontSize="sm" color="gray.600">
                            {formData.is_active ? 'Visible to users' : 'Hidden'}
                        </Text>
                    </HStack>
                </FormControl>
            </SimpleGrid>

            <FormControl mt={4}>
                <FormLabel>Description</FormLabel>
                <Textarea
                    value={formData.description}
                    onChange={(e) => setField('description', e.target.value)}
                    placeholder="What does this agent do?"
                    rows={3}
                />
            </FormControl>
        </Box>
    );
};

export default AgentIdentitySection;
