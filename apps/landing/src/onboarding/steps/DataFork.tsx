import React, { useEffect, useState } from "react";
import {
  Badge,
  Box,
  Button,
  HStack,
  Icon,
  SimpleGrid,
  Text,
  useToast,
  VStack,
} from "@chakra-ui/react";
import {
  ArrowForwardIcon,
  CheckCircleIcon,
  ExternalLinkIcon,
  WarningTwoIcon,
} from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import { DataPath, useOnboarding } from "../state";
import { supabase } from "../../lib/supabase";
import {
  captureDriveToken,
  patchOnboardingState,
} from "../services/onboardingService";

// Each system maps to a connector slug recognized by AdminFontesPage's ?connect= param.
const SYSTEMS: {
  id: string;
  label: string;
  desc: string;
  connectSlug: string;
  accent: string;
}[] = [
  { id: "shopify", label: "Shopify", desc: "Pedidos, produtos, clientes.", connectSlug: "shopify", accent: "#96BF48" },
  { id: "vtex", label: "VTEX", desc: "Catálogo e vendas completas.", connectSlug: "vtex", accent: "#F71963" },
  { id: "loja_integrada", label: "Loja Integrada", desc: "Vendas da sua loja Integrada.", connectSlug: "loja_integrada", accent: "#00A650" },
  { id: "bigquery", label: "Google BigQuery", desc: "Data warehouse próprio.", connectSlug: "bigquery", accent: "#4285F4" },
  { id: "postgres", label: "PostgreSQL", desc: "Banco transacional.", connectSlug: "postgresql", accent: "#336791" },
  { id: "mysql", label: "MySQL", desc: "Banco transacional.", connectSlug: "mysql", accent: "#4479A1" },
];

// Optional: pre-configured dashboard URL (defaults to same-origin /dashboard).
const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {};
const DASHBOARD_BASE = env.VITE_DASHBOARD_URL || "/dashboard";

// Step 3 – The Fork. No forced connections. 50% progress.
const DataFork: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();
  const [path, setPath] = useState<DataPath>(state.dataPath);
  const [systems, setSystems] = useState<string[]>(state.systems);
  const [csvUploaded, setCsvUploaded] = useState(state.csvUploaded);
  const [driveConnected, setDriveConnected] = useState(state.googleDriveConnected);
  const [driveLoading, setDriveLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  // Mapping review hint pushed back from the dashboard's connector modal.
  // Shape: { credentialId: string; connector?: string }
  const [mappingReview, setMappingReview] = useState<{
    credentialId: string;
    connector?: string;
  } | null>(null);

  // If we're coming back from a Google OAuth redirect (?drive=connected),
  // hand the provider refresh token off to the edge function that
  // encrypts and stores it in `integration_tokens`. Only flip the local
  // flag after the server confirms capture.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("drive") !== "connected") return;

    let cancelled = false;
    // Strip ?drive=connected eagerly so a reload doesn't re-run capture.
    const url = new URL(window.location.href);
    url.search = "";
    window.history.replaceState({}, "", url.toString());

    (async () => {
      const { connected } = await captureDriveToken();
      if (cancelled) return;
      if (connected) {
        setDriveConnected(true);
        setPath("files");
        update({ googleDriveConnected: true, dataPath: "files" });
        toast({
          title: "Google Drive conectado",
          description:
            "Seu agente já pode ler planilhas e documentos do Drive.",
          status: "success",
          duration: 4000,
          isClosable: true,
        });
      } else {
        toast({
          title: "Não foi possível salvar o acesso ao Drive",
          description:
            "O login funcionou, mas não conseguimos guardar o token. Tente reconectar.",
          status: "warning",
          duration: 5000,
          isClosable: true,
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [toast, update]);

  // Parse `?connector_synced=` / `?mapping_review=` hints set by the dashboard
  // connector modal. Strip them from the URL so a reload doesn't re-trigger.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const synced = params.get("connector_synced");
    const review = params.get("mapping_review");
    const reviewConnector = params.get("connector") || undefined;

    if (!synced && !review) return;

    if (synced) {
      const sys = synced.replace("postgresql", "postgres");
      setSystems((prev) => (prev.includes(sys) ? prev : [...prev, sys]));
      update({ dataPath: "systems" });
      toast({
        title: "Conector sincronizado",
        description: `A sincronização do ${synced} começou em segundo plano.`,
        status: "success",
        duration: 4000,
        isClosable: true,
      });
    }
    if (review) {
      setMappingReview({ credentialId: review, connector: reviewConnector });
    }

    const url = new URL(window.location.href);
    url.searchParams.delete("connector_synced");
    url.searchParams.delete("mapping_review");
    url.searchParams.delete("connector");
    window.history.replaceState({}, "", url.toString());
  }, [toast, update]);

  const toggleSystem = (id: string) =>
    setSystems((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setCsvUploaded(true);
  };

  const connectGoogleDrive = async () => {
    setDriveLoading(true);
    // Persist path before leaving the SPA.
    update({ dataPath: "files" });
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        // Supabase merges these with the provider's defaults.
        scopes:
          "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/spreadsheets.readonly",
        queryParams: {
          access_type: "offline",
          prompt: "consent",
        },
        redirectTo: `${window.location.origin}/onboarding/data?drive=connected`,
      },
    });
    if (error) {
      setDriveLoading(false);
      toast({
        title: "Não foi possível conectar o Drive",
        description: error.message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const openConnector = async (slug: string) => {
    // Flush the current path + selected systems synchronously so the
    // debounced autosave doesn't get cut off by the hard navigation.
    update({ dataPath: "systems", systems });
    try {
      await patchOnboardingState({ dataPath: "systems", systems });
    } catch {
      // Non-fatal: the dashboard's return-to-onboarding hook re-runs the
      // autosave loop on re-entry.
    }
    const url = `${DASHBOARD_BASE}/admin/fontes?connect=${encodeURIComponent(slug)}&return=${encodeURIComponent("/onboarding/data")}`;
    window.location.href = url;
  };

  const canContinue =
    path === "systems"
      ? systems.length > 0
      : path === "files"
        ? true
        : path === "scratch";

  const handleNext = async () => {
    if (saving) return;
    const patch = {
      dataPath: path,
      systems,
      csvUploaded,
      googleDriveConnected: driveConnected,
    };
    update(patch);
    setSaving(true);
    try {
      await patchOnboardingState(patch);
      navigate(path === "systems" ? "/onboarding/mapping" : "/onboarding/launch");
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
    <OnboardingLayout progress={50}>
      <StepHeader
        eyebrow="Passo 3 de 4"
        title={
          <>
            Qual é a sua{" "}
            <Text
              as="span"
              fontStyle="italic"
              bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink})`}
              bgClip="text"
            >
              realidade de dados
            </Text>
            ?
          </>
        }
        subtitle="Escolha o caminho que faz sentido hoje. Você pode adicionar mais depois."
      />

      {mappingReview && (
        <Box
          mb={5}
          p={4}
          borderRadius="14px"
          bg={`${C.yellow}14`}
          border="1px solid"
          borderColor={`${C.yellow}55`}
        >
          <HStack align="start" spacing={3}>
            <Icon as={WarningTwoIcon} color={C.yellow} mt="2px" />
            <VStack align="stretch" spacing={2} flex={1}>
              <Text fontSize="14px" fontWeight={600} color="white">
                Precisamos confirmar o mapeamento das colunas
              </Text>
              <Text fontSize="12px" color={C.textDim}>
                Conectamos {mappingReview.connector ?? "sua fonte"} com sucesso, mas algumas
                colunas precisam de revisão antes da sincronização. Confirme o mapeamento
                e voltaremos a sincronizar automaticamente.
              </Text>
              <HStack>
                <Button
                  size="sm"
                  bg={C.yellow}
                  color="#1a1a1a"
                  fontWeight={600}
                  borderRadius="full"
                  rightIcon={<ExternalLinkIcon boxSize={3} />}
                  _hover={{ filter: "brightness(1.05)" }}
                  onClick={() => {
                    const url = `${DASHBOARD_BASE}/admin/connectors/${mappingReview.credentialId}/mapping`;
                    window.location.href = url;
                  }}
                >
                  Confirmar mapeamento
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  color={C.textDim}
                  _hover={{ color: "white", bg: "rgba(255,255,255,0.04)" }}
                  onClick={() => setMappingReview(null)}
                >
                  Depois
                </Button>
              </HStack>
            </VStack>
          </HStack>
        </Box>
      )}

      <VStack spacing={4} align="stretch">
        <PathCard
          active={path === "systems"}
          accent={C.blue}
          onClick={() => setPath("systems")}
          label="Tenho sistemas"
          desc="Conecte agora mesmo. As credenciais ficam seguras, o agente começa a usar em minutos."
          rightBadge="1-tap"
        >
          {path === "systems" && (
            <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={2.5} mt={4}>
              {SYSTEMS.map((s) => {
                const selected = systems.includes(s.id);
                return (
                  <Box
                    key={s.id}
                    bg={selected ? `${s.accent}14` : "rgba(255,255,255,0.02)"}
                    border="1px solid"
                    borderColor={selected ? s.accent : C.borderStrong}
                    borderRadius="12px"
                    p={3.5}
                    transition="all .15s"
                    _hover={{ borderColor: selected ? s.accent : C.textDim }}
                  >
                    <HStack justify="space-between" align="start" mb={2}>
                      <Box
                        flex={1}
                        as="button"
                        type="button"
                        textAlign="left"
                        onClick={(e: React.MouseEvent) => {
                          e.stopPropagation();
                          toggleSystem(s.id);
                        }}
                      >
                        <HStack spacing={2} mb={0.5}>
                          <Box w="8px" h="8px" borderRadius="full" bg={s.accent} />
                          <Text fontSize="14px" fontWeight={600} color="white">
                            {s.label}
                          </Text>
                          {selected && (
                            <Badge
                              fontSize="9px"
                              letterSpacing="0.1em"
                              textTransform="uppercase"
                              bg={`${s.accent}22`}
                              color={s.accent}
                              borderRadius="6px"
                            >
                              Selecionado
                            </Badge>
                          )}
                        </HStack>
                        <Text fontSize="12px" color={C.textDim}>
                          {s.desc}
                        </Text>
                      </Box>
                    </HStack>
                    <Button
                      size="sm"
                      w="full"
                      h="34px"
                      variant="outline"
                      borderColor={C.borderStrong}
                      bg="rgba(255,255,255,0.03)"
                      color="white"
                      fontWeight={500}
                      rightIcon={<ExternalLinkIcon boxSize={3} />}
                      _hover={{ borderColor: s.accent, bg: `${s.accent}14` }}
                      onClick={(e) => {
                        e.stopPropagation();
                        openConnector(s.connectSlug);
                      }}
                    >
                      Conectar agora
                    </Button>
                  </Box>
                );
              })}
            </SimpleGrid>
          )}

          {path === "systems" && (
            <HStack spacing={2} mt={3} color={C.textMuted}>
              <Icon as={CheckCircleIcon} boxSize={3} color={C.green} />
              <Text fontSize="11px">
                Conexões são feitas na área de administração. Você volta para o onboarding ao terminar.
              </Text>
            </HStack>
          )}
        </PathCard>

        <PathCard
          active={path === "files"}
          accent={C.orange}
          onClick={() => setPath("files")}
          label="Trabalho com arquivos e planilhas"
          desc="Conecte seu Google Drive ou envie um CSV. O agente lê planilhas e documentos direto da fonte."
          rightBadge="opcional"
        >
          {path === "files" && (
            <VStack align="stretch" spacing={3} mt={4}>
              <Button
                h="48px"
                bg={driveConnected ? `${C.green}18` : "white"}
                color={driveConnected ? "white" : "#111"}
                fontWeight={600}
                border="1px solid"
                borderColor={driveConnected ? C.green : "transparent"}
                _hover={{
                  bg: driveConnected ? `${C.green}22` : "rgba(255,255,255,0.92)",
                }}
                isLoading={driveLoading}
                loadingText="Abrindo Google…"
                leftIcon={
                  driveConnected ? (
                    <CheckCircleIcon color={C.green} />
                  ) : (
                    <Box as="span" lineHeight={1}>
                      <GoogleDriveIcon />
                    </Box>
                  )
                }
                onClick={(e) => {
                  e.stopPropagation();
                  if (!driveConnected) connectGoogleDrive();
                }}
              >
                {driveConnected ? "Google Drive conectado" : "Conectar Google Drive"}
              </Button>

              <HStack spacing={3}>
                <Box flex={1} h="1px" bg={C.borderStrong} />
                <Text fontSize="11px" color={C.textMuted}>
                  ou
                </Text>
                <Box flex={1} h="1px" bg={C.borderStrong} />
              </HStack>

              <HStack spacing={3}>
                <Button
                  as="label"
                  htmlFor="csv-upload"
                  size="sm"
                  h="40px"
                  variant="outline"
                  borderColor={csvUploaded ? C.orange : C.borderStrong}
                  bg={csvUploaded ? `${C.orange}22` : "rgba(255,255,255,0.02)"}
                  color="white"
                  cursor="pointer"
                  leftIcon={csvUploaded ? <CheckCircleIcon /> : undefined}
                  _hover={{ borderColor: C.orangeLight }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {csvUploaded ? "Arquivo carregado" : "Enviar CSV/Excel"}
                </Button>
                <input
                  id="csv-upload"
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  style={{ display: "none" }}
                  onChange={handleFile}
                />
                <Text fontSize="12px" color={C.textMuted}>
                  ou continue sem enviar nada.
                </Text>
              </HStack>
            </VStack>
          )}
        </PathCard>

        <PathCard
          active={path === "scratch"}
          accent={C.purple}
          onClick={() => setPath("scratch")}
          label="Quero começar do zero"
          desc="Workspace em branco com templates e checklists prontos."
          rightBadge="templates"
        />

        <Text color={C.textMuted} fontSize="12px" pt={1}>
          Seus dados são seus. LGPD by design.
        </Text>
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
          isDisabled={!canContinue}
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

interface PathCardProps {
  active: boolean;
  accent: string;
  onClick: () => void;
  label: string;
  desc: string;
  rightBadge?: string;
  children?: React.ReactNode;
}

const PathCard: React.FC<PathCardProps> = ({ active, accent, onClick, label, desc, rightBadge, children }) => (
  <Box
    as="button"
    onClick={onClick}
    textAlign="left"
    bg={active ? `${accent}14` : C.surface}
    border="1px solid"
    borderColor={active ? accent : C.borderStrong}
    borderRadius="16px"
    p={{ base: 5, md: 6 }}
    transition="all .15s"
    _hover={{ borderColor: active ? accent : C.textDim, transform: "translateY(-1px)" }}
    position="relative"
  >
    <HStack justify="space-between" align="start">
      <Box flex={1}>
        <Text fontSize="17px" fontWeight={600} color="white" mb={1}>
          {label}
        </Text>
        <Text fontSize="14px" color={C.textDim} lineHeight={1.5}>
          {desc}
        </Text>
      </Box>
      {rightBadge && (
        <Text
          fontSize="10px"
          fontWeight={600}
          letterSpacing="0.1em"
          textTransform="uppercase"
          px={2}
          py={1}
          borderRadius="6px"
          bg={`${accent}22`}
          color={accent}
        >
          {rightBadge}
        </Text>
      )}
    </HStack>
    {children}
  </Box>
);

const GoogleDriveIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 87.3 78" aria-hidden="true">
    <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3L27.5 53H0c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
    <path d="M43.65 25 29.9 1.2c-1.35.8-2.5 1.9-3.3 3.3L1.2 47.5c-.8 1.4-1.2 2.95-1.2 4.5h27.5z" fill="#00ac47"/>
    <path d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.5l5.85 11.5z" fill="#ea4335"/>
    <path d="M43.65 25 57.4 1.2C56.05.4 54.5 0 52.9 0h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
    <path d="M59.8 53H27.5L13.75 76.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
    <path d="m73.4 26.5-12.75-22c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25l16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
  </svg>
);

export default DataFork;
