import React, { useEffect, useRef, useState } from "react";
import { Box, Button, HStack, Spinner, Text, VStack, useToast } from "@chakra-ui/react";
import { ArrowForwardIcon, WarningTwoIcon } from "@chakra-ui/icons";
import { OnboardingLayout } from "../OnboardingLayout";
import { C } from "../tokens";
import { useOnboarding } from "../state";
import { runBootstrap } from "../services/onboardingService";

type BootstrapStatus = "running" | "ready" | "error";

// Launch pad — runs bootstrap then redirects to the dashboard.
const LaunchPad: React.FC = () => {
  const { state } = useOnboarding();
  const toast = useToast();
  const [status, setStatus] = useState<BootstrapStatus>("running");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  // Guard against React StrictMode double-invocation in dev.
  const firedRef = useRef(false);

  const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {};
  const dashboardUrl = env.VITE_DASHBOARD_URL || "/dashboard";

  const bootstrap = React.useCallback(async () => {
    setStatus("running");
    setErrorDetail(null);
    try {
      await runBootstrap(state);
      setStatus("ready");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "falha desconhecida";
      console.error("[launchpad] bootstrap failed", err);
      setStatus("error");
      setErrorDetail(msg);
      toast({
        title: "Não foi possível inicializar",
        description: msg,
        status: "error",
        duration: 6000,
        isClosable: true,
      });
    }
  }, [state, toast]);

  useEffect(() => {
    if (firedRef.current) return;
    firedRef.current = true;
    void bootstrap();
  }, [bootstrap]);

  // Auto-redirect when ready.
  useEffect(() => {
    if (status === "ready") {
      window.location.href = dashboardUrl;
    }
  }, [status, dashboardUrl]);

  return (
    <OnboardingLayout progress={null}>
      <VStack spacing={8} textAlign="center" pt={{ base: 4, md: 10 }} minH="60vh" justify="center">
        <Text
          fontSize="12px"
          fontWeight={600}
          letterSpacing="0.14em"
          textTransform="uppercase"
          color={C.greenLight}
        >
          Quase lá
        </Text>

        <Box
          as="h1"
          fontFamily="'Playfair Display', serif"
          fontSize={{ base: "32px", md: "44px" }}
          fontWeight={500}
          letterSpacing="-0.02em"
          lineHeight={1.08}
          maxW="560px"
        >
          Preparando seu{" "}
          <Text
            as="span"
            fontStyle="italic"
            bgGradient={`linear(to-r, ${C.greenLight}, ${C.cyan}, ${C.blueLight})`}
            bgClip="text"
          >
            centro de comando
          </Text>
          {state.nome ? `, ${state.nome.trim().split(/\s+/)[0]}` : ""}.
        </Box>

        <Text color={C.textDim} fontSize={{ base: "15px", md: "17px" }} maxW="440px" lineHeight={1.55}>
          Estamos montando o contexto inicial dos seus agentes com as informações que você nos deu.
        </Text>

        <Box mt={4}>
          {status === "running" && (
            <HStack
              spacing={3}
              px={6}
              py={4}
              borderRadius="12px"
              bg={C.surface}
              border="1px solid"
              borderColor={C.borderStrong}
            >
              <Spinner size="sm" color={C.cyan} />
              <Text color={C.textDim} fontSize="14px">
                Ativando seus agentes…
              </Text>
            </HStack>
          )}

          {status === "error" && (
            <VStack spacing={3}>
              <HStack
                spacing={3}
                px={6}
                py={4}
                borderRadius="12px"
                bg={C.surface}
                border="1px solid"
                borderColor={C.borderStrong}
              >
                <WarningTwoIcon color={C.pink} />
                <Text color={C.textDim} fontSize="14px">
                  {errorDetail
                    ? `Falha: ${errorDetail}`
                    : "Não conseguimos inicializar agora."}
                </Text>
              </HStack>
              <HStack spacing={3}>
                <Button
                  size="md"
                  variant="outline"
                  borderColor={C.borderStrong}
                  color="white"
                  onClick={() => {
                    firedRef.current = true;
                    void bootstrap();
                  }}
                >
                  Tentar novamente
                </Button>
                <Button
                  size="md"
                  variant="ghost"
                  color={C.textDim}
                  onClick={() => { window.location.href = dashboardUrl; }}
                >
                  Entrar mesmo assim →
                </Button>
              </HStack>
            </VStack>
          )}

          {status === "ready" && (
            <Button
              size="lg"
              h="56px"
              px={8}
              borderRadius="12px"
              bgGradient={`linear(to-r, ${C.blue}, ${C.purple}, ${C.pink})`}
              color="white"
              fontWeight={600}
              fontSize="16px"
              rightIcon={<ArrowForwardIcon />}
              _hover={{ filter: "brightness(1.12)", transform: "translateY(-1px)" }}
              transition="all .2s"
              boxShadow={`0 16px 50px ${C.purple}55`}
              onClick={() => { window.location.href = dashboardUrl; }}
            >
              Entrar no Centro de Comando
            </Button>
          )}
        </Box>
      </VStack>
    </OnboardingLayout>
  );
};

export default LaunchPad;
