import {
    Box,
    FormControl,
    FormLabel,
    Input,
    Select,
    Slider,
    SliderTrack,
    SliderFilledTrack,
    SliderThumb,
    SimpleGrid,
    HStack,
    Text,
} from '@chakra-ui/react';
import type { AgentConfigData } from '../../../services/agentBuilderService';

interface AgentConfigSectionProps {
    agentConfig: AgentConfigData;
    setAgentConfigField: <K extends keyof AgentConfigData>(field: K, value: AgentConfigData[K]) => void;
}

const MODELS = [
    'openai:gpt-4o-mini',
    'openai:gpt-4o',
    'openai:gpt-4.1',
    'openai:gpt-4.1-mini',
    'anthropic:claude-sonnet-4-20250514',
];

const STRATEGIES = [
    'support_triage',
    'data_analysis',
    'report_generation',
    'knowledge_qa',
    'sales_outreach',
];

export const AgentConfigSection = ({ agentConfig, setAgentConfigField }: AgentConfigSectionProps) => {
    return (
        <Box>
            <FormControl isRequired mb={4}>
                <FormLabel>Role</FormLabel>
                <Input
                    value={agentConfig.role}
                    onChange={(e) => setAgentConfigField('role', e.target.value)}
                    placeholder="e.g., You are a data analyst that helps users..."
                />
            </FormControl>

            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl>
                    <FormLabel>Model</FormLabel>
                    <Select
                        value={agentConfig.model ?? 'openai:gpt-4o-mini'}
                        onChange={(e) => setAgentConfigField('model', e.target.value)}
                    >
                        {MODELS.map((model) => (
                            <option key={model} value={model}>{model}</option>
                        ))}
                    </Select>
                </FormControl>

                <FormControl>
                    <FormLabel>Elicitation Strategy</FormLabel>
                    <Select
                        value={agentConfig.elicitation_strategy ?? 'support_triage'}
                        onChange={(e) => setAgentConfigField('elicitation_strategy', e.target.value)}
                    >
                        {STRATEGIES.map((s) => (
                            <option key={s} value={s}>
                                {s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                            </option>
                        ))}
                    </Select>
                </FormControl>
            </SimpleGrid>

            <FormControl mt={4}>
                <FormLabel>
                    <HStack justify="space-between" w="full">
                        <Text>Max Turns</Text>
                        <Text fontWeight="bold" color="black">{agentConfig.max_turns}</Text>
                    </HStack>
                </FormLabel>
                <Slider
                    min={5}
                    max={50}
                    step={1}
                    value={agentConfig.max_turns}
                    onChange={(val) => setAgentConfigField('max_turns', val)}
                >
                    <SliderTrack bg="gray.200">
                        <SliderFilledTrack bg="black" />
                    </SliderTrack>
                    <SliderThumb boxSize={5} />
                </Slider>
                <HStack justify="space-between" mt={1}>
                    <Text fontSize="xs" color="gray.500">5</Text>
                    <Text fontSize="xs" color="gray.500">50</Text>
                </HStack>
            </FormControl>
        </Box>
    );
};

export default AgentConfigSection;
