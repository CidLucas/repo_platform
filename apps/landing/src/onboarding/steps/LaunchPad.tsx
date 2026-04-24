import React, { useEffect, useMemo, useRef, useState } from "react";
import { Box, Button, HStack, Spinner, Text, VStack, useToast } from "@chakra-ui/react";
import { ArrowForwardIcon, CheckCircleIcon, WarningTwoIcon } from "@chakra-ui/icons";
import { OnboardingLayout } from "../OnboardingLayout";
import { C } from "../tokens";
import { ALL_AGENTS, useOnboarding } from "../state";
import { runBootstrap } from "../services/onboardingService";

type BootstrapStatus = "running" | "ready" | "error";

// Step 6 – Launch Pad. First value. Progress bar disappears.
const LaunchPad: React.FC = () => {
  const { state } = useOnboarding();
  const toast = useToast();
  const [status, setStatus] = useState<BootstrapStatus>("running");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  // Guard against React StrictMode double-invocation in dev; the RPC
  // itself is idempotent but we avoid extra network round-trips.
  const firedRef = useRef(false);

  const activatedAgents = useMemo(
    () => ALL_AGENTS.filter((a) => state.agents.includes(a.id)),
    [state.agents]
  );

  const checklist = useMemo(() => buildChecklist(state.dataPath, state.csvUploaded), [state]);

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
        title: "Não foi possível ativar seus agentes",
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

  const handleEnter = () => {
    if (status !== "ready") return;
    window.location.href = dashboardUrl;
  };

  return (
    <OnboardingLayout progress={null}>
      <VStack spacing={8} textAlign="center" pt={{ base: 2, md: 6 }}>
        <Text
          fontSize="12px"
          fontWeight={600}
          letterSpacing="0.14em"
          textTransform="uppercase"
          color={C.greenLight}
        >
          Tudo pronto
        </Text>
        <Box
          as="h1"
          fontFamily="'Playfair Display', serif"
          fontSize={{ base: "32px", md: "44px" }}
          fontWeight={500}
          letterSpacing="-0.02em"
          lineHeight={1.08}
          maxW="620px"
        >
          Seu{" "}
          <Text
            as="span"
            fontStyle="italic"
            bgGradient={`linear(to-r, ${C.greenLight}, ${C.cyan}, ${C.blueLight})`}
            bgClip="text"
          >
            centro de comando
          </Text>{" "}
          está pronto, {firstName(state.nome) || "sócio"}.
        </Box>
        <Text color={C.textDim} fontSize={{ base: "15px", md: "17px" }} maxW="520px" lineHeight={1.55}>
          {heroLine(state)}
        </Text>
      </VStack>

      <HStack
        mt={10}
        spacing={4}
        justify="center"
        align="stretch"
        flexWrap="wrap"
      >
        <SummaryCard title="Agentes ativos" accent={C.purple} value={`${activatedAgents.length}`}>
          <VStack align="stretch" spacing={1.5} mt={2}>
            {activatedAgents.slice(0, 4).map((a) => (
              <HStack key={a.id} spacing={2}>
                <Box w="6px" h="6px" borderRadius="full" bg={a.color} flexShrink={0} />
                <Text fontSize="12px" color={C.textDim} noOfLines={1}>
                  {a.name.replace("Agente de ", "")}
                </Text>
              </HStack>
            ))}
            {activatedAgents.length > 4 && (
              <Text fontSize="12px" color={C.textMuted}>
                + {activatedAgents.length - 4} outros
              </Text>
            )}
          </VStack>
        </SummaryCard>

        <SummaryCard
          title="Rotinas ativas"
          accent={C.pink}
          value={`${state.routines.length}`}
        >
          <Text fontSize="12px" color={C.textDim} mt={2}>
            {state.approvalTasks.length} tarefa{state.approvalTasks.length === 1 ? "" : "s"} com aprovação sua.
          </Text>
          <Text fontSize="12px" color={C.textDim}>
            Notificações por {channelLabel(state.notifyChannel)}
          </Text>
        </SummaryCard>

        <SummaryCard title="Dados" accent={C.blue} value={pathLabel(state.dataPath)}>
          <Text fontSize="12px" color={C.textDim} mt={2}>
            {pathHint(state)}
          </Text>
        </SummaryCard>
      </HStack>

      <Box
        mt={10}
        bg={C.surface}
        border="1px solid"
        borderColor={C.borderStrong}
        borderRadius="18px"
        p={{ base: 6, md: 7 }}
      >
        <Text fontSize="14px" fontWeight={600} color="white" mb={4}>
          Próximos passos
        </Text>
        <VStack align="stretch" spacing={2.5}>
          {checklist.map((item, i) => (
            <HStack key={i} spacing={3}>
              <CheckCircleIcon color={item.done ? C.green : C.textMuted} />
              <Text fontSize="14px" color={item.done ? C.textDim : "white"}>
                {item.label}
              </Text>
            </HStack>
          ))}
        </VStack>
      </Box>

      <HStack justify="center" mt={10}>
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
              Ativando seu time de agentes…
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
                  ? `Falha ao ativar: ${errorDetail}`
                  : "Não conseguimos ativar seus agentes agora."}
              </Text>
            </HStack>
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
            onClick={handleEnter}
          >
            Entrar no Centro de Comando
          </Button>
        )}
      </HStack>
    </OnboardingLayout>
  );
};

interface SummaryCardProps {
  title: string;
  value: string;
  accent: string;
  children?: React.ReactNode;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ title, value, accent, children }) => (
  <Box
    flex="1 1 200px"
    minW="200px"
    maxW="280px"
    bg={C.surface}
    border="1px solid"
    borderColor={C.borderStrong}
    borderRadius="16px"
    p={5}
    textAlign="left"
  >
    <Text fontSize="11px" fontWeight={600} letterSpacing="0.1em" textTransform="uppercase" color={accent}>
      {title}
    </Text>
    <Text fontSize="22px" fontWeight={700} color="white" mt={1}>
      {value}
    </Text>
    {children}
  </Box>
);

// ========== Helpers ==========

function firstName(full: string): string {
  return full.trim().split(/\s+/)[0] || "";
}

function channelLabel(c: string): string {
  if (c === "email") return "e-mail";
  if (c === "whatsapp") return "WhatsApp";
  return "no app";
}

function pathLabel(p: string | null): string {
  if (p === "systems") return "Sistemas";
  if (p === "files") return "Arquivos";
  if (p === "scratch") return "Do zero";
  return "—";
}

function pathHint(state: ReturnType<typeof useOnboarding>["state"]): string {
  if (state.dataPath === "systems") {
    return state.systems.length > 0
      ? `${state.systems.length} conector(es) selecionado(s)`
      : "Escolha seus conectores depois";
  }
  if (state.dataPath === "files") {
    if (state.googleDriveConnected) return "Google Drive conectado";
    return state.csvUploaded ? "Arquivo pronto para análise" : "Comece com templates em branco";
  }
  return "Templates prontos para começar";
}

function heroLine(state: ReturnType<typeof useOnboarding>["state"]): string {
  if (state.dataPath === "systems") {
    return "Enquanto você configurava, seus agentes se prepararam para ler seus dados.";
  }
  if (state.dataPath === "files" && state.csvUploaded) {
    return "Recebemos seu arquivo. Seu agente de Analytics já está com ele na mesa.";
  }
  return "Templates, checklists e agentes prontos para as primeiras jogadas.";
}

function buildChecklist(path: string | null, csvUploaded: boolean) {
  const base = [
    { label: "Conta criada e DNA do negócio capturado", done: true },
    { label: "Agentes ativados e regras de aprovação definidas", done: true },
  ];
  if (path === "systems") {
    return [
      ...base,
      { label: "Finalizar conexões OAuth dos sistemas", done: false },
      { label: "Revisar primeiras sugestões dos agentes", done: false },
    ];
  }
  if (path === "files") {
    return [
      ...base,
      { label: csvUploaded ? "Revisar preview do Analytics" : "Enviar planilha (quando quiser)", done: false },
      { label: "Personalizar templates sugeridos", done: false },
    ];
  }
  return [
    ...base,
    { label: "Escolher um template para começar", done: false },
    { label: "Convidar pessoas do seu time", done: false },
  ];
}

export default LaunchPad;
