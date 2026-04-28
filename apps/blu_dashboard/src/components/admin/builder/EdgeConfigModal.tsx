import { useState, useEffect } from 'react';
import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    Button,
    FormControl,
    FormLabel,
    Input,
    Switch,
    VStack,
} from '@chakra-ui/react';
import type { Edge } from '@xyflow/react';

interface EdgeConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    edge: Edge | null;
    onSave: (edgeId: string, updates: { label?: string; animated?: boolean; data?: Record<string, unknown> }) => void;
}

export const EdgeConfigModal = ({ isOpen, onClose, edge, onSave }: EdgeConfigModalProps) => {
    const [label, setLabel] = useState('');
    const [animated, setAnimated] = useState(false);
    const [condition, setCondition] = useState('');

    useEffect(() => {
        if (edge) {
            setLabel(typeof edge.label === 'string' ? edge.label : '');
            setAnimated(edge.animated ?? false);
            setCondition((edge.data as Record<string, unknown>)?.condition as string ?? '');
        }
    }, [edge]);

    const handleSave = () => {
        if (!edge) return;
        onSave(edge.id, {
            label: label || undefined,
            animated,
            data: { condition: condition || undefined },
        });
        onClose();
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} size="md">
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>Edge Configuration</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                    <VStack spacing={4}>
                        <FormControl>
                            <FormLabel fontSize="sm">Label</FormLabel>
                            <Input
                                size="sm"
                                value={label}
                                onChange={(e) => setLabel(e.target.value)}
                                placeholder="e.g. success, needs_tool"
                            />
                        </FormControl>
                        <FormControl>
                            <FormLabel fontSize="sm">Condition (routing key)</FormLabel>
                            <Input
                                size="sm"
                                value={condition}
                                onChange={(e) => setCondition(e.target.value)}
                                placeholder="e.g. needs_tool, ready_to_respond"
                            />
                        </FormControl>
                        <FormControl display="flex" alignItems="center">
                            <FormLabel fontSize="sm" mb={0}>Animated</FormLabel>
                            <Switch
                                isChecked={animated}
                                onChange={(e) => setAnimated(e.target.checked)}
                                size="sm"
                            />
                        </FormControl>
                    </VStack>
                </ModalBody>
                <ModalFooter>
                    <Button variant="ghost" size="sm" onClick={onClose} mr={2}>
                        Cancel
                    </Button>
                    <Button size="sm" bg="black" color="white" _hover={{ bg: 'gray.800' }} onClick={handleSave}>
                        Save
                    </Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    );
};

export default EdgeConfigModal;
