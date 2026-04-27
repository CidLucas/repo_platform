import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Flex,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  Link,
  Grid,
  Container,
  Badge,
  useBreakpointValue,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  ModalCloseButton,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from "@chakra-ui/react";
import { ArrowForwardIcon, CheckCircleIcon } from "@chakra-ui/icons";

// ============================================================================
// DESIGN TOKENS (mirrored from the app — see docs/internal/landing-guideline.md §4)
// ============================================================================
const C = {
  bg: "#0b0c1e",
  bgSoft: "#0f1128",
  surface: "#151734",
  surfaceAlt: "#1a1c3d",
  border: "rgba(255,255,255,0.06)",
  borderStrong: "rgba(255,255,255,0.12)",
  textDim: "rgba(255,255,255,0.55)",
  textMuted: "rgba(255,255,255,0.4)",
  blue: "#3b82f6",
  blueLight: "#60a5fa",
  purple: "#a855f7",
  purpleLight: "#c084fc",
  green: "#10b981",
  greenLight: "#34d399",
  orange: "#f97316",
  orangeLight: "#fb923c",
  pink: "#ec4899",
  pinkLight: "#f472b6",
  yellow: "#eab308",
  red: "#ef4444",
};

// ============================================================================
// CONTENT (single source — easier to A/B test variants per §6 of the guideline)
// ============================================================================
const agentes = [
  {
    nome: "Agente de Análise",
    linha: "Pergunte em português, receba a resposta em segundos.",
    color: C.blue,
  },
  {
    nome: "Agente de Agenda",
    linha: "Sua segunda-feira, organizada.",
    color: C.purple,
  },
  {
    nome: "Agente de Compras",
    linha: "Cotações comparadas antes de comprar.",
    color: C.orange,
  },
  {
    nome: "Agente de Atendimento",
    linha: "Nenhum cliente esquecido.",
    color: C.pink,
  },
  {
    nome: "Agente de Documentos",
    linha: "Reuniões com pauta e resultado.",
    color: C.green,
  },
  {
    nome: "Agente de Planejamento",
    linha: "Metas claras, passos reais.",
    color: C.yellow,
  },
];

// Logo bar — placeholders are honest. Real logos go in once we have written
// permission per §2.2 of the guideline. Never fake logos.
const logosPlaceholders = [
  "Distribuidora",
  "Loja",
  "Indústria",
  "Serviços",
  "Atacado",
  "+ outras",
];

// Demo chips — must match what the seed tenant can actually answer.
const demoChips: Array<{ id: string; label: string; question: string }> = [
  {
    id: "vendas",
    label: "Quanto vendi essa semana?",
    question: "Quanto vendi essa semana?",
  },
  {
    id: "atrasos",
    label: "Quem ainda não pagou?",
    question: "Quem ainda não pagou esta semana?",
  },
  {
    id: "top",
    label: "Top 5 produtos do mês",
    question: "Quais foram os top 5 produtos do mês em receita?",
  },
];

// FAQ — keep min 5, max 8. See guideline §2.9.
const faq: Array<{ q: string; a: string }> = [
  {
    q: "Como meus dados ficam protegidos?",
    a: "LGPD by design. Cada empresa tem o ambiente isolado, criptografia em repouso, e seus dados nunca treinam modelos. Documentos marcados como pessoais não entram no contexto da empresa.",
  },
  {
    q: "Quanto tempo até ver resultado?",
    a: "Você experimenta em 60 segundos no modo demo, ainda nesta página. Ao conectar seus dados, os primeiros insights reais aparecem em até 1 dia.",
  },
  {
    q: "Posso cancelar quando quiser?",
    a: "Sim, sem multa, sem fidelidade. Cancela direto no painel.",
  },
  {
    q: "Quais sistemas o Blu integra?",
    a: "Planilhas (Excel, Google Sheets), Google Drive, WhatsApp, e e-commerces como Shopify, VTEX e Loja Integrada. Bling, Omie e Tiny estão em breve. Se o seu sistema não está aqui, fale com a gente.",
  },
  {
    q: "Quem aprova as ações dos agentes?",
    a: "Você ou quem você delegar. Toda ação que envolve dinheiro, fornecedor ou cliente passa por aprovação humana, com auditoria completa de quem aprovou e quando.",
  },
  {
    q: "Vai substituir meu ERP, Bling ou Omie?",
    a: "Não. Blu fica ao lado do seu sistema atual. Ele lê, organiza e sugere — quem emite NF-e e roda o financeiro continua sendo o seu ERP.",
  },
];

// Resultados — only ship cards we can defend. The guideline (§2.6) is explicit:
// 1 honest case + "outras histórias em breve" placeholders is preferred over
// inventing numbers.
const resultados = [
  {
    setor: "Distribuidora B2B · 12 funcionários",
    problema: "Compras saindo 15% acima do mercado.",
    resultado: "R$ 180/mês economizados na primeira cotação aprovada.",
    accent: C.orange,
    real: true,
  },
  {
    setor: "Outras histórias em breve",
    problema: "",
    resultado: "Estamos validando os números com cada cliente antes de publicar.",
    accent: C.purple,
    real: false,
  },
  {
    setor: "Outras histórias em breve",
    problema: "",
    resultado: "Estamos validando os números com cada cliente antes de publicar.",
    accent: C.blue,
    real: false,
  },
];

// ============================================================================
// INTERACTIVE DEMO — guideline §2.3
// ============================================================================
type DemoState =
  | { kind: "idle" }
  | { kind: "loading"; chipId: string }
  | { kind: "answer"; chipId: string }
  | { kind: "error" };

const InteractiveDemo: React.FC<{ onSignup: () => void; onTry: () => void }> = ({
  onSignup,
  onTry,
}) => {
  const [state, setState] = useState<DemoState>({ kind: "idle" });
  const timerRef = useRef<number | null>(null);

  const runChip = useCallback(
    (chipId: string) => {
      onTry();
      setState({ kind: "loading", chipId });
      if (timerRef.current) window.clearTimeout(timerRef.current);
      // Simulated streamed answer — wire to real seed-tenant endpoint when ready.
      // Keep latency small but realistic so the user feels something happen.
      timerRef.current = window.setTimeout(() => {
        // 1-in-N can be wired to the real backend's failure rate later.
        const fail = false;
        setState(fail ? { kind: "error" } : { kind: "answer", chipId });
      }, 900);
    },
    [onTry]
  );

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, []);

  const reset = () => setState({ kind: "idle" });

  return (
    <Box
      bg={C.surface}
      border="1px solid"
      borderColor={C.borderStrong}
      borderRadius="20px"
      p={{ base: 6, md: 8 }}
      position="relative"
      overflow="hidden"
      boxShadow={`0 30px 80px ${C.blue}1f`}
    >
      <Box
        position="absolute"
        left={0}
        top={0}
        bottom={0}
        w="3px"
        bg={C.blue}
        boxShadow={`0 0 14px ${C.blue}`}
      />
      <Text
        fontSize="13px"
        color={C.textMuted}
        letterSpacing="0.08em"
        fontWeight={600}
        mb={2}
      >
        DEMO · SEM CADASTRO
      </Text>
      <Heading
        as="h3"
        fontSize={{ base: "22px", md: "26px" }}
        fontFamily="'Playfair Display', serif"
        fontWeight={400}
        letterSpacing="-0.01em"
        lineHeight={1.2}
        mb={5}
      >
        Pergunte ao Blu, com dados de uma empresa de exemplo.
      </Heading>

      <HStack spacing={2} flexWrap="wrap" mb={6}>
        {demoChips.map((chip) => {
          const active =
            (state.kind === "loading" || state.kind === "answer") &&
            state.chipId === chip.id;
          return (
            <Button
              key={chip.id}
              size="sm"
              h="36px"
              px={4}
              borderRadius="999px"
              fontWeight={500}
              fontSize="13px"
              variant="outline"
              borderColor={active ? `${C.blue}99` : C.borderStrong}
              bg={active ? `${C.blue}22` : "transparent"}
              color="white"
              _hover={{ borderColor: C.blue, bg: `${C.blue}1a` }}
              onClick={() => runChip(chip.id)}
              aria-label={`Rodar pergunta de exemplo: ${chip.label}`}
            >
              {chip.label}
            </Button>
          );
        })}
      </HStack>

      {/* Answer surface — fixed height to avoid CLS. */}
      <Box
        bg={C.bgSoft}
        border="1px solid"
        borderColor={C.border}
        borderRadius="14px"
        p={5}
        minH="180px"
        position="relative"
      >
        {state.kind === "idle" && (
          <Text color={C.textDim} fontSize="14px" lineHeight={1.6}>
            Toque em uma pergunta acima para ver o Blu responder com gráfico,
            tabela e o porquê. <br />
            Os números vêm de uma empresa de exemplo — os seus aparecem assim
            que você conectar.
          </Text>
        )}

        {state.kind === "loading" && (
          <VStack align="stretch" spacing={3}>
            <HStack spacing={2.5}>
              <Box
                w="8px"
                h="8px"
                borderRadius="full"
                bg={C.blue}
                boxShadow={`0 0 12px ${C.blue}`}
                animation="pulse 1.2s ease-in-out infinite"
              />
              <Text fontSize="13px" color={C.textDim}>
                Blu está consultando os dados…
              </Text>
            </HStack>
            <Box h="10px" w="60%" bg="rgba(255,255,255,0.06)" borderRadius="6px" />
            <Box h="10px" w="80%" bg="rgba(255,255,255,0.04)" borderRadius="6px" />
            <Box h="10px" w="45%" bg="rgba(255,255,255,0.04)" borderRadius="6px" />
          </VStack>
        )}

        {state.kind === "answer" && (
          <DemoAnswer chipId={state.chipId} />
        )}

        {state.kind === "error" && (
          <VStack align="flex-start" spacing={3}>
            <Text fontSize="14px" color="white" fontWeight={500}>
              Tente outra pergunta.
            </Text>
            <Text fontSize="13px" color={C.textDim}>
              O Blu está acordando, leva alguns segundos. Você pode tocar em
              qualquer chip de novo.
            </Text>
            <Button
              size="sm"
              variant="ghost"
              color="white"
              fontSize="13px"
              onClick={reset}
              _hover={{ bg: "rgba(255,255,255,0.05)" }}
            >
              Voltar
            </Button>
          </VStack>
        )}
      </Box>

      {/* Soft CTA — appears once the user has seen one answer. */}
      <HStack justify="space-between" align="center" mt={5} flexWrap="wrap" spacing={3}>
        <Text fontSize="13px" color={C.textMuted}>
          Dados de exemplo. LGPD by design. Sem cadastro.
        </Text>
        {state.kind === "answer" && (
          <Button
            size="sm"
            h="40px"
            px={5}
            borderRadius="10px"
            bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
            color="white"
            fontWeight={600}
            fontSize="13px"
            rightIcon={<ArrowForwardIcon />}
            _hover={{ filter: "brightness(1.1)" }}
            onClick={onSignup}
          >
            Quero isso com os meus dados
          </Button>
        )}
      </HStack>
    </Box>
  );
};

const DemoAnswer: React.FC<{ chipId: string }> = ({ chipId }) => {
  if (chipId === "vendas") {
    return (
      <VStack align="stretch" spacing={3}>
        <Text fontSize="14px" color="white" fontWeight={500}>
          Esta semana: <Text as="span" color={C.greenLight}>R$ 87.420</Text>
          {" "}em receita, 12% acima da semana passada.
        </Text>
        <Box bg="rgba(16,185,129,0.06)" border="1px solid" borderColor="rgba(16,185,129,0.18)" borderRadius="10px" p={3}>
          <Text fontSize="12px" color={C.textDim} mb={1}>
            Por quê
          </Text>
          <Text fontSize="13px" color="white" lineHeight={1.5}>
            3 pedidos grandes da Distribuidora Silva entraram na quarta — sem
            eles, a semana ficaria estável.
          </Text>
        </Box>
        <Text fontSize="12px" color={C.textMuted} fontStyle="italic">
          Quer o detalhe por cliente? Pergunte de novo no produto.
        </Text>
      </VStack>
    );
  }
  if (chipId === "atrasos") {
    return (
      <VStack align="stretch" spacing={3}>
        <Text fontSize="14px" color="white" fontWeight={500}>
          5 clientes com pagamento em atraso, somando{" "}
          <Text as="span" color={C.orangeLight}>R$ 12.300</Text>.
        </Text>
        <Box bg="rgba(249,115,22,0.06)" border="1px solid" borderColor="rgba(249,115,22,0.18)" borderRadius="10px" p={3}>
          <Text fontSize="12px" color={C.textDim} mb={1}>
            Sugestão do Blu
          </Text>
          <Text fontSize="13px" color="white" lineHeight={1.5}>
            Posso preparar uma cobrança no WhatsApp para os 3 maiores e
            esperar a sua aprovação antes de enviar.
          </Text>
        </Box>
      </VStack>
    );
  }
  return (
    <VStack align="stretch" spacing={2}>
      <Text fontSize="14px" color="white" fontWeight={500}>
        Top 5 produtos em receita no mês:
      </Text>
      <VStack align="stretch" spacing={1.5} fontSize="13px" color={C.textDim}>
        {[
          ["1.", "Toner HP 107A", "R$ 18.900"],
          ["2.", "Papel A4 Reciclado", "R$ 14.220"],
          ["3.", "Cadeira Ergo Pro", "R$ 11.480"],
          ["4.", "Notebook 14\"", "R$ 9.760"],
          ["5.", "Kit Limpeza Pro", "R$ 7.310"],
        ].map(([n, name, val]) => (
          <Flex key={n} justify="space-between">
            <HStack spacing={2}>
              <Text color={C.textMuted}>{n}</Text>
              <Text color="white">{name}</Text>
            </HStack>
            <Text color="white" fontWeight={500}>{val}</Text>
          </Flex>
        ))}
      </VStack>
    </VStack>
  );
};

// ============================================================================
// EXIT INTENT — guideline §2.9.1
// ============================================================================
const useExitIntent = (
  onTrigger: () => void,
  opts: { suppressed: boolean }
) => {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (opts.suppressed) return;
    if (window.localStorage.getItem("blu.exit_intent.shown") === "1") return;

    const desktop = window.matchMedia("(min-width: 768px)").matches;

    let scrollFired = false;

    const handleMouseLeave = (e: MouseEvent) => {
      if (e.clientY > 0) return;
      window.localStorage.setItem("blu.exit_intent.shown", "1");
      onTrigger();
    };

    const handleScroll = () => {
      if (scrollFired) return;
      const ratio =
        (window.scrollY + window.innerHeight) /
        document.documentElement.scrollHeight;
      if (ratio >= 0.7) {
        scrollFired = true;
        window.localStorage.setItem("blu.exit_intent.shown", "1");
        onTrigger();
      }
    };

    if (desktop) {
      document.addEventListener("mouseleave", handleMouseLeave);
    } else {
      window.addEventListener("scroll", handleScroll, { passive: true });
    }

    return () => {
      document.removeEventListener("mouseleave", handleMouseLeave);
      window.removeEventListener("scroll", handleScroll);
    };
    // We intentionally do not depend on reduceMotion here; presentation respects it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.suppressed]);
};

// ============================================================================
// PAGE
// ============================================================================
const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);
  const [demoTried, setDemoTried] = useState(false);
  const exitModal = useDisclosure();

  // Mobile H1 variant — guideline §2.1
  const isNarrow = useBreakpointValue({ base: true, sm: false }) ?? false;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Primary CTA — kicks off onboarding.
  const openOnboarding = () => navigate("/onboarding");

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // §2.1 secondary CTA + §5 demo-disambiguation rule: every "demo" anchor
  // resolves to the same block.
  const goToDemo = () => scrollTo("demo");

  useExitIntent(
    () => {
      exitModal.onOpen();
    },
    { suppressed: demoTried }
  );

  return (
    <Box bg={C.bg} color="white" minH="100vh" overflow="hidden" position="relative">
      {/* Global subtle dotted grid */}
      <Box
        position="fixed"
        inset={0}
        pointerEvents="none"
        zIndex={0}
        opacity={0.25}
        backgroundImage="radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px)"
        backgroundSize="28px 28px"
      />

      {/* ===================== HEADER ===================== */}
      <Box
        as="header"
        position="fixed"
        top={0}
        left={0}
        right={0}
        zIndex={50}
        bg={scrolled ? "rgba(11,12,30,0.75)" : "transparent"}
        backdropFilter={scrolled ? "blur(14px) saturate(180%)" : "none"}
        borderBottom="1px solid"
        borderColor={scrolled ? C.border : "transparent"}
        transition="all .25s ease"
      >
        <Container maxW="1200px" px={{ base: 5, md: 8 }}>
          <Flex h="64px" align="center" justify="space-between">
            <HStack spacing={2.5}>
              <Box
                w="32px"
                h="32px"
                borderRadius="9px"
                bgGradient={`linear(135deg, ${C.blue}, ${C.purple})`}
                display="flex"
                alignItems="center"
                justifyContent="center"
                fontSize="16px"
                fontWeight={700}
                color="white"
                boxShadow={`0 0 18px ${C.blue}55`}
              >
                B
              </Box>
              <Text fontSize="18px" fontWeight={600} letterSpacing="-0.01em">
                Blu
              </Text>
            </HStack>
            <HStack spacing={2}>
              <Button
                variant="ghost"
                color="white"
                size="sm"
                fontWeight={500}
                _hover={{ bg: "rgba(255,255,255,0.06)" }}
                onClick={openOnboarding}
              >
                Entrar
              </Button>
              <Button
                size="sm"
                h="36px"
                px={5}
                borderRadius="10px"
                bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
                color="white"
                fontWeight={600}
                _hover={{ filter: "brightness(1.1)" }}
                onClick={openOnboarding}
              >
                Começar
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* ===================== HERO ===================== */}
      <Box
        as="section"
        position="relative"
        pt={{ base: "120px", md: "160px" }}
        pb={{ base: "60px", md: "90px" }}
      >
        <Box position="absolute" top="8%" left="-10%" w="520px" h="520px" bg={C.blue} filter="blur(160px)" opacity={0.22} borderRadius="full" pointerEvents="none" />
        <Box position="absolute" top="12%" right="-8%" w="480px" h="480px" bg={C.purple} filter="blur(160px)" opacity={0.2} borderRadius="full" pointerEvents="none" />
        <Box position="absolute" bottom="-10%" left="30%" w="420px" h="420px" bg={C.orange} filter="blur(170px)" opacity={0.12} borderRadius="full" pointerEvents="none" />

        <Container maxW="960px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={{ base: 7, md: 9 }} textAlign="center">
            <HStack
              spacing={2}
              px={3.5}
              py={1.5}
              borderRadius="full"
              bg="rgba(255,255,255,0.04)"
              border="1px solid"
              borderColor={C.borderStrong}
            >
              <Box w="7px" h="7px" borderRadius="full" bg={C.green} boxShadow={`0 0 12px ${C.green}`} />
              <Text fontSize="12px" color={C.textDim} letterSpacing="0.04em">
                Escritório virtual com IA · de 10 a 50 funcionários
              </Text>
            </HStack>

            <Heading
              as="h1"
              fontSize={{ base: "44px", md: "72px" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
              letterSpacing="-0.03em"
              lineHeight={1.02}
              color="white"
            >
              {isNarrow ? (
                <>
                  Pare de ser o{" "}
                  <Text
                    as="span"
                    fontStyle="italic"
                    bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink})`}
                    bgClip="text"
                  >
                    gargalo
                  </Text>
                  .
                </>
              ) : (
                <>
                  Pare de ser o{" "}
                  <Text
                    as="span"
                    fontStyle="italic"
                    bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink})`}
                    bgClip="text"
                  >
                    gargalo
                  </Text>
                  <br />
                  da sua empresa.
                </>
              )}
            </Heading>

            <Text
              fontSize={{ base: "17px", md: "20px" }}
              color={C.textDim}
              maxW="640px"
              lineHeight={1.55}
            >
              Blu é seu escritório virtual com IA. Ele lê suas planilhas, organiza
              suas rotinas e sugere as próximas jogadas.{" "}
              <Text as="span" color="white" fontWeight={500}>
                Você aprova. Ele executa.
              </Text>
            </Text>

            <HStack spacing={3} flexWrap="wrap" justify="center">
              <Button
                size="lg"
                h="54px"
                px={7}
                borderRadius="12px"
                bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
                color="white"
                fontWeight={600}
                fontSize="15px"
                rightIcon={<ArrowForwardIcon />}
                _hover={{ filter: "brightness(1.12)", transform: "translateY(-1px)" }}
                transition="all .2s"
                boxShadow={`0 12px 40px ${C.blue}44`}
                onClick={openOnboarding}
              >
                Montar meu escritório virtual
              </Button>
              <Button
                size="lg"
                h="54px"
                px={7}
                borderRadius="12px"
                variant="outline"
                borderColor={C.borderStrong}
                color="white"
                fontWeight={500}
                fontSize="15px"
                _hover={{ borderColor: "white", bg: "rgba(255,255,255,0.04)" }}
                onClick={goToDemo}
              >
                Ver demo de 60s
              </Button>
            </HStack>

            <HStack
              spacing={5}
              flexWrap="wrap"
              justify="center"
              color={C.textMuted}
              fontSize="13px"
              pt={2}
            >
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>De 10 a 50 funcionários</Text>
              </HStack>
              <Text color={C.borderStrong}>·</Text>
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>Nada acontece sem você</Text>
              </HStack>
              <Text color={C.borderStrong}>·</Text>
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>LGPD by design</Text>
              </HStack>
            </HStack>
          </VStack>
        </Container>
      </Box>

      {/* ===================== LOGO BAR ===================== */}
      <Box as="section" py={{ base: 8, md: 10 }} position="relative">
        <Container maxW="1160px" px={{ base: 5, md: 8 }}>
          <VStack spacing={5}>
            <Text fontSize="13px" color={C.textMuted} letterSpacing="0.04em">
              Empresas brasileiras que já têm Blu no time
            </Text>
            <Flex
              wrap="wrap"
              justify="center"
              align="center"
              gap={{ base: 6, md: 10 }}
              opacity={0.65}
            >
              {logosPlaceholders.map((name) => (
                <Box
                  key={name}
                  px={4}
                  py={2}
                  borderRadius="8px"
                  border="1px dashed"
                  borderColor={C.border}
                  fontSize="12px"
                  color={C.textDim}
                  letterSpacing="0.04em"
                  textTransform="uppercase"
                >
                  {name}
                </Box>
              ))}
            </Flex>
          </VStack>
        </Container>
      </Box>

      {/* ===================== INTERACTIVE DEMO ===================== */}
      <Box as="section" id="demo" py={{ base: "60px", md: "90px" }} position="relative">
        <Box position="absolute" top="10%" left="-5%" w="380px" h="380px" bg={C.blue} filter="blur(160px)" opacity={0.12} borderRadius="full" pointerEvents="none" />

        <Container maxW="960px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={6} mb={8} textAlign="center">
            <Heading
              fontSize={{ base: "28px", md: "40px" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
              letterSpacing="-0.02em"
              lineHeight={1.1}
            >
              Experimente em{" "}
              <Text
                as="span"
                fontStyle="italic"
                bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`}
                bgClip="text"
              >
                60 segundos.
              </Text>
            </Heading>
            <Text fontSize={{ base: "15px", md: "16px" }} color={C.textDim} maxW="560px" lineHeight={1.55}>
              Sem cadastro, sem instalação. Toque em uma pergunta abaixo e veja
              o Blu responder com dados de uma empresa de exemplo.
            </Text>
          </VStack>
          <InteractiveDemo
            onSignup={openOnboarding}
            onTry={() => setDemoTried(true)}
          />
        </Container>
      </Box>

      {/* ===================== COMO FUNCIONA ===================== */}
      <Box as="section" id="como-funciona" py={{ base: "80px", md: "120px" }} bg={C.bgSoft} position="relative">
        <Container maxW="1160px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={{ base: 10, md: 14 }}>
            <VStack spacing={4} textAlign="center" maxW="720px">
              <Heading
                fontSize={{ base: "34px", md: "52px" }}
                fontFamily="'Playfair Display', serif"
                fontWeight={400}
                letterSpacing="-0.02em"
                lineHeight={1.1}
              >
                Como Blu{" "}
                <Text
                  as="span"
                  fontStyle="italic"
                  bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`}
                  bgClip="text"
                >
                  organiza
                </Text>{" "}
                sua operação
              </Heading>
            </VStack>

            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={5} w="full">
              {[
                {
                  n: "1",
                  t: "Conecte seu contexto",
                  d: "Planilhas, sistemas ou modelos. O que você já tem, o Blu lê.",
                  c: C.blue,
                },
                {
                  n: "2",
                  t: "Receba rotinas e insights",
                  d: "Agenda da semana, análises respondidas, cotações comparadas — sem você precisar pedir.",
                  c: C.purple,
                },
                {
                  n: "3",
                  t: "Aprove e cresça",
                  d: "Cada sugestão chega com o porquê. Você decide e o Blu executa.",
                  c: C.pink,
                },
              ].map((s) => (
                <Box
                  key={s.n}
                  position="relative"
                  bg={C.surface}
                  border="1px solid"
                  borderColor={C.borderStrong}
                  borderRadius="20px"
                  p={{ base: 7, md: 8 }}
                  overflow="hidden"
                  _hover={{
                    borderColor: `${s.c}55`,
                    transform: "translateY(-2px)",
                    boxShadow: `0 20px 60px ${s.c}22`,
                  }}
                  transition="all .25s"
                >
                  <Box position="absolute" left={0} top={0} bottom={0} w="3px" bg={s.c} boxShadow={`0 0 14px ${s.c}`} />
                  <Text
                    fontSize="64px"
                    fontFamily="'Playfair Display', serif"
                    fontStyle="italic"
                    fontWeight={400}
                    lineHeight={1}
                    bgGradient={`linear(to-br, ${s.c}, ${s.c}66)`}
                    bgClip="text"
                    mb={4}
                  >
                    {s.n}
                  </Text>
                  <Heading fontSize="22px" fontWeight={600} mb={2.5} letterSpacing="-0.01em">
                    {s.t}
                  </Heading>
                  <Text color={C.textDim} fontSize="15px" lineHeight={1.6}>
                    {s.d}
                  </Text>
                </Box>
              ))}
            </Grid>

            <Text color={C.textDim} fontSize="16px" fontStyle="italic" textAlign="center" maxW="640px">
              Quanto mais o Blu aprende sobre seu negócio, melhor ele decide com você.
            </Text>
          </VStack>
        </Container>
      </Box>

      {/* ===================== SEU TIME VIRTUAL ===================== */}
      <Box as="section" py={{ base: "80px", md: "120px" }} position="relative">
        <Container maxW="1160px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={{ base: 10, md: 14 }}>
            <VStack spacing={4} textAlign="center" maxW="720px">
              <Heading
                fontSize={{ base: "34px", md: "52px" }}
                fontFamily="'Playfair Display', serif"
                fontWeight={400}
                letterSpacing="-0.02em"
                lineHeight={1.1}
              >
                Seu{" "}
                <Text
                  as="span"
                  fontStyle="italic"
                  bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink})`}
                  bgClip="text"
                >
                  time
                </Text>{" "}
                de agentes prontos para ativar
              </Heading>
            </VStack>

            <Grid templateColumns={{ base: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" }} gap={4} w="full">
              {agentes.map((a) => (
                <Box
                  key={a.nome}
                  bg={C.surface}
                  border="1px solid"
                  borderColor={C.borderStrong}
                  borderRadius="16px"
                  p={6}
                  _hover={{ borderColor: `${a.color}66`, transform: "translateY(-2px)" }}
                  transition="all .2s"
                >
                  <HStack spacing={2.5} mb={2}>
                    <Box w="8px" h="8px" borderRadius="full" bg={a.color} boxShadow={`0 0 10px ${a.color}`} />
                    <Text fontSize="15px" fontWeight={600} color="white">
                      {a.nome}
                    </Text>
                  </HStack>
                  <Text color={C.textDim} fontSize="14px" lineHeight={1.5}>
                    "{a.linha}"
                  </Text>
                </Box>
              ))}
            </Grid>

            <VStack spacing={3}>
              <Text color={C.textDim} fontSize="15px" textAlign="center">
                Ative os que fizerem sentido. Adicione mais depois.
              </Text>
              <Button
                size="md"
                h="44px"
                px={6}
                borderRadius="10px"
                variant="outline"
                borderColor={C.borderStrong}
                color="white"
                fontWeight={500}
                fontSize="14px"
                _hover={{ borderColor: "white", bg: "rgba(255,255,255,0.04)" }}
                onClick={goToDemo}
              >
                Ver demo de 60s
              </Button>
            </VStack>
          </VStack>
        </Container>
      </Box>

      {/* ===================== RESULTADOS ===================== */}
      <Box as="section" py={{ base: "80px", md: "120px" }} bg={C.bgSoft} position="relative">
        <Container maxW="1160px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={{ base: 10, md: 14 }}>
            <VStack spacing={4} textAlign="center" maxW="720px">
              <Heading
                fontSize={{ base: "34px", md: "52px" }}
                fontFamily="'Playfair Display', serif"
                fontWeight={400}
                letterSpacing="-0.02em"
                lineHeight={1.1}
              >
                Resultados{" "}
                <Text
                  as="span"
                  fontStyle="italic"
                  bgGradient={`linear(to-r, ${C.greenLight}, ${C.blueLight})`}
                  bgClip="text"
                >
                  reais
                </Text>
                , de empresas reais
              </Heading>
            </VStack>

            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={5} w="full">
              {resultados.map((r, i) => (
                <Box
                  key={i}
                  position="relative"
                  bg={C.surface}
                  border="1px solid"
                  borderColor={C.borderStrong}
                  borderRadius="20px"
                  p={{ base: 6, md: 7 }}
                  overflow="hidden"
                  opacity={r.real ? 1 : 0.7}
                >
                  <Box position="absolute" left={0} top={0} bottom={0} w="3px" bg={r.accent} boxShadow={`0 0 14px ${r.accent}`} />
                  <Text fontSize="12px" color={C.textMuted} letterSpacing="0.06em" mb={3} textTransform="uppercase">
                    {r.setor}
                  </Text>
                  {r.problema && (
                    <Text fontSize="14px" color={C.textDim} mb={3} lineHeight={1.5}>
                      {r.problema}
                    </Text>
                  )}
                  <Text fontSize={{ base: "17px", md: "18px" }} color="white" fontWeight={500} lineHeight={1.4}>
                    {r.resultado}
                  </Text>
                </Box>
              ))}
            </Grid>
          </VStack>
        </Container>
      </Box>

      {/* ===================== CONFIANÇA (HITL) ===================== */}
      <Box as="section" py={{ base: "80px", md: "120px" }} position="relative">
        <Box position="absolute" top="20%" right="-5%" w="420px" h="420px" bg={C.blue} filter="blur(160px)" opacity={0.14} borderRadius="full" pointerEvents="none" />

        <Container maxW="1160px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={{ base: 10, md: 14 }}>
            <Heading
              fontSize={{ base: "34px", md: "52px" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
              letterSpacing="-0.02em"
              lineHeight={1.1}
              textAlign="center"
              maxW="720px"
            >
              Nada acontece{" "}
              <Text
                as="span"
                fontStyle="italic"
                bgGradient={`linear(to-r, ${C.greenLight}, ${C.blueLight})`}
                bgClip="text"
              >
                sem você.
              </Text>
            </Heading>

            <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap={8} w="full" alignItems="center">
              <Box
                bg={C.surface}
                border="1px solid"
                borderColor={C.borderStrong}
                borderRadius="18px"
                p={6}
                position="relative"
                overflow="hidden"
                boxShadow={`0 30px 80px ${C.blue}22`}
              >
                <Box position="absolute" left={0} top={0} bottom={0} w="3px" bg={C.orange} boxShadow={`0 0 14px ${C.orange}`} />
                <HStack justify="space-between" mb={5}>
                  <HStack spacing={2.5}>
                    <Box
                      w="34px"
                      h="34px"
                      borderRadius="10px"
                      bgGradient={`linear(135deg, ${C.orange}, ${C.pink})`}
                      display="flex"
                      alignItems="center"
                      justifyContent="center"
                      fontSize="16px"
                    >
                      🛒
                    </Box>
                    <Box>
                      <Text fontSize="11px" color={C.textMuted} letterSpacing="0.08em">
                        AGENTE DE COMPRAS
                      </Text>
                      <Text fontSize="14px" fontWeight={600} color="white">
                        Aguardando aprovação
                      </Text>
                    </Box>
                  </HStack>
                  <Badge bg="rgba(239,68,68,0.15)" color="#fca5a5" borderRadius="6px" px={2} py={0.5} fontSize="10px" fontWeight={600}>
                    ALTA
                  </Badge>
                </HStack>

                <VStack align="stretch" spacing={3} mb={5}>
                  <Box>
                    <Text fontSize="12px" color={C.textMuted}>Cotação</Text>
                    <Text fontSize="15px" color="white" fontWeight={500}>
                      Toner HP 107A · 20 unidades
                    </Text>
                  </Box>
                  <Flex justify="space-between">
                    <Box>
                      <Text fontSize="12px" color={C.textMuted}>Fornecedor</Text>
                      <Text fontSize="14px" color="white">Silva &amp; Cia</Text>
                    </Box>
                    <Box textAlign="right">
                      <Text fontSize="12px" color={C.textMuted}>Valor</Text>
                      <Text fontSize="14px" color="white" fontWeight={600}>R$ 3.200</Text>
                    </Box>
                  </Flex>
                  <Box bg="rgba(16,185,129,0.08)" border="1px solid" borderColor="rgba(16,185,129,0.25)" borderRadius="10px" p={3}>
                    <HStack spacing={2}>
                      <CheckCircleIcon color={C.green} boxSize={3.5} />
                      <Text fontSize="13px" color={C.greenLight} fontWeight={500}>
                        Economia estimada: R$ 180/mês
                      </Text>
                    </HStack>
                  </Box>
                </VStack>

                <HStack spacing={2.5}>
                  <Button
                    flex={1}
                    h="40px"
                    bg={C.green}
                    color="white"
                    fontWeight={600}
                    fontSize="13px"
                    borderRadius="10px"
                    _hover={{ filter: "brightness(1.1)" }}
                  >
                    Aprovar
                  </Button>
                  <Button
                    flex={1}
                    h="40px"
                    variant="outline"
                    borderColor={C.borderStrong}
                    color="white"
                    fontWeight={500}
                    fontSize="13px"
                    borderRadius="10px"
                    _hover={{ bg: "rgba(255,255,255,0.04)" }}
                  >
                    Recusar
                  </Button>
                </HStack>
              </Box>

              <VStack align="flex-start" spacing={5}>
                <Text
                  fontSize={{ base: "22px", md: "28px" }}
                  fontFamily="'Playfair Display', serif"
                  fontWeight={400}
                  lineHeight={1.3}
                  letterSpacing="-0.01em"
                  color="white"
                >
                  "O Agente de Compras me mostrou que eu pagava{" "}
                  <Text
                    as="span"
                    fontStyle="italic"
                    bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink})`}
                    bgClip="text"
                  >
                    15% a mais
                  </Text>{" "}
                  no mesmo produto. Só isso pagou o Blu."
                </Text>
                <HStack spacing={3}>
                  <Box
                    w="44px"
                    h="44px"
                    borderRadius="full"
                    bgGradient={`linear(135deg, ${C.blue}, ${C.purple})`}
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    fontWeight={600}
                  >
                    R
                  </Box>
                  <Box>
                    <Text fontSize="14px" fontWeight={600} color="white">
                      Ricardo T.
                    </Text>
                    <Text fontSize="13px" color={C.textDim}>
                      Distribuidora · 12 funcionários
                    </Text>
                  </Box>
                </HStack>
                <HStack spacing={3} pt={2}>
                  <Button
                    size="md"
                    h="44px"
                    px={6}
                    borderRadius="10px"
                    bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
                    color="white"
                    fontWeight={600}
                    fontSize="14px"
                    rightIcon={<ArrowForwardIcon />}
                    _hover={{ filter: "brightness(1.1)" }}
                    onClick={openOnboarding}
                  >
                    Começar agora
                  </Button>
                  <Link
                    href="mailto:contato@blu.com.br"
                    fontSize="14px"
                    color={C.textDim}
                    _hover={{ color: "white" }}
                  >
                    Falar com um humano
                  </Link>
                </HStack>
                <Text color={C.textDim} fontSize="15px" fontStyle="italic" pt={2}>
                  Agentes sugerem. Você decide.
                </Text>
              </VStack>
            </Grid>
          </VStack>
        </Container>
      </Box>

      {/* ===================== INVESTIMENTO ===================== */}
      <Box as="section" py={{ base: "80px", md: "120px" }} bg={C.bgSoft} position="relative">
        <Container maxW="1160px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={{ base: 10, md: 14 }}>
            <VStack spacing={4} textAlign="center" maxW="640px">
              <Heading
                fontSize={{ base: "34px", md: "52px" }}
                fontFamily="'Playfair Display', serif"
                fontWeight={400}
                letterSpacing="-0.02em"
                lineHeight={1.1}
              >
                Cresça{" "}
                <Text
                  as="span"
                  fontStyle="italic"
                  bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`}
                  bgClip="text"
                >
                  no seu ritmo
                </Text>
              </Heading>
              <Text color={C.textDim} fontSize="16px">
                Sem fidelidade. Cancele quando quiser.
              </Text>
            </VStack>

            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={5} w="full" alignItems="stretch">
              {[
                {
                  nome: "Inicial",
                  preco: "197",
                  cor: C.blue,
                  destaque: false,
                  features: [
                    "1 usuário",
                    "Análise + Agenda + Documentos",
                    "Planilhas ilimitadas",
                  ],
                },
                {
                  nome: "Crescimento",
                  preco: "497",
                  cor: C.purple,
                  destaque: true,
                  features: [
                    "Até 5 usuários",
                    "Todos os agentes",
                    "Compras + Atendimento + Planejamento",
                    "Aprovações e relatórios semanais",
                  ],
                },
                {
                  nome: "Profissional",
                  preco: "997",
                  cor: C.orange,
                  destaque: false,
                  features: [
                    "Até 15 usuários",
                    "Integrações Bling / Omie / Tiny (em breve)",
                    "OCR e auditoria completa",
                  ],
                },
              ].map((p) => (
                <Box
                  key={p.nome}
                  position="relative"
                  bg={C.surface}
                  border="1px solid"
                  borderColor={p.destaque ? `${p.cor}88` : C.borderStrong}
                  borderRadius="20px"
                  p={{ base: 7, md: 8 }}
                  overflow="hidden"
                  transform={p.destaque ? { md: "scale(1.03)" } : "none"}
                  boxShadow={p.destaque ? `0 30px 80px ${p.cor}33` : "none"}
                  _hover={{
                    borderColor: `${p.cor}99`,
                    transform: p.destaque ? { md: "scale(1.04)" } : "translateY(-2px)",
                  }}
                  transition="all .25s"
                >
                  {p.destaque && (
                    <Badge
                      position="absolute"
                      top={4}
                      right={4}
                      bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
                      color="white"
                      fontSize="10px"
                      fontWeight={700}
                      letterSpacing="0.08em"
                      borderRadius="6px"
                      px={2}
                      py={1}
                    >
                      ★ MAIS ESCOLHIDO
                    </Badge>
                  )}
                  <Text fontSize="13px" color={C.textMuted} letterSpacing="0.08em" fontWeight={600} mb={3}>
                    {p.nome.toUpperCase()}
                  </Text>
                  <HStack spacing={1.5} align="baseline" mb={6}>
                    <Text fontSize="14px" color={C.textDim}>R$</Text>
                    <Text
                      fontSize="48px"
                      fontFamily="'Playfair Display', serif"
                      fontWeight={500}
                      letterSpacing="-0.02em"
                      lineHeight={1}
                      color="white"
                    >
                      {p.preco}
                    </Text>
                    <Text fontSize="14px" color={C.textDim}>/mês</Text>
                  </HStack>
                  <VStack align="stretch" spacing={2.5} mb={7}>
                    {p.features.map((f) => (
                      <HStack key={f} spacing={2.5} align="flex-start">
                        <CheckCircleIcon color={p.cor} boxSize={3.5} mt={1} />
                        <Text fontSize="14px" color="white" lineHeight={1.5}>
                          {f}
                        </Text>
                      </HStack>
                    ))}
                  </VStack>
                  <Button
                    w="full"
                    h="46px"
                    borderRadius="10px"
                    fontWeight={600}
                    fontSize="14px"
                    bgGradient={p.destaque ? `linear(to-r, ${C.blue}, ${C.purple})` : "none"}
                    bg={p.destaque ? undefined : "rgba(255,255,255,0.04)"}
                    border={p.destaque ? "none" : "1px solid"}
                    borderColor={C.borderStrong}
                    color="white"
                    _hover={{
                      filter: "brightness(1.1)",
                      bg: p.destaque ? undefined : "rgba(255,255,255,0.08)",
                    }}
                    onClick={openOnboarding}
                  >
                    Começar
                  </Button>
                </Box>
              ))}
            </Grid>

            <HStack
              spacing={5}
              flexWrap="wrap"
              justify="center"
              color={C.textMuted}
              fontSize="13px"
              pt={2}
            >
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>Sem fidelidade. Cancele quando quiser.</Text>
              </HStack>
              <Text color={C.borderStrong}>·</Text>
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>Comece em modo demo, conecte seus dados quando quiser.</Text>
              </HStack>
            </HStack>
          </VStack>
        </Container>
      </Box>

      {/* ===================== FAQ ===================== */}
      <Box as="section" py={{ base: "80px", md: "120px" }} position="relative">
        <Container maxW="820px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={{ base: 8, md: 12 }}>
            <Heading
              fontSize={{ base: "32px", md: "44px" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
              letterSpacing="-0.02em"
              lineHeight={1.1}
              textAlign="center"
            >
              Perguntas que a gente{" "}
              <Text
                as="span"
                fontStyle="italic"
                bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`}
                bgClip="text"
              >
                sempre escuta
              </Text>
            </Heading>

            <Accordion allowToggle w="full">
              {faq.map((item) => (
                <AccordionItem
                  key={item.q}
                  border="1px solid"
                  borderColor={C.borderStrong}
                  borderRadius="14px"
                  bg={C.surface}
                  mb={3}
                  _last={{ mb: 0 }}
                >
                  <AccordionButton
                    py={5}
                    px={5}
                    _hover={{ bg: "rgba(255,255,255,0.03)" }}
                    borderRadius="14px"
                  >
                    <Box flex={1} textAlign="left" fontSize={{ base: "15px", md: "16px" }} fontWeight={500} color="white">
                      {item.q}
                    </Box>
                    <AccordionIcon color={C.textDim} />
                  </AccordionButton>
                  <AccordionPanel px={5} pb={5} pt={0} fontSize="14px" color={C.textDim} lineHeight={1.65}>
                    {item.a}
                  </AccordionPanel>
                </AccordionItem>
              ))}
            </Accordion>

            <HStack spacing={2} color={C.textDim} fontSize="14px">
              <Text>Ainda com dúvida?</Text>
              <Link href="mailto:contato@blu.com.br" color="white" textDecoration="underline" _hover={{ color: C.blueLight }}>
                Falar com a gente
              </Link>
            </HStack>
          </VStack>
        </Container>
      </Box>

      {/* ===================== CTA FINAL ===================== */}
      <Box as="section" py={{ base: "100px", md: "140px" }} position="relative">
        <Box position="absolute" top="-10%" left="10%" w="500px" h="500px" bg={C.blue} filter="blur(170px)" opacity={0.2} borderRadius="full" pointerEvents="none" />
        <Box position="absolute" bottom="-10%" right="10%" w="500px" h="500px" bg={C.purple} filter="blur(170px)" opacity={0.2} borderRadius="full" pointerEvents="none" />

        <Container maxW="860px" px={{ base: 5, md: 8 }} position="relative" zIndex={1}>
          <VStack spacing={7} textAlign="center">
            <Heading
              fontSize={{ base: "44px", md: "76px" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
              letterSpacing="-0.03em"
              lineHeight={1.02}
            >
              Sua vez de{" "}
              <Text
                as="span"
                fontStyle="italic"
                bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink}, ${C.purpleLight})`}
                bgClip="text"
              >
                crescer.
              </Text>
            </Heading>

            <Text fontSize={{ base: "17px", md: "20px" }} color={C.textDim} maxW="580px" lineHeight={1.55}>
              Comece em modo demo. Conecte seus dados quando fizer sentido.
              Aprove suas primeiras sugestões e veja o Blu virar parte do time.
            </Text>

            <Button
              size="lg"
              h="58px"
              px={9}
              borderRadius="12px"
              bgGradient={`linear(to-r, ${C.blue}, ${C.purple}, ${C.pink})`}
              color="white"
              fontWeight={600}
              fontSize="16px"
              rightIcon={<ArrowForwardIcon />}
              _hover={{ filter: "brightness(1.12)", transform: "translateY(-1px)" }}
              transition="all .2s"
              boxShadow={`0 16px 50px ${C.purple}55`}
              onClick={openOnboarding}
            >
              Começar agora
            </Button>

            <HStack
              spacing={5}
              flexWrap="wrap"
              justify="center"
              color={C.textMuted}
              fontSize="13px"
            >
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>De 10 a 50 funcionários</Text>
              </HStack>
              <Text color={C.borderStrong}>·</Text>
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>Nada acontece sem você</Text>
              </HStack>
              <Text color={C.borderStrong}>·</Text>
              <HStack spacing={1.5}>
                <CheckCircleIcon boxSize={3} color={C.green} />
                <Text>LGPD by design</Text>
              </HStack>
            </HStack>
          </VStack>
        </Container>
      </Box>

      {/* ===================== FOOTER ===================== */}
      <Box as="footer" borderTop="1px solid" borderColor={C.border} py={10}>
        <Container maxW="1160px" px={{ base: 5, md: 8 }}>
          <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
            <HStack spacing={2.5}>
              <Box
                w="28px"
                h="28px"
                borderRadius="8px"
                bgGradient={`linear(135deg, ${C.blue}, ${C.purple})`}
                display="flex"
                alignItems="center"
                justifyContent="center"
                fontSize="14px"
                fontWeight={700}
              >
                B
              </Box>
              <Text fontSize="14px" color={C.textDim}>
                © 2026 Blu · Escritório virtual com IA
              </Text>
            </HStack>
            <HStack spacing={5} fontSize="13px" color={C.textDim}>
              <Link _hover={{ color: "white" }}>Privacidade</Link>
              <Link _hover={{ color: "white" }}>Termos</Link>
              <Link _hover={{ color: "white" }}>Contato</Link>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* ===================== EXIT INTENT ===================== */}
      <Modal
        isOpen={exitModal.isOpen}
        onClose={exitModal.onClose}
        isCentered
        motionPreset="none"
      >
        <ModalOverlay bg="rgba(11,12,30,0.78)" backdropFilter="blur(8px)" />
        <ModalContent
          bg={C.surface}
          border="1px solid"
          borderColor={C.borderStrong}
          borderRadius="18px"
          mx={4}
          maxW="460px"
          overflow="hidden"
        >
          <Box position="absolute" left={0} top={0} bottom={0} w="3px" bg={C.blue} boxShadow={`0 0 14px ${C.blue}`} />
          <ModalCloseButton color={C.textDim} />
          <ModalBody p={7}>
            <VStack align="flex-start" spacing={4}>
              <Text fontSize="13px" color={C.textMuted} letterSpacing="0.08em" fontWeight={600}>
                ANTES DE IR
              </Text>
              <Heading
                as="h3"
                fontSize="26px"
                fontFamily="'Playfair Display', serif"
                fontWeight={400}
                lineHeight={1.15}
                letterSpacing="-0.01em"
              >
                Veja em{" "}
                <Text
                  as="span"
                  fontStyle="italic"
                  bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`}
                  bgClip="text"
                >
                  60 segundos
                </Text>{" "}
                o que o Blu faz.
              </Heading>
              <Text fontSize="14px" color={C.textDim} lineHeight={1.55}>
                Sem cadastro, sem cartão. Toque em uma pergunta de exemplo e
                veja o Blu responder com dados reais.
              </Text>
              <HStack spacing={2} pt={2} w="full">
                <Button
                  flex={1}
                  h="44px"
                  borderRadius="10px"
                  bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
                  color="white"
                  fontWeight={600}
                  fontSize="14px"
                  _hover={{ filter: "brightness(1.1)" }}
                  onClick={() => {
                    exitModal.onClose();
                    goToDemo();
                  }}
                >
                  Ver demo agora
                </Button>
                <Button
                  h="44px"
                  px={5}
                  borderRadius="10px"
                  variant="ghost"
                  color={C.textDim}
                  fontWeight={500}
                  fontSize="14px"
                  _hover={{ bg: "rgba(255,255,255,0.05)", color: "white" }}
                  onClick={exitModal.onClose}
                >
                  Fechar
                </Button>
              </HStack>
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default LandingPage;
