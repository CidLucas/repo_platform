import React, { useState, useEffect } from "react";
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
} from "@chakra-ui/react";
import { ArrowForwardIcon, CheckCircleIcon } from "@chakra-ui/icons";

// ========== DESIGN TOKENS (mirrored from the app) ==========
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

// ========== AGENT CARD DATA ==========
const agentes = [
  { nome: "Agente de Análise", linha: "Sua planilha vira resposta.", color: C.blue },
  { nome: "Agente de Agenda", linha: "Sua segunda-feira, organizada.", color: C.purple },
  { nome: "Agente de Compras", linha: "Cotações comparadas antes de comprar.", color: C.orange },
  { nome: "Agente de Atendimento", linha: "Nenhum cliente esquecido.", color: C.pink },
  { nome: "Agente de Documentos", linha: "Reuniões com pauta e resultado.", color: C.green },
  { nome: "Agente de Planejamento", linha: "Metas claras, passos reais.", color: C.yellow },
];

// ========== LANDING PAGE ==========
const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Primary CTA — kick off the Context Flywheel onboarding.
  const openModal = () => navigate("/onboarding");

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

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

      {/* ==================== HEADER ==================== */}
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
              <Text fontSize="18px" fontWeight={600} letterSpacing="-0.01em">Blu</Text>
            </HStack>
            <HStack spacing={2}>
              <Button
                variant="ghost"
                color="white"
                size="sm"
                fontWeight={500}
                _hover={{ bg: "rgba(255,255,255,0.06)" }}
                onClick={openModal}
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
                onClick={openModal}
              >
                Começar
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* ==================== 1. HERO ==================== */}
      <Box as="section" position="relative" pt={{ base: "120px", md: "160px" }} pb={{ base: "100px", md: "140px" }}>
        {/* Radial glows */}
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
              fontSize={{ base: "42px", md: "72px" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
              letterSpacing="-0.03em"
              lineHeight={1.02}
              color="white"
            >
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
            </Heading>

            <Text
              fontSize={{ base: "17px", md: "20px" }}
              color={C.textDim}
              maxW="640px"
              lineHeight={1.55}
            >
              Blu é seu escritório virtual com IA. Ele lê suas planilhas, organiza suas rotinas e sugere suas próximas jogadas.{" "}
              <Text as="span" color="white" fontWeight={500}>Você aprova. Ele executa.</Text>
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
                onClick={openModal}
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
                onClick={() => scrollTo("como-funciona")}
              >
                Ver como funciona
              </Button>
            </HStack>

            <HStack spacing={5} flexWrap="wrap" justify="center" color={C.textMuted} fontSize="13px" pt={2}>
              <HStack spacing={1.5}><CheckCircleIcon boxSize={3} color={C.green} /><Text>De 10 a 50 funcionários</Text></HStack>
              <Text color={C.borderStrong}>·</Text>
              <HStack spacing={1.5}><CheckCircleIcon boxSize={3} color={C.green} /><Text>Nada acontece sem você</Text></HStack>
              <Text color={C.borderStrong}>·</Text>
              <HStack spacing={1.5}><CheckCircleIcon boxSize={3} color={C.green} /><Text>LGPD by design</Text></HStack>
            </HStack>
          </VStack>
        </Container>
      </Box>

      {/* ==================== 2. COMO FUNCIONA ==================== */}
      <Box as="section" id="como-funciona" py={{ base: "80px", md: "120px" }} position="relative">
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
                <Text as="span" fontStyle="italic" bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`} bgClip="text">
                  organiza
                </Text>{" "}
                sua operação
              </Heading>
            </VStack>

            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={5} w="full">
              {[
                { n: "1", t: "Conecte seu contexto", d: "Envie suas planilhas ou use nossos modelos. Blu entende seu negócio.", c: C.blue },
                { n: "2", t: "Receba rotinas e insights", d: "Agenda montada, análises respondidas, cotações comparadas — automaticamente.", c: C.purple },
                { n: "3", t: "Aprove e cresça", d: "Você revisa e autoriza. Blu executa. Você aprende e escala.", c: C.pink },
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
                  _hover={{ borderColor: `${s.c}55`, transform: "translateY(-2px)", boxShadow: `0 20px 60px ${s.c}22` }}
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
                  <Heading fontSize="22px" fontWeight={600} mb={2.5} letterSpacing="-0.01em">{s.t}</Heading>
                  <Text color={C.textDim} fontSize="15px" lineHeight={1.6}>{s.d}</Text>
                </Box>
              ))}
            </Grid>

            <Text color={C.textDim} fontSize="16px" fontStyle="italic" textAlign="center">
              Quanto mais contexto, mais sua é a plataforma.
            </Text>
          </VStack>
        </Container>
      </Box>

      {/* ==================== 3. SEU TIME VIRTUAL ==================== */}
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
                Seu{" "}
                <Text as="span" fontStyle="italic" bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink})`} bgClip="text">
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
                    <Text fontSize="15px" fontWeight={600} color="white">{a.nome}</Text>
                  </HStack>
                  <Text color={C.textDim} fontSize="14px" lineHeight={1.5}>"{a.linha}"</Text>
                </Box>
              ))}
            </Grid>

            <Text color={C.textDim} fontSize="15px" textAlign="center">
              Ative os que fizerem sentido. Adicione mais depois.
            </Text>
          </VStack>
        </Container>
      </Box>

      {/* ==================== 4. CONFIANÇA ==================== */}
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
              <Text as="span" fontStyle="italic" bgGradient={`linear(to-r, ${C.greenLight}, ${C.blueLight})`} bgClip="text">
                sem você.
              </Text>
            </Heading>

            <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap={8} w="full" alignItems="center">
              {/* Approval card mock */}
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
                    <Box w="34px" h="34px" borderRadius="10px" bgGradient={`linear(135deg, ${C.orange}, ${C.pink})`} display="flex" alignItems="center" justifyContent="center" fontSize="16px">🛒</Box>
                    <Box>
                      <Text fontSize="11px" color={C.textMuted} letterSpacing="0.08em">AGENTE DE COMPRAS</Text>
                      <Text fontSize="14px" fontWeight={600} color="white">Aguardando aprovação</Text>
                    </Box>
                  </HStack>
                  <Badge bg="rgba(239,68,68,0.15)" color="#fca5a5" borderRadius="6px" px={2} py={0.5} fontSize="10px" fontWeight={600}>ALTA</Badge>
                </HStack>

                <VStack align="stretch" spacing={3} mb={5}>
                  <Box>
                    <Text fontSize="12px" color={C.textMuted}>Cotação</Text>
                    <Text fontSize="15px" color="white" fontWeight={500}>Toner HP 107A · 20 unidades</Text>
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
                      <Text fontSize="13px" color={C.greenLight} fontWeight={500}>Economia estimada: R$ 180/mês</Text>
                    </HStack>
                  </Box>
                </VStack>

                <HStack spacing={2.5}>
                  <Button flex={1} h="40px" bg={C.green} color="white" fontWeight={600} fontSize="13px" borderRadius="10px" _hover={{ filter: "brightness(1.1)" }}>Aprovar</Button>
                  <Button flex={1} h="40px" variant="outline" borderColor={C.borderStrong} color="white" fontWeight={500} fontSize="13px" borderRadius="10px" _hover={{ bg: "rgba(255,255,255,0.04)" }}>Recusar</Button>
                </HStack>
              </Box>

              {/* Testimonial */}
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
                  <Text as="span" fontStyle="italic" bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink})`} bgClip="text">
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
                    <Text fontSize="14px" fontWeight={600} color="white">Ricardo T.</Text>
                    <Text fontSize="13px" color={C.textDim}>Distribuidora · 12 funcionários</Text>
                  </Box>
                </HStack>
                <Text color={C.textDim} fontSize="15px" fontStyle="italic" pt={2}>
                  Agentes sugerem. Você decide.
                </Text>
              </VStack>
            </Grid>
          </VStack>
        </Container>
      </Box>

      {/* ==================== 5. INVESTIMENTO ==================== */}
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
                <Text as="span" fontStyle="italic" bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`} bgClip="text">
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
                  features: ["1 usuário", "Análise + Agenda + Documentos", "Planilhas ilimitadas"],
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
                  features: ["Até 15 usuários", "Integrações Bling / Omie / Tiny", "OCR e auditoria completa"],
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
                  _hover={{ borderColor: `${p.cor}99`, transform: p.destaque ? { md: "scale(1.04)" } : "translateY(-2px)" }}
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
                        <Text fontSize="14px" color="white" lineHeight={1.5}>{f}</Text>
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
                    _hover={{ filter: "brightness(1.1)", bg: p.destaque ? undefined : "rgba(255,255,255,0.08)" }}
                    onClick={openModal}
                  >
                    Começar
                  </Button>
                </Box>
              ))}
            </Grid>
          </VStack>
        </Container>
      </Box>

      {/* ==================== 6. CTA FINAL ==================== */}
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
              <Text as="span" fontStyle="italic" bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink}, ${C.purpleLight})`} bgClip="text">
                crescer.
              </Text>
            </Heading>

            <Text fontSize={{ base: "17px", md: "20px" }} color={C.textDim} maxW="580px" lineHeight={1.55}>
              Monte seu escritório virtual em 10 minutos. Use seus dados. Aprove suas primeiras sugestões.
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
              onClick={openModal}
            >
              Montar meu escritório virtual
            </Button>

            <Text fontSize="14px" color={C.textMuted}>
              Comece grátis. Sem cartão.
            </Text>
          </VStack>
        </Container>
      </Box>

      {/* ==================== FOOTER ==================== */}
      <Box as="footer" borderTop="1px solid" borderColor={C.border} py={10}>
        <Container maxW="1160px" px={{ base: 5, md: 8 }}>
          <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
            <HStack spacing={2.5}>
              <Box w="28px" h="28px" borderRadius="8px" bgGradient={`linear(135deg, ${C.blue}, ${C.purple})`} display="flex" alignItems="center" justifyContent="center" fontSize="14px" fontWeight={700}>B</Box>
              <Text fontSize="14px" color={C.textDim}>© 2026 Blu · Escritório virtual com IA</Text>
            </HStack>
            <HStack spacing={5} fontSize="13px" color={C.textDim}>
              <Link _hover={{ color: "white" }}>Privacidade</Link>
              <Link _hover={{ color: "white" }}>Termos</Link>
              <Link _hover={{ color: "white" }}>Contato</Link>
            </HStack>
          </Flex>
        </Container>
      </Box>

    </Box>
  );
};

export default LandingPage;
