import React, { useEffect, useMemo, useState } from "react";
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Radio,
  RadioGroup,
  Select,
  SimpleGrid,
  Skeleton,
  Switch,
  Text,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import {
  ALL_AGENTS,
  KpiDimension,
  PrimaryFocus,
  RoutineId,
  Vertical,
  useOnboarding,
} from "../state";
import { mapBusinessDNAToCompanyProfile } from "../mappers";
import {
  fetchWebsiteIntel,
  listKpiCatalog,
  patchOnboardingState,
  runBootstrap,
  saveContextSections,
  setClientDimensionKpis,
  updateClientColumn,
} from "../services/onboardingService";

const VERTICALS: { value: Exclude<Vertical, null>; label: string }[] = [
  { value: "ecommerce", label: "E-commerce / Varejo" },
  { value: "servicos", label: "Serviços" },
  { value: "industria", label: "Indústria" },
  { value: "saude", label: "Saúde" },
  { value: "educacao", label: "Educação" },
  { value: "financeiro", label: "Financeiro" },
  { value: "agro", label: "Agro" },
  { value: "outro", label: "Outro" },
];

const FOCUS_OPTIONS: Array<{ value: Exclude<PrimaryFocus, null>; label: string }> = [
  { value: "vendas", label: "Vendas crescer" },
  { value: "operacao", label: "Operação travada" },
  { value: "atendimento", label: "Atendimento ruim" },
  { value: "estoque", label: "Estoque sangrando" },
  { value: "outro", label: "Outro" },
];

const DIMENSIONS: KpiDimension[] = ["commercial", "inventory", "supply", "finance"];

const DEFAULT_ROUTINES_BY_FOCUS: Record<Exclude<PrimaryFocus, null>, RoutineId[]> = {
  vendas: ["daily_sales_digest", "stale_lead_followup", "weekly_performance"],
  operacao: ["weekly_performance", "supplier_quote", "appointment_reminder"],
  atendimento: ["appointment_reminder", "stale_lead_followup", "daily_sales_digest"],
  estoque: ["low_stock_alert", "supplier_quote", "weekly_performance"],
  outro: ["daily_sales_digest", "weekly_performance", "low_stock_alert"],
};

const STRICT_APPROVAL_TASKS = [
  "send_email",
  "send_message",
  "book_appointment",
  "supplier_order",
  "make_payment",
  "publish_content",
  "update_prices",
  "share_report",
] as const;

const LIGHT_APPROVAL_TASKS = ["supplier_order", "make_payment", "update_prices"] as const;

const dimensionLabel = (d: KpiDimension) => {
  if (d === "commercial") return "Comercial";
  if (d === "inventory") return "Estoque";
  if (d === "supply") return "Compras";
  return "Financeiro";
};

const toArrayUnique = <T extends string>(arr: T[], max: number): T[] =>
  Array.from(new Set(arr)).slice(0, max);

const PackageProposal: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();

  const [empresa, setEmpresa] = useState(state.empresa);
  const [vertical, setVertical] = useState<Vertical>(state.vertical);
  const [porte, setPorte] = useState(state.porte);
  const [primaryFocus, setPrimaryFocus] = useState<PrimaryFocus>(state.primaryFocus);
  const [alwaysRequireApproval, setAlwaysRequireApproval] = useState(state.alwaysRequireApproval);
  const [agents, setAgents] = useState<string[]>(state.agents.length ? state.agents : ["analytics", "crm", "inventory"]);
  const [routines, setRoutines] = useState<RoutineId[]>(
    state.routines.length ? state.routines : DEFAULT_ROUTINES_BY_FOCUS.outro,
  );
  const [kpiSelections, setKpiSelections] = useState<Partial<Record<KpiDimension, string[]>>>(
    state.kpiSelections ?? {},
  );
  const [availableKpis, setAvailableKpis] = useState<Partial<Record<KpiDimension, Array<{ slug: string; label: string }>>>>({});
  const [loadingIntel, setLoadingIntel] = useState(false);
  const [saving, setSaving] = useState(false);

  const canContinue = empresa.trim().length > 1 && !!vertical && !!primaryFocus;

  useEffect(() => {
    let cancelled = false;

    const loadDefaults = async () => {
      const rows = await Promise.all(
        DIMENSIONS.map(async (dimension) => {
          const entries = await listKpiCatalog(dimension, false);
          const normalized = entries.map((e) => ({ slug: e.slug, label: e.label }));
          return { dimension, entries: normalized };
        }),
      );
      if (cancelled) return;

      const nextAvailable: Partial<Record<KpiDimension, Array<{ slug: string; label: string }>>> = {};
      const nextSelection: Partial<Record<KpiDimension, string[]>> = { ...(state.kpiSelections ?? {}) };

      rows.forEach(({ dimension, entries }) => {
        nextAvailable[dimension] = entries;
        if (!nextSelection[dimension] || nextSelection[dimension]?.length === 0) {
          nextSelection[dimension] = entries.slice(0, 5).map((x) => x.slug);
        }
      });

      setAvailableKpis(nextAvailable);
      setKpiSelections(nextSelection);
    };

    void loadDefaults().catch((err) => {
      console.warn("[onboarding] defaults load failed", err);
    });

    return () => {
      cancelled = true;
    };
  }, [state.kpiSelections]);

  useEffect(() => {
    if (!state.website?.trim()) return;
    let cancelled = false;

    const loadIntel = async () => {
      setLoadingIntel(true);
      const timeout = new Promise<null>((resolve) => {
        setTimeout(() => resolve(null), 6000);
      });
      const intel = await Promise.race([fetchWebsiteIntel(state.website), timeout]);
      if (cancelled) return;
      setLoadingIntel(false);
      if (!intel) return;

      if (intel.company_name) setEmpresa((prev) => prev || intel.company_name || "");

      if (intel.vertical && !vertical) {
        const match = VERTICALS.find((v) => v.value === intel.vertical);
        if (match) setVertical(match.value);
      }

      if (intel.suggested_size && !porte) setPorte(intel.suggested_size);

      if (intel.suggested_agents && intel.suggested_agents.length > 0) {
        setAgents(toArrayUnique(intel.suggested_agents, 6));
      }

      if (intel.suggested_routines && intel.suggested_routines.length > 0) {
        setRoutines(toArrayUnique(intel.suggested_routines as RoutineId[], 5));
      }

      if (intel.suggested_kpis) {
        setKpiSelections((prev) => {
          const next = { ...prev };
          DIMENSIONS.forEach((d) => {
            const suggested = intel.suggested_kpis?.[d];
            if (suggested && suggested.length > 0) next[d] = toArrayUnique(suggested, 5);
          });
          return next;
        });
      }
    };

    void loadIntel().catch((err) => {
      console.warn("[onboarding] website intel failed", err);
      setLoadingIntel(false);
    });

    return () => {
      cancelled = true;
    };
  }, [porte, state.website, vertical]);

  useEffect(() => {
    if (!primaryFocus) return;
    setRoutines((prev) => (prev.length > 0 ? prev : DEFAULT_ROUTINES_BY_FOCUS[primaryFocus]));
  }, [primaryFocus]);

  const approvalTasks = useMemo(
    () => (alwaysRequireApproval ? [...STRICT_APPROVAL_TASKS] : [...LIGHT_APPROVAL_TASKS]),
    [alwaysRequireApproval],
  );

  const toggleAgent = (id: string) => {
    setAgents((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleRoutine = (id: RoutineId) => {
    setRoutines((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleKpi = (dimension: KpiDimension, slug: string) => {
    setKpiSelections((prev) => {
      const current = prev[dimension] ?? [];
      if (current.includes(slug)) {
        return { ...prev, [dimension]: current.filter((s) => s !== slug) };
      }
      if (current.length >= 5) return prev;
      return { ...prev, [dimension]: [...current, slug] };
    });
  };

  const saveAndLaunch = async () => {
    if (saving || !canContinue) return;
    setSaving(true);

    const nextState = {
      ...state,
      empresa: empresa.trim(),
      vertical,
      porte: porte.trim(),
      primaryFocus,
      dataPath: state.dataPath ?? "scratch",
      agents,
      routines,
      alwaysRequireApproval,
      approvalTasks,
      kpiSelections,
    };

    update(nextState);

    try {
      await Promise.all([
        patchOnboardingState({
          empresa: nextState.empresa,
          vertical: nextState.vertical,
          porte: nextState.porte,
          primaryFocus: nextState.primaryFocus,
          dataPath: nextState.dataPath,
          agents: nextState.agents,
          routines: nextState.routines,
          alwaysRequireApproval: nextState.alwaysRequireApproval,
          approvalTasks: nextState.approvalTasks,
          kpiSelections: nextState.kpiSelections,
        }),
        saveContextSections({
          company_profile: {
            ...mapBusinessDNAToCompanyProfile(nextState),
            core_values: [],
          },
        }),
        updateClientColumn("nome_empresa", nextState.empresa || null),
      ]);

      await Promise.all(
        DIMENSIONS.map(async (dimension) => {
          const slugs = nextState.kpiSelections[dimension] ?? [];
          await setClientDimensionKpis(dimension, slugs);
        }),
      );

      await runBootstrap(nextState);

      const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {};
      const dashboardUrl = env.VITE_DASHBOARD_URL || "/dashboard";
      window.location.href = dashboardUrl;
    } catch (err) {
      toast({
        title: "Não foi possível concluir o onboarding",
        description: err instanceof Error ? err.message : "Tente novamente em instantes.",
        status: "error",
        duration: 6000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <OnboardingLayout progress={75}>
      <StepHeader
        eyebrow="Passo 2 de 3"
        title={
          <>
            Pacote{" "}
            <Text
              as="span"
              fontStyle="italic"
              bgGradient={`linear(to-r, ${C.purpleLight}, ${C.pink})`}
              bgClip="text"
            >
              sugerido
            </Text>
            para começar hoje
          </>
        }
        subtitle="Revise contexto, confirme foco e ajuste agentes/rotinas/KPIs."
      />

      <VStack spacing={5} align="stretch">
        <Box bg={C.surface} border="1px solid" borderColor={C.borderStrong} borderRadius="16px" p={5}>
          <Text fontSize="12px" color={C.textMuted} mb={3} textTransform="uppercase" letterSpacing="0.1em">
            Achei isto sobre vocês
          </Text>

          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
            <FormControl isRequired>
              <FormLabel color="white" fontSize="12px">Empresa</FormLabel>
              <Input value={empresa} onChange={(e) => setEmpresa(e.target.value)} />
            </FormControl>
            <FormControl isRequired>
              <FormLabel color="white" fontSize="12px">Setor</FormLabel>
              <Select
                value={vertical ?? ""}
                onChange={(e) => setVertical((e.target.value || null) as Vertical)}
                placeholder="Selecione"
                sx={{ option: { background: C.surface, color: "white" } }}
              >
                {VERTICALS.map((v) => (
                  <option key={v.value} value={v.value}>{v.label}</option>
                ))}
              </Select>
            </FormControl>
            <FormControl>
              <FormLabel color="white" fontSize="12px">Porte</FormLabel>
              <Select
                value={porte}
                onChange={(e) => setPorte(e.target.value)}
                placeholder="Selecione"
                sx={{ option: { background: C.surface, color: "white" } }}
              >
                <option value="solo">Autônomo / Solo</option>
                <option value="micro">Até 10 pessoas</option>
                <option value="pequena">11 a 50 pessoas</option>
                <option value="media">51 a 250 pessoas</option>
                <option value="grande">Mais de 250 pessoas</option>
              </Select>
            </FormControl>
            <FormControl isRequired>
              <FormLabel color="white" fontSize="12px">Foco principal</FormLabel>
              <RadioGroup value={primaryFocus ?? ""} onChange={(v) => setPrimaryFocus(v as PrimaryFocus)}>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2}>
                  {FOCUS_OPTIONS.map((opt) => (
                    <Radio key={opt.value} value={opt.value}>{opt.label}</Radio>
                  ))}
                </SimpleGrid>
              </RadioGroup>
            </FormControl>
          </SimpleGrid>
        </Box>

        <Box bg={C.surface} border="1px solid" borderColor={C.borderStrong} borderRadius="16px" p={5}>
          <Text fontSize="13px" fontWeight={600} color="white" mb={3}>Agentes</Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2.5}>
            {ALL_AGENTS.map((a) => (
              <HStack
                key={a.id}
                spacing={3}
                p={2.5}
                borderRadius="12px"
                border="1px solid"
                borderColor={agents.includes(a.id) ? `${a.color}66` : C.borderStrong}
                bg={agents.includes(a.id) ? `${a.color}14` : "rgba(255,255,255,0.02)"}
                onClick={() => toggleAgent(a.id)}
                cursor="pointer"
              >
                <Checkbox isChecked={agents.includes(a.id)} pointerEvents="none" colorScheme="purple" />
                <Box>
                  <Text fontSize="13px" color="white" fontWeight={600}>{a.name}</Text>
                  <Text fontSize="12px" color={C.textDim}>{a.value}</Text>
                </Box>
              </HStack>
            ))}
          </SimpleGrid>
        </Box>

        <Box bg={C.surface} border="1px solid" borderColor={C.borderStrong} borderRadius="16px" p={5}>
          <Text fontSize="13px" fontWeight={600} color="white" mb={3}>Rotinas</Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2.5}>
            {([
              { id: "daily_sales_digest", label: "Resumo diário de vendas" },
              { id: "low_stock_alert", label: "Alerta de estoque baixo" },
              { id: "stale_lead_followup", label: "Follow-up de leads" },
              { id: "overdue_invoice", label: "Cobrança de inadimplentes" },
              { id: "weekly_performance", label: "Relatório semanal" },
              { id: "supplier_quote", label: "Cotação com fornecedores" },
            ] as Array<{ id: RoutineId; label: string }>).map((r) => (
              <HStack
                key={r.id}
                spacing={3}
                p={2.5}
                borderRadius="12px"
                border="1px solid"
                borderColor={routines.includes(r.id) ? `${C.cyan}66` : C.borderStrong}
                bg={routines.includes(r.id) ? `${C.cyan}14` : "rgba(255,255,255,0.02)"}
                onClick={() => toggleRoutine(r.id)}
                cursor="pointer"
              >
                <Checkbox isChecked={routines.includes(r.id)} pointerEvents="none" colorScheme="cyan" />
                <Text fontSize="13px" color="white">{r.label}</Text>
              </HStack>
            ))}
          </SimpleGrid>
        </Box>

        <Box bg={C.surface} border="1px solid" borderColor={C.borderStrong} borderRadius="16px" p={5}>
          <HStack justify="space-between" mb={3}>
            <Text fontSize="13px" fontWeight={600} color="white">KPIs do painel (até 5 por dimensão)</Text>
            {loadingIntel && (
              <HStack spacing={2}>
                <Skeleton height="10px" width="56px" />
                <Text fontSize="11px" color={C.textMuted}>ajustando…</Text>
              </HStack>
            )}
          </HStack>

          <Accordion allowMultiple defaultIndex={[0]}>
            {DIMENSIONS.map((dimension) => {
              const list = availableKpis[dimension] ?? [];
              const selected = kpiSelections[dimension] ?? [];
              return (
                <AccordionItem key={dimension} borderColor={C.borderStrong}>
                  <AccordionButton>
                    <Box flex="1" textAlign="left">
                      <Text color="white" fontSize="13px" fontWeight={600}>
                        {dimensionLabel(dimension)}
                      </Text>
                      <Text color={C.textMuted} fontSize="11px">{selected.length}/5 selecionados</Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel pb={4}>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2}>
                      {list.map((kpi) => (
                        <HStack
                          key={kpi.slug}
                          spacing={2.5}
                          p={2}
                          borderRadius="10px"
                          border="1px solid"
                          borderColor={selected.includes(kpi.slug) ? `${C.blue}66` : C.borderStrong}
                          bg={selected.includes(kpi.slug) ? `${C.blue}14` : "rgba(255,255,255,0.02)"}
                          onClick={() => toggleKpi(dimension, kpi.slug)}
                          cursor="pointer"
                        >
                          <Checkbox isChecked={selected.includes(kpi.slug)} pointerEvents="none" colorScheme="blue" />
                          <Text fontSize="12px" color="white">{kpi.label}</Text>
                        </HStack>
                      ))}
                    </SimpleGrid>
                  </AccordionPanel>
                </AccordionItem>
              );
            })}
          </Accordion>
        </Box>

        <Box bg={C.surface} border="1px solid" borderColor={C.borderStrong} borderRadius="16px" p={5}>
          <Text fontSize="13px" fontWeight={600} color="white" mb={2}>
            Aprovação de ações externas
          </Text>
          <HStack justify="space-between">
            <Box>
              <Text color="white" fontSize="13px">Sempre pedir aprovação?</Text>
              <Text color={C.textMuted} fontSize="12px">
                Se desligado, o Blu pede aprovação apenas nas ações de maior risco.
              </Text>
            </Box>
            <Switch
              isChecked={alwaysRequireApproval}
              onChange={(e) => setAlwaysRequireApproval(e.target.checked)}
              colorScheme="purple"
            />
          </HStack>
        </Box>
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
              setAgents(["analytics", "crm", "inventory"]);
              setRoutines(DEFAULT_ROUTINES_BY_FOCUS[primaryFocus ?? "outro"]);
            }}
          >
            Ajustar tudo
          </Button>
          <Button
            h="48px"
            px={7}
            bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
            color="white"
            fontWeight={600}
            rightIcon={<ArrowForwardIcon />}
            _hover={{ filter: "brightness(1.1)" }}
            isDisabled={!canContinue || agents.length === 0}
            isLoading={saving}
            loadingText="Ativando…"
            onClick={() => {
              void saveAndLaunch();
            }}
          >
            Vamos com isto
          </Button>
        </HStack>
      </HStack>
    </OnboardingLayout>
  );
};

export default PackageProposal;
