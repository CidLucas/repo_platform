import React, { useState } from "react";
import { Button, FormControl, FormLabel, HStack, Input, Text, useToast, VStack } from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import { useOnboarding } from "../state";
import { patchOnboardingState } from "../services/onboardingService";

const Website: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();
  const [website, setWebsite] = useState(state.website ?? "");
  const [saving, setSaving] = useState(false);

  const handleContinue = async () => {
    if (saving) return;
    const normalized = website.trim();
    update({ website: normalized });
    setSaving(true);
    try {
      await patchOnboardingState({ website: normalized });
      navigate("/onboarding/package");
    } catch (err) {
      toast({
        title: "Não foi possível salvar",
        description: err instanceof Error ? err.message : "Tente novamente em instantes.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <OnboardingLayout progress={35}>
      <StepHeader
        eyebrow="Passo 1 de 3"
        title={
          <>
            Qual é o site da sua{" "}
            <Text
              as="span"
              fontStyle="italic"
              bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`}
              bgClip="text"
            >
              empresa
            </Text>
            ?
          </>
        }
        subtitle="Se tiver, usamos isso para sugerir agentes, rotinas e KPIs. Se não tiver, seguimos com defaults agora mesmo."
      />

      <VStack
        spacing={4}
        bg={C.surface}
        border="1px solid"
        borderColor={C.borderStrong}
        borderRadius="18px"
        p={{ base: 6, md: 7 }}
        align="stretch"
      >
        <FormControl>
          <FormLabel color="white" fontSize="13px" fontWeight={500} mb={1.5}>
            Website
          </FormLabel>
          <Input
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="acme.com.br"
            bg="rgba(255,255,255,0.04)"
            border="1px solid"
            borderColor={C.borderStrong}
            color="white"
            _hover={{ borderColor: C.blueLight }}
            _focus={{ borderColor: C.blue }}
          />
          <Text mt={2} fontSize="12px" color={C.textMuted}>
            Não temos bloqueio aqui: você pode pular agora e ajustar tudo no próximo passo.
          </Text>
        </FormControl>
      </VStack>

      <HStack justify="space-between" mt={8}>
        <Button
          variant="ghost"
          color={C.textDim}
          _hover={{ color: "white", bg: "rgba(255,255,255,0.04)" }}
          onClick={() => navigate(-1)}
        >
          Voltar
        </Button>
        <HStack spacing={2.5}>
          <Button
            variant="outline"
            borderColor={C.borderStrong}
            color="white"
            _hover={{ bg: "rgba(255,255,255,0.04)" }}
            isLoading={saving}
            onClick={() => {
              setWebsite("");
              void handleContinue();
            }}
          >
            Não tenho site
          </Button>
          <Button
            h="48px"
            px={7}
            bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
            color="white"
            fontWeight={600}
            rightIcon={<ArrowForwardIcon />}
            _hover={{ filter: "brightness(1.1)" }}
            isLoading={saving}
            loadingText="Salvando…"
            onClick={handleContinue}
          >
            Continuar
          </Button>
        </HStack>
      </HStack>
    </OnboardingLayout>
  );
};

export default Website;
