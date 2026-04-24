import React, { useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  FormControl,
  FormLabel,
  HStack,
  SimpleGrid,
  Text,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import {
  ApprovalTaskId,
  NotifyChannel,
  RoutineId,
  useOnboarding,
} from "../state";
import { patchOnboardingState } from "../services/onboardingService";

const CHANNELS: { id: NotifyChannel; label: string }[] = [
  { id: "email", label: "E-mail" },
  { id: "whatsapp", label: "WhatsApp" },
  { id: "app", label: "No app" },
];

// Tasks the agents can perform. User ticks the ones that should require approval.
const TASKS: { id: ApprovalTaskId; label: string; desc: string }[] = [
  { id: "send_email", label: "Enviar e-mails", desc: "Campanhas e follow-ups para clientes." },
  { id: "send_message", label: "Enviar mensagens", desc: "WhatsApp e chats com clientes." },
  { id: "book_appointment", label: "Marcar compromissos", desc: "Reuniões, visitas, agendamentos." },
  { id: "supplier_order", label: "Fazer pedidos a fornecedores", desc: "Reposição de estoque, cotações." },
  { id: "make_payment", label: "Realizar pagamentos", desc: "Contas a pagar, transferências." },
  { id: "publish_content", label: "Publicar em redes sociais", desc: "Posts, stories, campanhas." },
  { id: "update_prices", label: "Alterar preços e catálogo", desc: "Promoções, reajustes." },
  { id: "share_report", label: "Compartilhar relatórios", desc: "Envio automático a clientes e equipe." },
];

// Built-in routines the user can activate out of the box.
const ROUTINES: { id: RoutineId; label: string; desc: string; color: string; emoji: string }[] = [
  {
    id: "daily_sales_digest",
    label: "Resumo diário de vendas",
    desc: "Todo dia às 8h, um panorama do que vendeu e do que está em risco.",
    color: C.blue,
    emoji: "📈",
  },
  {
    id: "low_stock_alert",
    label: "Alerta de estoque baixo",
    desc: "Aviso automático quando um SKU atinge o ponto de reposição.",
    color: C.orange,
    emoji: "📦",
  },
  {
    id: "stale_lead_followup",
    label: "Follow-up de leads parados",
    desc: "Retoma contato quando um lead fica sem resposta por 3 dias.",
    color: C.pink,
    emoji: "💬",
  },
  {
    id: "overdue_invoice",
    label: "Cobrança de inadimplentes",
    desc: "Lembretes educados escalando até 2º aviso e aviso final.",
    color: C.purple,
    emoji: "💳",
  },
  {
    id: "weekly_performance",
    label: "Relatório semanal",
    desc: "Toda segunda, o resumo da semana com KPIs e insights.",
    color: C.cyan,
    emoji: "📊",
  },
  {
    id: "supplier_quote",
    label: "Cotação com fornecedores",
    desc: "Ao detectar reposição, envia RFQ aos fornecedores já mapeados.",
    color: C.green,
    emoji: "🏷️",
  },
  {
    id: "appointment_reminder",
    label: "Lembrete de compromissos",
    desc: "Avisos 24h e 1h antes para clientes e equipe.",
    color: C.yellow,
    emoji: "⏰",
  },
  {
    id: "churn_signal",
    label: "Sinal de churn",
    desc: "Alerta quando um cliente recorrente reduz o ritmo de compras.",
    color: C.red,
    emoji: "⚠️",
  },
];

// Step 5 – Command Rules (HITL setup). 90%.
const CommandRules: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();
  const [approvalTasks, setApprovalTasks] = useState<ApprovalTaskId[]>(state.approvalTasks);
  const [routines, setRoutines] = useState<RoutineId[]>(state.routines);
  const [channel, setChannel] = useState<NotifyChannel>(state.notifyChannel);
  const [saving, setSaving] = useState(false);

  const toggleTask = (id: ApprovalTaskId) =>
    setApprovalTasks((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const toggleRoutine = (id: RoutineId) =>
    setRoutines((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const handleNext = async () => {
    if (saving) return;
    const patch = { approvalTasks, routines, notifyChannel: channel };
    update(patch);
    setSaving(true);
    try {
      // No client_routines rows yet — provisioning happens atomically in
      // LaunchPad bootstrap. We only persist the selection.
      await patchOnboardingState(patch);
      navigate("/onboarding/launch");
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
    <OnboardingLayout progress={90}>
      <StepHeader
        eyebrow="Passo 4 de 4"
        title={
          <>
            Você define os{" "}
            <Text
              as="span"
              fontStyle="italic"
              bgGradient={`linear(to-r, ${C.pinkLight}, ${C.orangeLight})`}
              bgClip="text"
            >
              limites
            </Text>
            . Os agentes respeitam.
          </>
        }
        subtitle="Regras simples que governam todo o time. Podem ser revistas a qualquer momento."
      />

      <VStack
        spacing={7}
        bg={C.surface}
        border="1px solid"
        borderColor={C.borderStrong}
        borderRadius="18px"
        p={{ base: 6, md: 7 }}
        align="stretch"
      >
        <FormControl>
          <FormLabel color="white" fontSize="14px" fontWeight={600} mb={1}>
            Quais tarefas exigem sua aprovação?
          </FormLabel>
          <Text fontSize="12px" color={C.textMuted} mb={3}>
            Marque as ações que só devem acontecer depois que você der o OK. As demais os agentes executam sozinhos.
          </Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2.5}>
            {TASKS.map((t) => {
              const active = approvalTasks.includes(t.id);
              return (
                <Box
                  key={t.id}
                  as="button"
                  type="button"
                  onClick={() => toggleTask(t.id)}
                  textAlign="left"
                  bg={active ? `${C.blue}14` : "rgba(255,255,255,0.02)"}
                  border="1px solid"
                  borderColor={active ? C.blue : C.borderStrong}
                  borderRadius="12px"
                  p={3.5}
                  transition="all .15s"
                  _hover={{ borderColor: active ? C.blue : C.textDim }}
                >
                  <HStack align="start" spacing={3}>
                    <Checkbox
                      isChecked={active}
                      pointerEvents="none"
                      colorScheme="blue"
                      mt={0.5}
                    />
                    <Box>
                      <Text fontSize="13px" fontWeight={600} color="white">
                        {t.label}
                      </Text>
                      <Text fontSize="12px" color={C.textDim} lineHeight={1.4}>
                        {t.desc}
                      </Text>
                    </Box>
                  </HStack>
                </Box>
              );
            })}
          </SimpleGrid>
        </FormControl>

        <FormControl>
          <FormLabel color="white" fontSize="14px" fontWeight={600} mb={1}>
            Rotinas prontas para ligar
          </FormLabel>
          <Text fontSize="12px" color={C.textMuted} mb={3}>
            Fluxos testados que começam a rodar hoje. Você pode editar, pausar ou criar novos depois.
          </Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2.5}>
            {ROUTINES.map((r) => {
              const active = routines.includes(r.id);
              return (
                <Box
                  key={r.id}
                  as="button"
                  type="button"
                  onClick={() => toggleRoutine(r.id)}
                  textAlign="left"
                  bg={active ? `${r.color}14` : "rgba(255,255,255,0.02)"}
                  border="1px solid"
                  borderColor={active ? r.color : C.borderStrong}
                  borderRadius="12px"
                  p={4}
                  transition="all .15s"
                  _hover={{ borderColor: active ? r.color : C.textDim }}
                >
                  <HStack justify="space-between" align="start" mb={1}>
                    <HStack spacing={2}>
                      <Text fontSize="18px" lineHeight={1}>
                        {r.emoji}
                      </Text>
                      <Text fontSize="13px" fontWeight={600} color="white">
                        {r.label}
                      </Text>
                    </HStack>
                    <Text
                      fontSize="10px"
                      fontWeight={600}
                      letterSpacing="0.1em"
                      textTransform="uppercase"
                      color={active ? r.color : C.textMuted}
                    >
                      {active ? "Ativa" : "Ligar"}
                    </Text>
                  </HStack>
                  <Text fontSize="12px" color={C.textDim} lineHeight={1.45}>
                    {r.desc}
                  </Text>
                </Box>
              );
            })}
          </SimpleGrid>
        </FormControl>

        <FormControl>
          <FormLabel color="white" fontSize="14px" fontWeight={600} mb={2}>
            Canal de notificação
          </FormLabel>
          <HStack spacing={2.5}>
            {CHANNELS.map((c) => {
              const active = channel === c.id;
              return (
                <Button
                  key={c.id}
                  flex={1}
                  size="md"
                  h="44px"
                  variant="outline"
                  borderColor={active ? C.blue : C.borderStrong}
                  bg={active ? `${C.blue}22` : "rgba(255,255,255,0.02)"}
                  color="white"
                  fontWeight={500}
                  _hover={{ borderColor: C.blueLight }}
                  onClick={() => setChannel(c.id)}
                >
                  {c.label}
                </Button>
              );
            })}
          </HStack>
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
        <Button
          h="48px"
          px={7}
          bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
          color="white"
          fontWeight={600}
          rightIcon={<ArrowForwardIcon />}
          _hover={{ filter: "brightness(1.1)" }}
          onClick={handleNext}
          isLoading={saving}
          loadingText="Salvando…"
        >
          Finalizar
        </Button>
      </HStack>
    </OnboardingLayout>
  );
};

export default CommandRules;
