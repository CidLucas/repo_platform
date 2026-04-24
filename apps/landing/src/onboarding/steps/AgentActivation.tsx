import React, { useMemo, useState } from "react";
import { Box, Button, HStack, Switch, Text, useToast, VStack } from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import { ALL_AGENTS, suggestAgents, useOnboarding } from "../state";
import { patchOnboardingState } from "../services/onboardingService";

// Step 4 – Smart Agent Activation. Pre-selected based on vertical + path. 75%.
const AgentActivation: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();

  const suggested = useMemo(() => suggestAgents(state), [state]);
  const [selected, setSelected] = useState<string[]>(
    state.agents.length > 0 ? state.agents : suggested
  );
  const [saving, setSaving] = useState(false);

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const handleNext = async () => {
    if (saving) return;
    update({ agents: selected });
    setSaving(true);
    try {
      // Selection is only persisted in onboarding_state; client_enabled_agents
      // rows are created atomically at LaunchPad bootstrap.
      await patchOnboardingState({ agents: selected });
      navigate("/onboarding/rules");
    } catch (err) {
      toast({
        title: "Não foi possível salvar",
        description:
          err instanceof Error ? err.message : "Tente novamente em instantes.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <OnboardingLayout progress={75}>
      <StepHeader
        eyebrow="Passo 3 de 4"
        title={
          <>
            Seu time de{" "}
            <Text
              as="span"
              fontStyle="italic"
              bgGradient={`linear(to-r, ${C.purpleLight}, ${C.pink})`}
              bgClip="text"
            >
              agentes
            </Text>
            .
          </>
        }
        subtitle="Já deixamos os mais úteis para o seu contexto ativos. Ajuste se quiser."
      />

      <VStack spacing={2.5} align="stretch">
        {ALL_AGENTS.map((a) => {
          const active = selected.includes(a.id);
          const recommended = suggested.includes(a.id);
          return (
            <Box
              key={a.id}
              bg={active ? `${a.color}0F` : C.surface}
              border="1px solid"
              borderColor={active ? `${a.color}66` : C.borderStrong}
              borderRadius="14px"
              px={{ base: 4, md: 5 }}
              py={4}
              transition="all .15s"
              _hover={{ borderColor: active ? a.color : C.textDim }}
            >
              <HStack justify="space-between" align="center" spacing={4}>
                <HStack spacing={3.5} flex={1} minW={0}>
                  <Box
                    w="10px"
                    h="10px"
                    borderRadius="full"
                    bg={a.color}
                    boxShadow={active ? `0 0 14px ${a.color}` : "none"}
                    flexShrink={0}
                  />
                  <Box minW={0}>
                    <HStack spacing={2}>
                      <Text fontSize="15px" fontWeight={600} color="white">
                        {a.name}
                      </Text>
                      {recommended && (
                        <Text
                          fontSize="10px"
                          fontWeight={600}
                          letterSpacing="0.08em"
                          textTransform="uppercase"
                          color={C.blueLight}
                        >
                          Recomendado
                        </Text>
                      )}
                    </HStack>
                    <Text fontSize="13px" color={C.textDim} noOfLines={1}>
                      {a.value}
                    </Text>
                  </Box>
                </HStack>
                <Switch
                  isChecked={active}
                  onChange={() => toggle(a.id)}
                  colorScheme="purple"
                  size="md"
                />
              </HStack>
            </Box>
          );
        })}
      </VStack>

      <Text color={C.textMuted} fontSize="12px" mt={4}>
        Você pode ativar ou desativar agentes a qualquer momento dentro do Centro de Comando.
      </Text>

      <HStack justify="space-between" mt={8}>
        <Button
          variant="ghost"
          color={C.textDim}
          _hover={{ color: "white", bg: "rgba(255,255,255,0.04)" }}
          onClick={() => navigate(-1)}
        >
          Voltar
        </Button>
        <Button
          h="48px"
          px={7}
          bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
          color="white"
          fontWeight={600}
          rightIcon={<ArrowForwardIcon />}
          _hover={{ filter: "brightness(1.1)" }}
          isDisabled={selected.length === 0}
          isLoading={saving}
          loadingText="Salvando…"
          onClick={handleNext}
        >
          Continuar
        </Button>
      </HStack>
    </OnboardingLayout>
  );
};

export default AgentActivation;
