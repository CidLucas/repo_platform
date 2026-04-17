import React, { useState, useEffect } from "react";
import {
  Box,
  Flex,
  Heading,
  Text,
  Button,
  Image,
  VStack,
  HStack,
  Input,
  Link,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Grid,
  GridItem,
  Container,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  CloseButton,
  IconButton,
  FormControl,
  FormLabel,
  useToast,
  SimpleGrid,
} from "@chakra-ui/react";
import { ChevronLeftIcon, ChevronRightIcon, ArrowForwardIcon } from "@chakra-ui/icons";

// Dashboard screenshots carousel
const softwareImages = [
  "/images/home.png",
  "/images/fontesdedados.png",
  "/images/lista.png",
  "/images/chat.png",
  "/images/fornecedores.png",
];

// Feature detail modals data
const featureModals = [
  {
    id: "analytics",
    gradient: "linear(to-br, #3b82f6, #1d4ed8)",
    accentColor: "#3b82f6",
    title: "De dados brutos a decisões precisas",
    subtitle: "A Blu estrutura, limpa e transforma seus dados em dashboards prontos — sem SQL, sem planilhas, sem dor de cabeça.",
    items: [
      {
        number: "01",
        title: "Ingestão inteligente",
        description: "Suba dados de qualquer fonte — notas fiscais, ERPs, planilhas. A Blu faz os merges, joins e normalização automaticamente. Seus dados falam a mesma língua em minutos."
      },
      {
        number: "02",
        title: "Dashboards instantâneos",
        description: "Assim que os dados entram, você já tem visão completa de Clientes, Produtos, Pedidos e Fornecedores. Sem configuração. Sem espera."
      },
      {
        number: "03",
        title: "Agente analista de BI",
        description: "Pergunte em português: \"Qual foi o produto mais vendido no Sul este trimestre?\". O agente roda a query e te responde em segundos, com gráficos."
      },
      {
        number: "04",
        title: "Segurança enterprise",
        description: "Row Level Security, JWT, criptografia ponta a ponta. A informação certa chega apenas à pessoa certa. Infraestrutura de multinacional, sem time de TI."
      },
    ],
  },
  {
    id: "automation",
    gradient: "linear(to-br, #10b981, #059669)",
    accentColor: "#10b981",
    title: "Automatize o operacional. Foque no estratégico.",
    subtitle: "A Blu elimina tarefas manuais e repetitivas. Seu tempo volta para o que gera receita.",
    items: [
      {
        number: "01",
        title: "NF-e em um clique",
        description: "Emissão integrada ao seu fluxo de vendas. Conformidade fiscal garantida, erros de digitação eliminados. Segundos, não horas."
      },
      {
        number: "02",
        title: "Estoque + Vendas + Caixa sincronizados",
        description: "Quando uma venda acontece, o estoque baixa e o financeiro atualiza automaticamente. Visão 360º em tempo real."
      },
      {
        number: "03",
        title: "Pipeline comercial sem atrito",
        description: "De cotações a pedidos, a Blu remove a burocracia. Sua equipe fecha negócios em vez de preencher formulários."
      },
      {
        number: "04",
        title: "Agente financeiro estratégico",
        description: "Mais que controle de caixa — um mentor financeiro. Metas OKR, simulações de cenário e alertas preditivos sobre a saúde do seu negócio."
      },
    ],
  },
  {
    id: "intelligence",
    gradient: "linear(to-br, #a855f7, #7c3aed)",
    accentColor: "#a855f7",
    title: "Inteligência que antecipa o mercado",
    subtitle: "Pare de reagir. Com a Blu, você se antecipa ao churn, identifica oportunidades e cresce com precisão cirúrgica.",
    items: [
      {
        number: "01",
        title: "Decisões data-driven em segundos",
        description: "A IA processa milhões de combinações para te dizer: onde investir, o que estocar, qual cliente priorizar. Gestão baseada em fatos, não palpites."
      },
      {
        number: "02",
        title: "Reativação automática de clientes",
        description: "A Blu identifica o timing de recompra e reativa clientes inativos automaticamente. Receita recorrente com esforço zero."
      },
      {
        number: "03",
        title: "Radar de oportunidades",
        description: "Identifique padrões de churn antes que aconteçam. Descubra o momento exato em que um cliente está pronto para a próxima compra."
      },
      {
        number: "04",
        title: "Interface conversacional",
        description: "Todos os módulos têm agentes de IA. Gere relatórios, programe promoções, emita notas — tudo por linguagem natural."
      },
    ],
  },
];

// ========== SIGNUP MODAL ==========
interface SignupModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SignupModal: React.FC<SignupModalProps> = ({ isOpen, onClose }) => {
  const [formData, setFormData] = useState({
    nome: "",
    email: "",
    empresa: "",
    telefone: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Erro ao enviar");

      toast({
        title: "Pronto!",
        description: data.existing
          ? "Você já está em nossa base. Falaremos em breve."
          : "Recebemos seus dados. Entraremos em contato.",
        status: "success",
        duration: 5000,
        isClosable: true,
      });
      onClose();
      setFormData({ nome: "", email: "", empresa: "", telefone: "" });
    } catch {
      toast({
        title: "Erro ao enviar",
        description: "Tente novamente mais tarde.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md" isCentered>
      <ModalOverlay bg="blackAlpha.800" backdropFilter="blur(8px)" />
      <ModalContent
        bg="#1a1b2e"
        border="1px solid"
        borderColor="rgba(255,255,255,0.1)"
        borderRadius="1.5rem"
        p={8}
      >
        <ModalBody p={0}>
          <CloseButton
            position="absolute"
            top={4}
            right={4}
            onClick={onClose}
            color="whiteAlpha.600"
            _hover={{ color: "white" }}
          />
          <Heading size="lg" mb={2} fontFamily="'Playfair Display', serif" color="white">
            Vamos conversar
          </Heading>
          <Text color="whiteAlpha.600" mb={8} fontSize="sm">
            Preencha seus dados e mostramos como a Blu transforma sua operação.
          </Text>

          <form onSubmit={handleSubmit}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel color="whiteAlpha.700" fontSize="sm">Nome</FormLabel>
                <Input
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  placeholder="Seu nome"
                  bg="#0d0e1f"
                  border="1px solid rgba(255,255,255,0.08)"
                  borderRadius="0.75rem"
                  color="white"
                  _placeholder={{ color: "whiteAlpha.400" }}
                  _focus={{ borderColor: "#3b82f6", boxShadow: "0 0 0 1px #3b82f6" }}
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel color="whiteAlpha.700" fontSize="sm">E-mail</FormLabel>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="seu@email.com"
                  bg="#0d0e1f"
                  border="1px solid rgba(255,255,255,0.08)"
                  borderRadius="0.75rem"
                  color="white"
                  _placeholder={{ color: "whiteAlpha.400" }}
                  _focus={{ borderColor: "#3b82f6", boxShadow: "0 0 0 1px #3b82f6" }}
                />
              </FormControl>
              <FormControl>
                <FormLabel color="whiteAlpha.700" fontSize="sm">Empresa</FormLabel>
                <Input
                  value={formData.empresa}
                  onChange={(e) => setFormData({ ...formData, empresa: e.target.value })}
                  placeholder="Nome da empresa"
                  bg="#0d0e1f"
                  border="1px solid rgba(255,255,255,0.08)"
                  borderRadius="0.75rem"
                  color="white"
                  _placeholder={{ color: "whiteAlpha.400" }}
                  _focus={{ borderColor: "#3b82f6", boxShadow: "0 0 0 1px #3b82f6" }}
                />
              </FormControl>
              <FormControl>
                <FormLabel color="whiteAlpha.700" fontSize="sm">Telefone</FormLabel>
                <Input
                  value={formData.telefone}
                  onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                  placeholder="(11) 99999-9999"
                  bg="#0d0e1f"
                  border="1px solid rgba(255,255,255,0.08)"
                  borderRadius="0.75rem"
                  color="white"
                  _placeholder={{ color: "whiteAlpha.400" }}
                  _focus={{ borderColor: "#3b82f6", boxShadow: "0 0 0 1px #3b82f6" }}
                />
              </FormControl>
              <Button
                type="submit"
                w="100%"
                h="52px"
                borderRadius="full"
                bgGradient="linear(to-r, #3b82f6, #2563eb)"
                color="white"
                fontSize="sm"
                fontWeight={600}
                isLoading={isLoading}
                _hover={{ bgGradient: "linear(to-r, #2563eb, #1d4ed8)", boxShadow: "0 8px 24px rgba(59,130,246,0.4)" }}
              >
                Enviar
              </Button>
            </VStack>
          </form>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

// ========== METRIC COUNTER COMPONENT ==========
const AnimatedNumber: React.FC<{ target: number; suffix?: string; prefix?: string }> = ({ target, suffix = "", prefix = "" }) => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let frame: number;
    const duration = 2000;
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * target));
      if (progress < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [target]);
  return <>{prefix}{count.toLocaleString("pt-BR")}{suffix}</>;
};

// ========== LANDING PAGE ==========
const LandingPage: React.FC = () => {
  const [softwareImageIndex, setSoftwareImageIndex] = useState(0);
  const [activeModal, setActiveModal] = useState<number | null>(null);
  const [isSignupOpen, setIsSignupOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [email, setEmail] = useState("");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setSoftwareImageIndex((prev) => (prev + 1) % softwareImages.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box w="100%" minH="100vh" bg="#0d0e1f" color="white" overflowX="hidden">

      {/* ====== HEADER ====== */}
      <Flex
        as="header"
        w="100%"
        h="72px"
        align="center"
        justify="space-between"
        px={{ base: 6, md: 12 }}
        position="fixed"
        top={0}
        zIndex={100}
        bg={scrolled ? "rgba(13,14,31,0.9)" : "transparent"}
        backdropFilter={scrolled ? "blur(12px)" : "none"}
        borderBottom={scrolled ? "1px solid rgba(255,255,255,0.06)" : "none"}
        transition="all 0.3s"
      >
        <Text
          fontSize="xl"
          fontWeight={800}
          letterSpacing="-0.5px"
          bgGradient="linear(to-r, #3b82f6, #a855f7)"
          bgClip="text"
        >
          Blu
        </Text>
        <HStack spacing={8} display={{ base: "none", md: "flex" }}>
          <Link href="#features" color="whiteAlpha.700" fontSize="sm" _hover={{ color: "white" }}>Soluções</Link>
          <Link href="#product" color="whiteAlpha.700" fontSize="sm" _hover={{ color: "white" }}>Produto</Link>
          <Link href="#pricing" color="whiteAlpha.700" fontSize="sm" _hover={{ color: "white" }}>Planos</Link>
          <Link href="#faq" color="whiteAlpha.700" fontSize="sm" _hover={{ color: "white" }}>FAQ</Link>
        </HStack>
        <HStack spacing={3}>
          <Button
            variant="ghost"
            color="whiteAlpha.800"
            fontSize="sm"
            _hover={{ color: "white", bg: "whiteAlpha.100" }}
            display={{ base: "none", md: "flex" }}
            onClick={() => window.location.href = "/login"}
          >
            Entrar
          </Button>
          <Button
            bgGradient="linear(to-r, #3b82f6, #2563eb)"
            color="white"
            borderRadius="full"
            px={6}
            fontSize="sm"
            fontWeight={600}
            _hover={{ bgGradient: "linear(to-r, #2563eb, #1d4ed8)", boxShadow: "0 4px 16px rgba(59,130,246,0.4)" }}
            onClick={() => setIsSignupOpen(true)}
          >
            Começar agora
          </Button>
        </HStack>
      </Flex>

      {/* ====== HERO SECTION ====== */}
      <Box
        position="relative"
        pt={{ base: "140px", md: "180px" }}
        pb={{ base: "80px", md: "120px" }}
        textAlign="center"
        overflow="hidden"
      >
        {/* Background glow effects */}
        <Box
          position="absolute"
          top="-200px"
          left="50%"
          transform="translateX(-50%)"
          w="800px"
          h="800px"
          bg="radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%)"
          pointerEvents="none"
        />
        <Box
          position="absolute"
          top="100px"
          right="-200px"
          w="600px"
          h="600px"
          bg="radial-gradient(circle, rgba(168,85,247,0.1) 0%, transparent 70%)"
          pointerEvents="none"
        />

        <Container maxW="900px" position="relative" zIndex={1}>
          {/* Badge */}
          <Flex justify="center" mb={6}>
            <Box
              bg="rgba(59,130,246,0.1)"
              border="1px solid rgba(59,130,246,0.2)"
              borderRadius="full"
              px={4}
              py={1.5}
            >
              <Text fontSize="xs" fontWeight={600} color="#3b82f6" letterSpacing="wider" textTransform="uppercase">
                Agentes de IA para negócios
              </Text>
            </Box>
          </Flex>

          <Heading
            as="h1"
            fontSize={{ base: "2.5rem", md: "4.5rem", lg: "5rem" }}
            fontWeight={400}
            fontFamily="'Playfair Display', serif"
            lineHeight={{ base: 1.15, md: 1.1 }}
            mb={6}
          >
            Inteligência que{" "}
            <Box
              as="span"
              bgGradient="linear(to-r, #3b82f6, #a855f7)"
              bgClip="text"
            >
              move
            </Box>
            <br />
            o seu negócio
          </Heading>

          <Text
            fontSize={{ base: "lg", md: "xl" }}
            color="whiteAlpha.600"
            maxW="600px"
            mx="auto"
            mb={10}
            lineHeight={1.7}
          >
            Conecte seus dados em minutos. Libere agentes de IA que analisam, automatizam e
            antecipam — para que você decida com clareza e cresça com confiança.
          </Text>

          <HStack spacing={4} justify="center" flexWrap="wrap">
            <Button
              size="lg"
              bgGradient="linear(to-r, #3b82f6, #2563eb)"
              color="white"
              borderRadius="full"
              px={8}
              h="56px"
              fontSize="md"
              fontWeight={600}
              _hover={{ bgGradient: "linear(to-r, #2563eb, #1d4ed8)", boxShadow: "0 8px 32px rgba(59,130,246,0.4)", transform: "translateY(-2px)" }}
              transition="all 0.2s"
              rightIcon={<ArrowForwardIcon />}
              onClick={() => setIsSignupOpen(true)}
            >
              Comece grátis
            </Button>
            <Button
              size="lg"
              variant="outline"
              borderColor="whiteAlpha.200"
              color="white"
              borderRadius="full"
              px={8}
              h="56px"
              fontSize="md"
              fontWeight={500}
              _hover={{ bg: "whiteAlpha.100", borderColor: "whiteAlpha.300" }}
              onClick={() => setIsSignupOpen(true)}
            >
              Agendar demo
            </Button>
          </HStack>

          {/* Social proof metrics */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={8} mt={20} maxW="700px" mx="auto">
            {[
              { value: 150, suffix: "+", label: "Empresas ativas" },
              { value: 2, suffix: "M+", label: "Registros processados" },
              { value: 99, suffix: "%", label: "Uptime garantido" },
              { value: 40, suffix: "%", label: "Economia de tempo" },
            ].map((stat) => (
              <VStack key={stat.label} spacing={1}>
                <Text fontSize={{ base: "2xl", md: "3xl" }} fontWeight={700} color="white">
                  <AnimatedNumber target={stat.value} suffix={stat.suffix} />
                </Text>
                <Text fontSize="xs" color="whiteAlpha.500" textTransform="uppercase" letterSpacing="wider">
                  {stat.label}
                </Text>
              </VStack>
            ))}
          </SimpleGrid>
        </Container>
      </Box>

      {/* ====== FEATURES SECTION ====== */}
      <Box id="features" py={{ base: 16, md: 24 }} position="relative">
        <Container maxW="1200px">
          <VStack spacing={4} textAlign="center" mb={16}>
            <Text fontSize="xs" fontWeight={600} color="#3b82f6" letterSpacing="wider" textTransform="uppercase">
              Soluções
            </Text>
            <Heading
              as="h2"
              fontSize={{ base: "2rem", md: "3.5rem" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
            >
              Sua estratégia não pode{" "}
              <Box as="span" bgGradient="linear(to-r, #ff6b35, #ff006e)" bgClip="text">
                ser um palpite
              </Box>
            </Heading>
            <Text fontSize="lg" color="whiteAlpha.500" maxW="550px">
              Três pilares que transformam dados em vantagem competitiva real.
            </Text>
          </VStack>

          <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={6}>
            {/* Analytics Card */}
            <GridItem>
              <Box
                bg="#1a1b2e"
                borderRadius="1.25rem"
                border="1px solid rgba(255,255,255,0.06)"
                p={8}
                h="100%"
                minH="380px"
                position="relative"
                cursor="pointer"
                onClick={() => setActiveModal(0)}
                transition="all 0.3s"
                overflow="hidden"
                _hover={{
                  borderColor: "rgba(59,130,246,0.3)",
                  boxShadow: "0 0 60px rgba(59,130,246,0.1)",
                  transform: "translateY(-4px)",
                }}
              >
                <Box position="absolute" top={0} left={0} w="100%" h="3px" bgGradient="linear(to-r, #3b82f6, #60a5fa)" />
                <Flex
                  w={14} h={14} borderRadius="1rem" align="center" justify="center"
                  bg="rgba(59,130,246,0.15)" mb={6}
                >
                  <Text fontSize="2xl">📊</Text>
                </Flex>
                <Text fontSize="sm" fontWeight={600} color="#3b82f6" textTransform="uppercase" letterSpacing="wider" mb={3}>
                  Analytics
                </Text>
                <Heading as="h3" fontSize="xl" fontWeight={600} color="white" mb={3} lineHeight={1.3}>
                  Transforme notas fiscais em insights acionáveis
                </Heading>
                <Text fontSize="sm" color="whiteAlpha.500" lineHeight={1.7} mb={6}>
                  Ingestão automática, dashboards prontos e um agente de BI que responde em português.
                </Text>
                <Flex align="center" gap={2} color="#3b82f6" fontSize="sm" fontWeight={500} mt="auto">
                  <Text>Explorar</Text>
                  <ArrowForwardIcon boxSize={3} />
                </Flex>
              </Box>
            </GridItem>

            {/* Automation Card */}
            <GridItem>
              <Box
                bg="#1a1b2e"
                borderRadius="1.25rem"
                border="1px solid rgba(255,255,255,0.06)"
                p={8}
                h="100%"
                minH="380px"
                position="relative"
                cursor="pointer"
                onClick={() => setActiveModal(1)}
                transition="all 0.3s"
                overflow="hidden"
                _hover={{
                  borderColor: "rgba(16,185,129,0.3)",
                  boxShadow: "0 0 60px rgba(16,185,129,0.1)",
                  transform: "translateY(-4px)",
                }}
              >
                <Box position="absolute" top={0} left={0} w="100%" h="3px" bgGradient="linear(to-r, #10b981, #34d399)" />
                <Flex
                  w={14} h={14} borderRadius="1rem" align="center" justify="center"
                  bg="rgba(16,185,129,0.15)" mb={6}
                >
                  <Text fontSize="2xl">⚡</Text>
                </Flex>
                <Text fontSize="sm" fontWeight={600} color="#10b981" textTransform="uppercase" letterSpacing="wider" mb={3}>
                  Automação
                </Text>
                <Heading as="h3" fontSize="xl" fontWeight={600} color="white" mb={3} lineHeight={1.3}>
                  Elimine o trabalho manual que trava o seu crescimento
                </Heading>
                <Text fontSize="sm" color="whiteAlpha.500" lineHeight={1.7} mb={6}>
                  NF-e em um clique, estoque sincronizado e pipeline comercial sem atrito.
                </Text>
                <Flex align="center" gap={2} color="#10b981" fontSize="sm" fontWeight={500}>
                  <Text>Explorar</Text>
                  <ArrowForwardIcon boxSize={3} />
                </Flex>
              </Box>
            </GridItem>

            {/* Intelligence Card */}
            <GridItem>
              <Box
                bg="#1a1b2e"
                borderRadius="1.25rem"
                border="1px solid rgba(255,255,255,0.06)"
                p={8}
                h="100%"
                minH="380px"
                position="relative"
                cursor="pointer"
                onClick={() => setActiveModal(2)}
                transition="all 0.3s"
                overflow="hidden"
                _hover={{
                  borderColor: "rgba(168,85,247,0.3)",
                  boxShadow: "0 0 60px rgba(168,85,247,0.1)",
                  transform: "translateY(-4px)",
                }}
              >
                <Box position="absolute" top={0} left={0} w="100%" h="3px" bgGradient="linear(to-r, #a855f7, #c084fc)" />
                <Flex
                  w={14} h={14} borderRadius="1rem" align="center" justify="center"
                  bg="rgba(168,85,247,0.15)" mb={6}
                >
                  <Text fontSize="2xl">🧠</Text>
                </Flex>
                <Text fontSize="sm" fontWeight={600} color="#a855f7" textTransform="uppercase" letterSpacing="wider" mb={3}>
                  Inteligência
                </Text>
                <Heading as="h3" fontSize="xl" fontWeight={600} color="white" mb={3} lineHeight={1.3}>
                  Antecipe o mercado antes dos seus concorrentes
                </Heading>
                <Text fontSize="sm" color="whiteAlpha.500" lineHeight={1.7} mb={6}>
                  Predição de churn, reativação automática e decisões data-driven em tempo real.
                </Text>
                <Flex align="center" gap={2} color="#a855f7" fontSize="sm" fontWeight={500}>
                  <Text>Explorar</Text>
                  <ArrowForwardIcon boxSize={3} />
                </Flex>
              </Box>
            </GridItem>
          </Grid>
        </Container>
      </Box>

      {/* ====== AI AGENT SECTION ====== */}
      <Box py={{ base: 16, md: 24 }} position="relative">
        <Container maxW="1200px">
          <Flex direction={{ base: "column", lg: "row" }} align="center" gap={16}>
            <VStack align="start" flex={1} spacing={6}>
              <Text fontSize="xs" fontWeight={600} color="#f97316" letterSpacing="wider" textTransform="uppercase">
                Agente inteligente
              </Text>
              <Heading
                as="h2"
                fontSize={{ base: "2rem", md: "3rem" }}
                fontFamily="'Playfair Display', serif"
                fontWeight={400}
                lineHeight={1.2}
              >
                Pergunte qualquer coisa.{" "}
                <Box as="span" color="#f97316">
                  Receba a resposta certa.
                </Box>
              </Heading>
              <Text fontSize="md" color="whiteAlpha.500" lineHeight={1.8} maxW="500px">
                O agente Blu é treinado com o DNA do seu negócio. Ele entende seu contexto,
                seus dados e suas metas — e entrega respostas cirúrgicas em linguagem natural.
              </Text>
              <VStack align="start" spacing={3} pt={4}>
                {[
                  "Análises complexas em segundos",
                  "Relatórios gerados por comando de voz",
                  "Alertas proativos sobre anomalias",
                  "Integrado a todos os módulos da plataforma",
                ].map((item) => (
                  <HStack key={item} spacing={3}>
                    <Box w={2} h={2} borderRadius="full" bg="#f97316" flexShrink={0} />
                    <Text fontSize="sm" color="whiteAlpha.700">{item}</Text>
                  </HStack>
                ))}
              </VStack>
              <Button
                mt={4}
                bgGradient="linear(to-r, #f97316, #ea580c)"
                color="white"
                borderRadius="full"
                px={8}
                h="48px"
                fontSize="sm"
                fontWeight={600}
                _hover={{ bgGradient: "linear(to-r, #ea580c, #c2410c)", boxShadow: "0 8px 24px rgba(249,115,22,0.3)" }}
                onClick={() => setIsSignupOpen(true)}
              >
                Testar o agente
              </Button>
            </VStack>

            {/* Chat mockup / phone image */}
            <Box
              flex={1}
              position="relative"
              minH={{ base: "400px", lg: "500px" }}
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Box
                position="absolute"
                w="400px" h="400px"
                bg="radial-gradient(circle, rgba(249,115,22,0.15) 0%, transparent 70%)"
                pointerEvents="none"
              />
              <Image
                src="/images/Apple iPhone 15 Pro Black Titanium 1.png"
                alt="Blu Agent"
                maxH={{ base: "380px", lg: "480px" }}
                position="relative"
                zIndex={1}
                filter="drop-shadow(0 20px 40px rgba(0,0,0,0.5))"
              />
            </Box>
          </Flex>
        </Container>
      </Box>

      {/* ====== PRODUCT SECTION ====== */}
      <Box id="product" py={{ base: 16, md: 24 }} position="relative">
        <Container maxW="1200px">
          <Flex direction={{ base: "column", lg: "row" }} align="center" gap={12}>
            {/* Dashboard carousel */}
            <Box
              flex={1}
              bg="#1a1b2e"
              borderRadius="1.5rem"
              border="1px solid rgba(255,255,255,0.06)"
              overflow="hidden"
              position="relative"
              minH={{ base: "300px", lg: "420px" }}
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              {softwareImages.map((img, index) => (
                <Image
                  key={index}
                  src={img}
                  alt={`Blu Dashboard ${index + 1}`}
                  position="absolute"
                  maxW="92%"
                  maxH="88%"
                  objectFit="contain"
                  opacity={softwareImageIndex === index ? 1 : 0}
                  transition="opacity 0.6s ease"
                  borderRadius="0.75rem"
                />
              ))}
              <IconButton
                aria-label="Previous"
                icon={<ChevronLeftIcon boxSize={6} />}
                position="absolute" left={3} top="50%" transform="translateY(-50%)"
                bg="whiteAlpha.100" color="white" borderRadius="full" size="sm"
                _hover={{ bg: "whiteAlpha.200" }}
                onClick={() => setSoftwareImageIndex((prev) => (prev === 0 ? softwareImages.length - 1 : prev - 1))}
              />
              <IconButton
                aria-label="Next"
                icon={<ChevronRightIcon boxSize={6} />}
                position="absolute" right={3} top="50%" transform="translateY(-50%)"
                bg="whiteAlpha.100" color="white" borderRadius="full" size="sm"
                _hover={{ bg: "whiteAlpha.200" }}
                onClick={() => setSoftwareImageIndex((prev) => (prev + 1) % softwareImages.length)}
              />
              <HStack position="absolute" bottom={4} spacing={1.5}>
                {softwareImages.map((_, index) => (
                  <Box
                    key={index}
                    w={softwareImageIndex === index ? "20px" : "6px"}
                    h="6px"
                    borderRadius="full"
                    bg={softwareImageIndex === index ? "white" : "whiteAlpha.300"}
                    cursor="pointer"
                    transition="all 0.3s"
                    onClick={() => setSoftwareImageIndex(index)}
                  />
                ))}
              </HStack>
            </Box>

            <VStack align="start" flex={1} spacing={6}>
              <Text fontSize="xs" fontWeight={600} color="#3b82f6" letterSpacing="wider" textTransform="uppercase">
                Plataforma
              </Text>
              <Heading
                as="h2"
                fontSize={{ base: "2rem", md: "2.5rem" }}
                fontFamily="'Playfair Display', serif"
                fontWeight={400}
                lineHeight={1.2}
              >
                Um painel que{" "}
                <Box as="span" bgGradient="linear(to-r, #3b82f6, #a855f7)" bgClip="text">
                  simplifica
                </Box>{" "}
                a complexidade
              </Heading>
              <Text fontSize="md" color="whiteAlpha.500" lineHeight={1.8}>
                Dashboard intuitivo com visão 360º do seu negócio. Clientes, produtos,
                fornecedores e finanças — tudo em um lugar, atualizado em tempo real.
              </Text>
              <SimpleGrid columns={2} spacing={4} pt={4} w="100%">
                {[
                  { label: "Conectores", desc: "BigQuery, Shopify, VTEX, PostgreSQL" },
                  { label: "Módulos", desc: "Clientes, Vendas, Estoque, Financeiro" },
                  { label: "Agentes IA", desc: "Analista, Estratégico, Operacional" },
                  { label: "Relatórios", desc: "Automáticos, exportáveis, compartilháveis" },
                ].map((item) => (
                  <Box key={item.label}>
                    <Text fontSize="sm" fontWeight={600} color="white" mb={1}>{item.label}</Text>
                    <Text fontSize="xs" color="whiteAlpha.500">{item.desc}</Text>
                  </Box>
                ))}
              </SimpleGrid>
            </VStack>
          </Flex>
        </Container>
      </Box>

      {/* ====== PRICING SECTION ====== */}
      <Box id="pricing" py={{ base: 16, md: 24 }} position="relative">
        <Box
          position="absolute" inset={0}
          bgGradient="linear(to-b, #0d0e1f, #111233, #0d0e1f)"
          pointerEvents="none"
        />
        <Container maxW="1200px" position="relative" zIndex={1}>
          <VStack spacing={4} textAlign="center" mb={16}>
            <Text fontSize="xs" fontWeight={600} color="#fbbf24" letterSpacing="wider" textTransform="uppercase">
              Planos
            </Text>
            <Heading
              as="h2"
              fontSize={{ base: "2rem", md: "3.5rem" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
            >
              Visão estratégica{" "}
              <Box as="span" color="#fbbf24">sem surpresas</Box>
            </Heading>
            <Text fontSize="lg" color="whiteAlpha.500" maxW="550px">
              Duas plataformas, três níveis cada. Escolha o que faz sentido para o seu momento.
            </Text>
          </VStack>

          {/* ── Small Business Platform ── */}
          <Box mb={16}>
            <Flex align="center" gap={3} mb={8}>
              <Box bg="rgba(59,130,246,0.15)" borderRadius="full" px={4} py={1.5}>
                <Text fontSize="xs" fontWeight={700} color="#3b82f6" textTransform="uppercase" letterSpacing="wider">
                  Pequenas Empresas
                </Text>
              </Box>
              <Box h="1px" flex={1} bg="rgba(255,255,255,0.06)" />
            </Flex>

            <Flex direction={{ base: "column", lg: "row" }} gap={6} justify="center" align="stretch">
              {/* Small — Painel de Controle */}
              <Box
                bg="#1a1b2e"
                borderRadius="1.5rem"
                border="1px solid rgba(255,255,255,0.06)"
                p={8}
                flex={1}
                display="flex"
                flexDirection="column"
                transition="all 0.3s"
                _hover={{ borderColor: "rgba(59,130,246,0.2)", transform: "translateY(-4px)" }}
              >
                <Text fontSize="2xl" fontWeight={700} color="white" mb={2}>Painel de Controle</Text>
                <Text fontSize="sm" color="whiteAlpha.500" mb={6}>
                  Dashboards prontos e dados organizados para enxergar seu negócio com clareza.
                </Text>
                <VStack align="start" spacing={3} flex={1} mb={8}>
                  {[
                    "Ingestão e limpeza automática de dados",
                    "Dashboards de Clientes, Produtos, Pedidos",
                    "Visão consolidada de receita e estoque",
                    "Exportação de relatórios",
                  ].map((item) => (
                    <HStack key={item} spacing={3}>
                      <Box w={1.5} h={1.5} borderRadius="full" bg="#3b82f6" flexShrink={0} />
                      <Text fontSize="sm" color="whiteAlpha.700">{item}</Text>
                    </HStack>
                  ))}
                </VStack>
                <Text fontSize="xs" color="whiteAlpha.400" mb={1}>a partir de</Text>
                <Text fontSize="3xl" fontWeight={700} color="white" mb={6}>R$ 499<Text as="span" fontSize="sm" color="whiteAlpha.500">/mês</Text></Text>
                <Button
                  w="100%"
                  h="52px"
                  borderRadius="full"
                  bg="transparent"
                  color="white"
                  border="1px solid rgba(255,255,255,0.15)"
                  _hover={{ bg: "whiteAlpha.100", borderColor: "rgba(255,255,255,0.3)" }}
                  fontSize="sm"
                  fontWeight={600}
                  onClick={() => setIsSignupOpen(true)}
                >
                  Começar agora
                </Button>
              </Box>

              {/* Small — Assistentes Digitais (Featured) */}
              <Box
                bg="#1a1b2e"
                borderRadius="1.5rem"
                border="1px solid rgba(59,130,246,0.3)"
                p={8}
                flex={1}
                display="flex"
                flexDirection="column"
                position="relative"
                overflow="hidden"
                boxShadow="0 0 80px rgba(59,130,246,0.1)"
                transition="all 0.3s"
                _hover={{ transform: "translateY(-4px)" }}
              >
                <Box position="absolute" top={0} left={0} w="100%" h="3px" bgGradient="linear(to-r, #3b82f6, #a855f7)" />
                <Flex justify="space-between" align="center" mb={4}>
                  <Text fontSize="2xl" fontWeight={700} color="white">Assistentes Digitais</Text>
                  <Box bg="rgba(168,85,247,0.15)" borderRadius="full" px={3} py={1}>
                    <Text fontSize="xs" fontWeight={600} color="#a855f7">POPULAR</Text>
                  </Box>
                </Flex>
                <Text fontSize="sm" color="whiteAlpha.500" mb={6}>
                  Agentes de IA que respondem perguntas, geram relatórios e automatizam tarefas do dia a dia.
                </Text>
                <VStack align="start" spacing={3} flex={1} mb={8}>
                  {[
                    "Tudo do Painel de Controle",
                    "Agente de BI — pergunte em português",
                    "Emissão de NF-e automatizada",
                    "Alertas inteligentes de estoque e caixa",
                    "Pipeline comercial sem atrito",
                  ].map((item) => (
                    <HStack key={item} spacing={3}>
                      <Box w={1.5} h={1.5} borderRadius="full" bg="#a855f7" flexShrink={0} />
                      <Text fontSize="sm" color="whiteAlpha.700">{item}</Text>
                    </HStack>
                  ))}
                </VStack>
                <Text fontSize="xs" color="whiteAlpha.400" mb={1}>a partir de</Text>
                <Text fontSize="3xl" fontWeight={700} color="white" mb={6}>R$ 999<Text as="span" fontSize="sm" color="whiteAlpha.500">/mês</Text></Text>
                <Button
                  w="100%"
                  h="52px"
                  borderRadius="full"
                  bgGradient="linear(to-r, #3b82f6, #2563eb)"
                  color="white"
                  fontSize="sm"
                  fontWeight={600}
                  _hover={{ bgGradient: "linear(to-r, #2563eb, #1d4ed8)", boxShadow: "0 8px 24px rgba(59,130,246,0.4)" }}
                  onClick={() => setIsSignupOpen(true)}
                >
                  Começar agora
                </Button>
              </Box>

              {/* Small — Sob Medida */}
              <Box
                bg="#1a1b2e"
                borderRadius="1.5rem"
                border="1px solid rgba(255,255,255,0.06)"
                p={8}
                flex={1}
                display="flex"
                flexDirection="column"
                transition="all 0.3s"
                _hover={{ borderColor: "rgba(16,185,129,0.2)", transform: "translateY(-4px)" }}
              >
                <Text fontSize="2xl" fontWeight={700} color="white" mb={2}>Sob Medida</Text>
                <Text fontSize="sm" color="whiteAlpha.500" mb={6}>
                  Agentes customizados e integrações específicas para a sua operação.
                </Text>
                <VStack align="start" spacing={3} flex={1} mb={8}>
                  {[
                    "Tudo dos Assistentes Digitais",
                    "Agentes de IA personalizados",
                    "Integrações sob demanda (ERP, CRM, etc.)",
                    "Suporte prioritário",
                    "Onboarding dedicado",
                  ].map((item) => (
                    <HStack key={item} spacing={3}>
                      <Box w={1.5} h={1.5} borderRadius="full" bg="#10b981" flexShrink={0} />
                      <Text fontSize="sm" color="whiteAlpha.700">{item}</Text>
                    </HStack>
                  ))}
                </VStack>
                <Text fontSize="3xl" fontWeight={700} color="white" mb={6}>Sob medida</Text>
                <Button
                  w="100%"
                  h="52px"
                  borderRadius="full"
                  bg="transparent"
                  color="white"
                  border="1px solid rgba(255,255,255,0.15)"
                  _hover={{ bg: "whiteAlpha.100", borderColor: "rgba(255,255,255,0.3)" }}
                  fontSize="sm"
                  fontWeight={600}
                  onClick={() => setIsSignupOpen(true)}
                >
                  Fale conosco
                </Button>
              </Box>
            </Flex>
          </Box>

          {/* ── Medium Business Platform ── */}
          <Box>
            <Flex align="center" gap={3} mb={8}>
              <Box bg="rgba(168,85,247,0.15)" borderRadius="full" px={4} py={1.5}>
                <Text fontSize="xs" fontWeight={700} color="#a855f7" textTransform="uppercase" letterSpacing="wider">
                  Médias Empresas
                </Text>
              </Box>
              <Box h="1px" flex={1} bg="rgba(255,255,255,0.06)" />
            </Flex>

            <Flex direction={{ base: "column", lg: "row" }} gap={6} justify="center" align="stretch">
              {/* Medium — Painel de Controle */}
              <Box
                bg="#1a1b2e"
                borderRadius="1.5rem"
                border="1px solid rgba(255,255,255,0.06)"
                p={8}
                flex={1}
                display="flex"
                flexDirection="column"
                transition="all 0.3s"
                _hover={{ borderColor: "rgba(168,85,247,0.2)", transform: "translateY(-4px)" }}
              >
                <Text fontSize="2xl" fontWeight={700} color="white" mb={2}>Painel de Controle</Text>
                <Text fontSize="sm" color="whiteAlpha.500" mb={6}>
                  Visão 360º com dashboards avançados, multi-filial e controle granular de acesso.
                </Text>
                <VStack align="start" spacing={3} flex={1} mb={8}>
                  {[
                    "Dashboards avançados multi-filial",
                    "Controle de acesso por função (RLS)",
                    "Módulos: Clientes, Produtos, Pedidos, Fornecedores, Financeiro",
                    "Histórico e auditoria de dados",
                  ].map((item) => (
                    <HStack key={item} spacing={3}>
                      <Box w={1.5} h={1.5} borderRadius="full" bg="#a855f7" flexShrink={0} />
                      <Text fontSize="sm" color="whiteAlpha.700">{item}</Text>
                    </HStack>
                  ))}
                </VStack>
                <Text fontSize="xs" color="whiteAlpha.400" mb={1}>a partir de</Text>
                <Text fontSize="3xl" fontWeight={700} color="white" mb={6}>R$ 1.499<Text as="span" fontSize="sm" color="whiteAlpha.500">/mês</Text></Text>
                <Button
                  w="100%"
                  h="52px"
                  borderRadius="full"
                  bg="transparent"
                  color="white"
                  border="1px solid rgba(255,255,255,0.15)"
                  _hover={{ bg: "whiteAlpha.100", borderColor: "rgba(255,255,255,0.3)" }}
                  fontSize="sm"
                  fontWeight={600}
                  onClick={() => setIsSignupOpen(true)}
                >
                  Começar agora
                </Button>
              </Box>

              {/* Medium — Assistentes Digitais (Featured) */}
              <Box
                bg="#1a1b2e"
                borderRadius="1.5rem"
                border="1px solid rgba(168,85,247,0.3)"
                p={8}
                flex={1}
                display="flex"
                flexDirection="column"
                position="relative"
                overflow="hidden"
                boxShadow="0 0 80px rgba(168,85,247,0.1)"
                transition="all 0.3s"
                _hover={{ transform: "translateY(-4px)" }}
              >
                <Box position="absolute" top={0} left={0} w="100%" h="3px" bgGradient="linear(to-r, #a855f7, #ec4899)" />
                <Flex justify="space-between" align="center" mb={4}>
                  <Text fontSize="2xl" fontWeight={700} color="white">Assistentes Digitais</Text>
                  <Box bg="rgba(236,72,153,0.15)" borderRadius="full" px={3} py={1}>
                    <Text fontSize="xs" fontWeight={600} color="#ec4899">RECOMENDADO</Text>
                  </Box>
                </Flex>
                <Text fontSize="sm" color="whiteAlpha.500" mb={6}>
                  IA estratégica com agentes financeiros, analíticos e operacionais para escalar com inteligência.
                </Text>
                <VStack align="start" spacing={3} flex={1} mb={8}>
                  {[
                    "Tudo do Painel de Controle",
                    "Agente analista de BI avançado",
                    "Agente financeiro estratégico (OKRs, simulações)",
                    "Automação de NF-e, estoque e caixa",
                    "Predição de churn e reativação automática",
                    "Pipeline comercial automatizado",
                  ].map((item) => (
                    <HStack key={item} spacing={3}>
                      <Box w={1.5} h={1.5} borderRadius="full" bg="#ec4899" flexShrink={0} />
                      <Text fontSize="sm" color="whiteAlpha.700">{item}</Text>
                    </HStack>
                  ))}
                </VStack>
                <Text fontSize="xs" color="whiteAlpha.400" mb={1}>a partir de</Text>
                <Text fontSize="3xl" fontWeight={700} color="white" mb={6}>R$ 2.499<Text as="span" fontSize="sm" color="whiteAlpha.500">/mês</Text></Text>
                <Button
                  w="100%"
                  h="52px"
                  borderRadius="full"
                  bgGradient="linear(to-r, #a855f7, #ec4899)"
                  color="white"
                  fontSize="sm"
                  fontWeight={600}
                  _hover={{ boxShadow: "0 8px 24px rgba(168,85,247,0.4)" }}
                  onClick={() => setIsSignupOpen(true)}
                >
                  Começar agora
                </Button>
              </Box>

              {/* Medium — Sob Medida */}
              <Box
                bg="#1a1b2e"
                borderRadius="1.5rem"
                border="1px solid rgba(255,255,255,0.06)"
                p={8}
                flex={1}
                display="flex"
                flexDirection="column"
                transition="all 0.3s"
                _hover={{ borderColor: "rgba(16,185,129,0.2)", transform: "translateY(-4px)" }}
              >
                <Text fontSize="2xl" fontWeight={700} color="white" mb={2}>Sob Medida</Text>
                <Text fontSize="sm" color="whiteAlpha.500" mb={6}>
                  Infraestrutura dedicada, SLA garantido e agentes construídos para o seu processo.
                </Text>
                <VStack align="start" spacing={3} flex={1} mb={8}>
                  {[
                    "Tudo dos Assistentes Digitais",
                    "Agentes de IA 100% personalizados",
                    "Infraestrutura dedicada",
                    "SLA e suporte white-glove",
                    "Onboarding com time de especialistas",
                    "API aberta para integrações custom",
                  ].map((item) => (
                    <HStack key={item} spacing={3}>
                      <Box w={1.5} h={1.5} borderRadius="full" bg="#10b981" flexShrink={0} />
                      <Text fontSize="sm" color="whiteAlpha.700">{item}</Text>
                    </HStack>
                  ))}
                </VStack>
                <Text fontSize="3xl" fontWeight={700} color="white" mb={6}>Sob medida</Text>
                <Button
                  w="100%"
                  h="52px"
                  borderRadius="full"
                  bg="transparent"
                  color="white"
                  border="1px solid rgba(255,255,255,0.15)"
                  _hover={{ bg: "whiteAlpha.100", borderColor: "rgba(255,255,255,0.3)" }}
                  fontSize="sm"
                  fontWeight={600}
                  onClick={() => setIsSignupOpen(true)}
                >
                  Fale conosco
                </Button>
              </Box>
            </Flex>
          </Box>
        </Container>
      </Box>

      {/* ====== CTA SECTION ====== */}
      <Box py={{ base: 16, md: 24 }} position="relative" overflow="hidden">
        <Box
          position="absolute"
          top="50%" left="50%"
          transform="translate(-50%, -50%)"
          w="900px" h="900px"
          bg="radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 60%)"
          pointerEvents="none"
        />
        <Container maxW="800px" textAlign="center" position="relative" zIndex={1}>
          <Heading
            as="h2"
            fontSize={{ base: "2rem", md: "3.5rem" }}
            fontFamily="'Playfair Display', serif"
            fontWeight={400}
            lineHeight={1.15}
            mb={6}
          >
            Sua receita está escondida{" "}
            <Box as="span" bgGradient="linear(to-r, #3b82f6, #a855f7)" bgClip="text">
              nos seus dados
            </Box>
          </Heading>
          <Text fontSize="lg" color="whiteAlpha.500" mb={10} maxW="500px" mx="auto">
            A Blu encontra, organiza e entrega para você as decisões que faltam para o seu próximo salto.
          </Text>
          <Button
            size="lg"
            bgGradient="linear(to-r, #3b82f6, #a855f7)"
            color="white"
            borderRadius="full"
            px={10}
            h="60px"
            fontSize="md"
            fontWeight={600}
            _hover={{ boxShadow: "0 8px 40px rgba(59,130,246,0.35)", transform: "translateY(-2px)" }}
            transition="all 0.2s"
            rightIcon={<ArrowForwardIcon />}
            onClick={() => setIsSignupOpen(true)}
          >
            Comece a tomar decisões melhores
          </Button>
        </Container>
      </Box>

      {/* ====== FAQ SECTION ====== */}
      <Box id="faq" py={{ base: 16, md: 24 }}>
        <Container maxW="800px">
          <VStack spacing={4} textAlign="center" mb={12}>
            <Text fontSize="xs" fontWeight={600} color="#3b82f6" letterSpacing="wider" textTransform="uppercase">
              Dúvidas frequentes
            </Text>
            <Heading
              as="h2"
              fontSize={{ base: "2rem", md: "3rem" }}
              fontFamily="'Playfair Display', serif"
              fontWeight={400}
            >
              Perguntas e respostas
            </Heading>
          </VStack>
          <Accordion allowMultiple>
            {[
              {
                question: "O que acontece depois que eu começo a usar a Blu?",
                answer: "Nossa tecnologia faz a ingestão e higienização dos seus dados automaticamente. Em poucos minutos, o que era uma confusão de planilhas vira dashboards limpos e organizados. A partir daí, você já acessa todos os módulos e pode usar os agentes de IA."
              },
              {
                question: "Preciso entender de dados ou SQL para usar?",
                answer: "Não. A Blu foi construída para que você converse com a plataforma em linguagem natural. Pergunte \"Qual foi o produto mais vendido na região Sul?\" e o agente te responde com texto claro e gráficos."
              },
              {
                question: "Como a Blu transforma dados em informação útil?",
                answer: "Nós processamos seus dados para identificar padrões de compra, níveis de estoque e saúde do fluxo de caixa. A plataforma limpa duplicidades, organiza em KPIs visuais e mostra onde você está ganhando ou perdendo dinheiro."
              },
              {
                question: "A plataforma ajuda a definir metas e estratégias?",
                answer: "Sim. Você pode desdobrar objetivos do seu negócio, acompanhar OKRs em tempo real e receber insights automáticos que avisam se você está no caminho certo para bater a meta do mês."
              },
              {
                question: "Posso automatizar atividades rotineiras?",
                answer: "Com certeza. Emissão de NF-e automatizada, registro de vendas reflete no estoque e caixa instantaneamente. Automação de agendamentos e cotações para que sua equipe foque em vender."
              },
              {
                question: "Quais integrações estão disponíveis?",
                answer: "BigQuery, PostgreSQL, MySQL, Shopify, VTEX, Loja Integrada, upload de CSV/Excel. Além dos conectores nativos, nossa API aberta permite integrar com qualquer sistema."
              },
              {
                question: "Posso testar antes de contratar?",
                answer: "Sim. Oferecemos um período de demonstração para que você explore os módulos e veja como a IA transforma a sua visão sobre o seu negócio. Sem compromisso."
              },
            ].map((item, index) => (
              <AccordionItem
                key={index}
                border="none"
                borderBottom="1px solid rgba(255,255,255,0.06)"
              >
                <h3>
                  <AccordionButton py={5} _hover={{ bg: "transparent" }}>
                    <Box flex="1" textAlign="left">
                      <Text fontSize="md" fontWeight={500} color="white">{item.question}</Text>
                    </Box>
                    <AccordionIcon color="whiteAlpha.500" />
                  </AccordionButton>
                </h3>
                <AccordionPanel pb={6}>
                  <Text color="whiteAlpha.600" lineHeight={1.8} fontSize="sm">{item.answer}</Text>
                </AccordionPanel>
              </AccordionItem>
            ))}
          </Accordion>
        </Container>
      </Box>

      {/* ====== FOOTER ====== */}
      <Box
        py={16}
        px={{ base: 6, md: 12 }}
        borderTop="1px solid rgba(255,255,255,0.06)"
      >
        <Container maxW="1200px">
          <Grid templateColumns={{ base: "1fr", lg: "2fr 1fr 1fr" }} gap={12} mb={12}>
            <VStack align="start" spacing={6}>
              <Text
                fontSize="2xl"
                fontWeight={800}
                bgGradient="linear(to-r, #3b82f6, #a855f7)"
                bgClip="text"
              >
                Blu
              </Text>
              <Text fontSize="sm" color="whiteAlpha.500" maxW="350px" lineHeight={1.8}>
                Inteligência artificial que transforma dados em decisões.
                Para empresas que querem crescer com clareza, velocidade e confiança.
              </Text>
              <Flex w="100%" maxW="400px" bg="#1a1b2e" borderRadius="full" overflow="hidden" border="1px solid rgba(255,255,255,0.06)">
                <Input
                  placeholder="Seu e-mail"
                  variant="unstyled"
                  color="white"
                  _placeholder={{ color: "whiteAlpha.400" }}
                  px={5}
                  py={3}
                  flex={1}
                  fontSize="sm"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <Button
                  bgGradient="linear(to-r, #3b82f6, #2563eb)"
                  color="white"
                  borderRadius="full"
                  px={6}
                  m={1}
                  fontSize="sm"
                  _hover={{ bgGradient: "linear(to-r, #2563eb, #1d4ed8)" }}
                  onClick={() => setIsSignupOpen(true)}
                >
                  Inscrever
                </Button>
              </Flex>
            </VStack>

            <VStack align="start" spacing={4}>
              <Text color="whiteAlpha.400" fontWeight={600} fontSize="xs" textTransform="uppercase" letterSpacing="wider">Produto</Text>
              {["Soluções", "Planos", "Integrações", "Segurança", "API"].map((link) => (
                <Link key={link} color="whiteAlpha.600" fontSize="sm" href="#" _hover={{ color: "white" }}>{link}</Link>
              ))}
            </VStack>
            <VStack align="start" spacing={4}>
              <Text color="whiteAlpha.400" fontWeight={600} fontSize="xs" textTransform="uppercase" letterSpacing="wider">Empresa</Text>
              {["Sobre", "Blog", "Carreiras", "Contato"].map((link) => (
                <Link key={link} color="whiteAlpha.600" fontSize="sm" href="#" _hover={{ color: "white" }}>{link}</Link>
              ))}
              <Text color="whiteAlpha.400" fontWeight={600} fontSize="xs" textTransform="uppercase" letterSpacing="wider" pt={4}>Redes</Text>
              {["LinkedIn", "Instagram", "YouTube"].map((link) => (
                <Link key={link} color="whiteAlpha.600" fontSize="sm" href="#" _hover={{ color: "white" }}>{link}</Link>
              ))}
            </VStack>
          </Grid>

          <Flex
            justify="space-between"
            align="center"
            flexWrap="wrap"
            gap={4}
            pt={8}
            borderTop="1px solid rgba(255,255,255,0.06)"
          >
            <Text color="whiteAlpha.400" fontSize="xs">
              © 2025 Blu — Todos os direitos reservados.
            </Text>
            <HStack spacing={6}>
              <Link color="whiteAlpha.400" fontSize="xs" href="#" _hover={{ color: "whiteAlpha.700" }}>Política de privacidade</Link>
              <Link color="whiteAlpha.400" fontSize="xs" href="#" _hover={{ color: "whiteAlpha.700" }}>Termos de uso</Link>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* ====== FEATURE DETAIL MODALS ====== */}
      {activeModal !== null && (
        <Modal
          isOpen={activeModal !== null}
          onClose={() => setActiveModal(null)}
          size="full"
          motionPreset="slideInBottom"
        >
          <ModalOverlay bg="rgba(13,14,31,0.95)" backdropFilter="blur(8px)" />
          <ModalContent bg="#0d0e1f" m={0} borderRadius={0} minH="100vh">
            <ModalBody p={0} position="relative">
              <Flex
                position="fixed"
                top={8}
                right={8}
                bg="whiteAlpha.100"
                borderRadius="full"
                w="56px" h="56px"
                align="center"
                justify="center"
                cursor="pointer"
                onClick={() => setActiveModal(null)}
                zIndex={10}
                _hover={{ bg: "whiteAlpha.200" }}
                transition="all 0.2s"
              >
                <CloseButton size="lg" color="white" _hover={{ bg: "transparent" }} />
              </Flex>

              <Container maxW="700px" py={20}>
                <Box
                  bg={`${featureModals[activeModal].accentColor}15`}
                  borderRadius="full"
                  px={3}
                  py={1}
                  w="fit-content"
                  mb={6}
                >
                  <Text fontSize="xs" fontWeight={600} color={featureModals[activeModal].accentColor} textTransform="uppercase" letterSpacing="wider">
                    {featureModals[activeModal].id}
                  </Text>
                </Box>

                <Heading
                  as="h2"
                  fontSize={{ base: "2rem", md: "2.5rem" }}
                  fontFamily="'Playfair Display', serif"
                  fontWeight={400}
                  color="white"
                  lineHeight={1.2}
                  mb={4}
                >
                  {featureModals[activeModal].title}
                </Heading>

                <Text fontSize="md" color="whiteAlpha.500" mb={12} maxW="500px" lineHeight={1.8}>
                  {featureModals[activeModal].subtitle}
                </Text>

                <VStack spacing={0} align="stretch">
                  {featureModals[activeModal].items.map((item, idx) => (
                    <Box
                      key={idx}
                      borderTop="1px solid rgba(255,255,255,0.06)"
                      _last={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
                    >
                      <Accordion allowToggle>
                        <AccordionItem border="none">
                          <AccordionButton py={6} px={0} _hover={{ bg: "transparent" }}>
                            <HStack flex="1" spacing={4}>
                              <Text fontSize="xs" fontWeight={700} color={featureModals[activeModal].accentColor}>
                                {item.number}
                              </Text>
                              <Text fontSize="md" fontWeight={500} color="white" textAlign="left">
                                {item.title}
                              </Text>
                            </HStack>
                            <AccordionIcon color="whiteAlpha.400" />
                          </AccordionButton>
                          <AccordionPanel pb={6} pt={0} pl={10}>
                            <Text fontSize="sm" color="whiteAlpha.600" lineHeight={1.8}>
                              {item.description}
                            </Text>
                          </AccordionPanel>
                        </AccordionItem>
                      </Accordion>
                    </Box>
                  ))}
                </VStack>

                <HStack spacing={3} mt={12} justify="center">
                  {featureModals.map((_, idx) => (
                    <Box
                      key={idx}
                      w={activeModal === idx ? "32px" : "8px"}
                      h="8px"
                      borderRadius="full"
                      bg={activeModal === idx ? featureModals[activeModal].accentColor : "whiteAlpha.200"}
                      cursor="pointer"
                      transition="all 0.3s"
                      onClick={() => setActiveModal(idx)}
                    />
                  ))}
                </HStack>
              </Container>
            </ModalBody>
          </ModalContent>
        </Modal>
      )}

      {/* ====== SIGNUP MODAL ====== */}
      <SignupModal isOpen={isSignupOpen} onClose={() => setIsSignupOpen(false)} />
    </Box>
  );
};

export default LandingPage;
