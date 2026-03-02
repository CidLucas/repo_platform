import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
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
} from "@chakra-ui/react";
import { ChevronLeftIcon, ChevronRightIcon } from "@chakra-ui/icons";
import SignupModal from "../components/SignupModal";

// Imagens do carrossel Hero
const heroImages = [
  "/image 82.png",
  "/image 317.png",
  "/image 319.png",
  "/image 320.png",
  "/image 3212.png",
  "/image 499.png",
  "/image 501.png",
];

// Imagens do carrossel do Software/Dashboard
const softwareImages = [
  "/home.png",
  "/fontesdedados.png",
  "/lista.png",
  "/chat.png",
  "/fornecedores.png",
];

// Dados dos modais para cada card
const cardModals = [
  {
    id: "dados",
    bg: "#92daff",
    circleBg: "#77c7f0",
    title: "Transforme seus dados em informação",
    subtitle: "Com o VIZU Analytics, estruturamos seus dados, do diagnóstico à oportunidade em segundos.",
    items: [
      {
        number: "1",
        title: "Estruturação Facilitada",
        description: "Esqueça integrações complexas. Com o Vizu Data Ingestion, você sobe dados de qualquer fonte e nós cuidamos do trabalho pesado: fazemos os merges, joins e a normalização automática para que seus dados falem a mesma língua."
      },
      {
        number: "2",
        title: "Insights Automáticos",
        description: "Não perca tempo criando gráficos do zero. Assim que os dados são estruturados, renderizamos dashboards prontos com foco no que move o ponteiro: Produtos, Clientes, Pedidos e Fornecedores."
      },
      {
        number: "3",
        title: "Agente de B.I",
        description: "Chega de depender de fórmulas de Excel ou SQL. Utilize nosso Agente de B.I para extrair análises profundas e fazer queries complexas usando apenas linguagem natural. É como perguntar para um analista e receber a resposta na hora."
      },
      {
        number: "4",
        title: "Segurança e Autonomia",
        description: "Tenha infraestrutura de multinacional sem precisar de um time de TI. Cuidamos de servidores e bancos de dados com segurança de ponta via RLS (Row Level Security) e JWT, garantindo que a informação certa chegue apenas à pessoa certa."
      },
    ],
  },
  {
    id: "erp",
    bg: "#fff856",
    circleBg: "#f1e93c",
    title: "Elimine tarefas repetitivas do seu dia a dia",
    subtitle: "Com o VIZU Platform, você não perde tempo com tarefas manuais. Use esse tempo com o que realmente importa.",
    items: [
      {
        number: "1",
        title: "Emita notas fiscais em um clique",
        description: "Dê adeus aos portais governamentais lentos e ao preenchimento manual. Nossa emissão de NF-e é integrada ao seu fluxo de vendas, garantindo conformidade fiscal em segundos e reduzindo erros de digitação."
      },
      {
        number: "2",
        title: "Integre seu estoque com suas vendas e seu fluxo de caixa",
        description: "Tenha uma visão 360º da sua operação. Quando uma venda acontece, o estoque baixa e o financeiro sobe automaticamente. Controle sua quebra de estoque e saiba exatamente quanto tem no bolso em tempo real."
      },
      {
        number: "3",
        title: "Foque nas suas vendas",
        description: "Automatize o ciclo comercial. De agendamentos inteligentes a emissão de pedidos e cotações rápidas, removemos os atritos burocráticos para que sua equipe foque em fechar negócios, não em preencher formulários."
      },
      {
        number: "4",
        title: "Agente Estratégico",
        description: "Muito mais que um controle de caixa, um mentor financeiro ao seu lado. Utilize nosso Agente para estabelecer metas de OKR, simular cenários de crescimento e receber alertas preditivos sobre a saúde financeira do seu negócio."
      },
    ],
  },
  {
    id: "crm",
    bg: "#f9bbcb",
    circleBg: "#efa8ba",
    title: "Máxima Produtividade: Onde a Estratégia encontra a Operação",
    subtitle: "Elimine o desperdício de tempo e de dinheiro, transformando sua operação em uma estrutura enxuta, inteligente e de alto crescimento.",
    items: [
      {
        number: "1",
        title: "Decisões automáticas guiadas por Dados (Data-Driven)",

        description: "Pare de queimar neurônios com palpites. Nossa inteligência processa milhões de combinações de dados para te entregar o que realmente importa: onde investir, o que estocar e quem demitir ou promover. É a gestão baseada em fatos, disponível em segundos."
      },
      {
        number: "2",
        title: "Venda sem Esforço",
        description: "Réguas de Conversão Automática:A VIZU identifica o timing de recompra e reativa clientes inativos automaticamente. É receita recorrente com esforço zero."
      },
      {
        number: "3",
        title: "Radar de Oportunidades e Antecipação",
        description: "Não reaja ao mercado, antecipe-se. Identifique padrões de churn (cancelamento) antes que aconteçam ou descubra o momento exato em que um cliente está pronto para sua próxima compra."
      },
      {
        number: "4",
        title: "Interface Conversacional",
        description: "Todos os produtos e módulos da Vizu contam com Agentes para te ajudar com sua operação a partir de linguagem natural. Gere relatórios, programe promoções para seus clientes, emita notas sem esforço e muito mais. "
      },
    ],
  },
];

// Logo VIZU em SVG
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- SVG component available for alternative layouts
const VizuLogo: React.FC<{ color?: string; height?: string }> = ({
  color = "#000",
  height = "28px"
}) => (
  <svg
    height={height}
    viewBox="0 0 82 29"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Símbolo V estilizado com ponto */}
    <path
      d="M14.09 0C11.19 0 8.53 1.53 7.03 4.01L0 16.03C-0.42 16.76 0.11 17.67 0.95 17.67H6.16C7.24 17.67 8.24 17.1 8.77 16.18L14.09 6.89L19.41 16.18C19.94 17.1 20.94 17.67 22.02 17.67H27.23C28.07 17.67 28.6 16.76 28.18 16.03L21.15 4.01C19.65 1.53 16.99 0 14.09 0Z"
      fill={color}
    />
    <circle cx="14.09" cy="24.81" r="4" fill={color} />
    {/* I */}
    <path
      d="M34.07 5.76H40.72V28.44H34.07V5.76Z"
      fill={color}
    />
    {/* Z */}
    <path
      d="M44.91 5.76H66.12V10.76L52.12 22.44H66.52V28.44H43.91V23.44L58.31 11.76H44.91V5.76Z"
      fill={color}
    />
    {/* U */}
    <path
      d="M69.52 5.76H76.17V19.44C76.17 21.64 77.17 22.84 79.17 22.84C81.17 22.84 82.17 21.64 82.17 19.44V5.76H88.82V19.84C88.82 25.84 85.02 28.84 79.17 28.84C73.32 28.84 69.52 25.84 69.52 19.84V5.76Z"
      fill={color}
    />
  </svg>
);

// Landing Page baseada no design do Figma - VIZU LANDING PAGE
const LandingFinalPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [softwareImageIndex, setSoftwareImageIndex] = useState(0);
  const [activeModal, setActiveModal] = useState<number | null>(null);
  const [isSignupOpen, setIsSignupOpen] = useState(false);

  // Carrossel automático do Hero
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % heroImages.length);
    }, 5000); // Troca a cada 5 segundos

    return () => clearInterval(interval);
  }, []);

  // Carrossel automático do Software
  useEffect(() => {
    const interval = setInterval(() => {
      setSoftwareImageIndex((prev) => (prev + 1) % softwareImages.length);
    }, 4000); // Troca a cada 4 segundos

    return () => clearInterval(interval);
  }, []);

  // Handlers para navegação manual do carrossel de software
  const handlePrevSoftwareImage = () => {
    setSoftwareImageIndex((prev) => (prev === 0 ? softwareImages.length - 1 : prev - 1));
  };

  const handleNextSoftwareImage = () => {
    setSoftwareImageIndex((prev) => (prev + 1) % softwareImages.length);
  };

  return (
    <Box w="100%" minH="100vh" bg="#9dc5f6">
      {/* ========== HERO SECTION (com Header integrado) ========== */}
      <Box
        minH="796px"
        position="relative"
        overflow="hidden"
      >
        {/* ========== HEADER ========== */}
        <Flex
          as="header"
          w="100%"
          h="96px"
          bg="transparent"
          align="center"
          justify="space-between"
          px={{ base: 6, md: 12 }}
          position="absolute"
          top={0}
          left={0}
          right={0}
          zIndex={100}
        >
          <HStack spacing={2}>
            <Image src="/Group 2049761270.png" alt="VIZU" h="28px" />
          </HStack>
          <HStack spacing={4}>
            <Button
              bg="#000"
              color="#fff"
              borderRadius="full"
              px={8}
              py={6}
              fontWeight={600}
              fontSize="18px"
              _hover={{ bg: "#333" }}
              onClick={() => setIsSignupOpen(true)}
            >
              CADASTRO
            </Button>
            <Button
              bg="white"
              color="#0f0f0f"
              border="1px solid #000"
              borderRadius="full"
              px={8}
              py={6}
              fontWeight={600}
              fontSize="18px"
              _hover={{ bg: "#f0f0f0" }}
              onClick={() => navigate("/login")}
            >
              Entrar
            </Button>
          </HStack>
        </Flex>
        {/* Imagens do carrossel com transição */}
        {heroImages.map((img, index) => (
          <Box
            key={index}
            position="absolute"
            top={0}
            left={0}
            right={0}
            bottom={0}
            bgImage={`url('${img}')`}
            bgSize="cover"
            bgPosition="center 30%"
            bgRepeat="no-repeat"
            opacity={currentImageIndex === index ? 1 : 0}
            transition="opacity 1s ease-in-out"
          />
        ))}
        <Flex
          direction="column"
          align="center"
          justify="center"
          minH="796px"
          position="relative"
          zIndex={1}
          textAlign="center"
          px={4}
          pt="96px"
        >
          <Heading
            as="h1"
            fontSize={{ base: "36px", md: "90px" }}
            fontWeight={600}
            color="white"
            lineHeight={{ base: "40px", md: "88px" }}
            letterSpacing="0.35px"
            mb={8}
            fontFamily="'Noto Looped Thai UI', sans-serif"
          >
            Enxergue nos <br />
            seus dados o que <br />
            realmente importa.
          </Heading>
          <Button
            bg="white"
            color="#0f0f0f"
            border="1px solid #000"
            borderRadius="full"
            px={10}
            py={7}
            fontSize="20px"
            fontWeight={600}
            _hover={{ bg: "#f0f0f0" }}
            onClick={() => setIsSignupOpen(true)}
          >
            FALE CONOSCO
          </Button>

          {/* Indicadores do carrossel */}
          <HStack spacing={3} mt={8}>
            {heroImages.map((_, index) => (
              <Box
                key={index}
                w={currentImageIndex === index ? "32px" : "12px"}
                h="12px"
                borderRadius="full"
                bg={currentImageIndex === index ? "white" : "rgba(255,255,255,0.5)"}
                cursor="pointer"
                transition="all 0.3s ease"
                onClick={() => setCurrentImageIndex(index)}
              />
            ))}
          </HStack>
        </Flex>
      </Box>

      {/* ========== ESTRATÉGIA SECTION ========== */}
      <Box bg="white" py={20} px={{ base: 6, md: 12 }}>
        <Container maxW="1200px">
          <Heading
            as="h2"
            fontSize={{ base: "36px", md: "64px" }}
            fontWeight={600}
            color="#000"
            textAlign="center"
            mb={16}
            fontFamily="'Noto Looped Thai UI', sans-serif"
          >
            Sua estratégia não <br />
            pode ser um palpite.
          </Heading>

          {/* Feature Cards */}
          <Grid
            templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }}
            gap={8}
          >
            {/* Card 1 - Azul */}
            <GridItem>
              <Box
                bg="#92daff"
                borderRadius="24px"
                p={8}
                h="100%"
                minH="400px"
                position="relative"
                cursor="pointer"
                onClick={() => setActiveModal(0)}
                transition="transform 0.2s"
                _hover={{ transform: "scale(1.02)" }}
              >
                <Text
                  fontSize={{ base: "24px", md: "34px" }}
                  fontWeight={600}
                  color="#000"
                  lineHeight={1.2}
                >
                  Transforme qualquer dado em informação
                </Text>
                <Flex
                  position="absolute"
                  bottom={6}
                  right={6}
                  bg="#77c7f0"
                  borderRadius="full"
                  w="80px"
                  h="80px"
                  align="center"
                  justify="center"
                >
                  <Text fontSize="32px" fontWeight={300} color="white" opacity={0.8}>+</Text>
                </Flex>
              </Box>
            </GridItem>

            {/* Card 2 - Amarelo */}
            <GridItem>
              <Box
                bg="#fff856"
                borderRadius="24px"
                p={8}
                h="100%"
                minH="400px"
                position="relative"
                cursor="pointer"
                onClick={() => setActiveModal(1)}
                transition="transform 0.2s"
                _hover={{ transform: "scale(1.02)" }}
              >
                <Text
                  fontSize={{ base: "24px", md: "34px" }}
                  fontWeight={600}
                  color="#000"
                  lineHeight={1.2}
                >
                  Elimine tarefas repetitivas do seu dia a dia
                </Text>
                <Flex
                  position="absolute"
                  bottom={6}
                  right={6}
                  bg="#f1e93c"
                  borderRadius="full"
                  w="80px"
                  h="80px"
                  align="center"
                  justify="center"
                >
                  <Text fontSize="32px" fontWeight={300} color="white" opacity={0.8}>+</Text>
                </Flex>
              </Box>
            </GridItem>

            {/* Card 3 - Rosa */}
            <GridItem>
              <Box
                bg="#f9bbcb"
                borderRadius="24px"
                p={8}
                h="100%"
                minH="400px"
                position="relative"
                cursor="pointer"
                onClick={() => setActiveModal(2)}
                transition="transform 0.2s"
                _hover={{ transform: "scale(1.02)" }}
              >
                <Text
                  fontSize={{ base: "24px", md: "34px" }}
                  fontWeight={600}
                  color="#000"
                  lineHeight={1.2}
                >
                  Aumente a sua produtividade
                </Text>
                <Flex
                  position="absolute"
                  bottom={6}
                  right={6}
                  bg="#efa8ba"
                  borderRadius="full"
                  w="80px"
                  h="80px"
                  align="center"
                  justify="center"
                >
                  <Text fontSize="32px" fontWeight={300} color="white" opacity={0.8}>+</Text>
                </Flex>
              </Box>
            </GridItem>
          </Grid>
        </Container>
      </Box>

      {/* ========== PLANOS / PREÇOS SECTION ========== */}
      <Box bg="#fdc700" py={20} px={{ base: 6, md: 12 }} minH="600px">
        <Container maxW="1200px">
          {/* Title */}
          <Heading
            as="h2"
            fontSize={{ base: "36px", md: "48px" }}
            fontWeight={700}
            color="#000"
            textAlign="center"
            mb={4}
            fontFamily="'IBM Plex Sans', sans-serif"
          >
            Visão Estratégica Sem Surpresas.
          </Heading>

          {/* Subtitle */}
          <Text
            fontSize={{ base: "16px", md: "20px" }}
            color="#000"
            textAlign="center"
            maxW="605px"
            mx="auto"
            mb={12}
            fontFamily="'IBM Plex Sans', sans-serif"
          >
            Escolha o nível de contexto necessário para o seu crescimento. Nenhum contrato é vago.
          </Text>

          {/* Pricing Cards */}
          <Flex
            direction={{ base: "column", lg: "row" }}
            gap={6}
            justify="center"
            align="stretch"
          >
            {/* Card 1 - Base */}
            <Box
              bg="white"
              borderRadius="24px"
              p={8}
              w={{ base: "100%", lg: "360px" }}
              minH="520px"
              display="flex"
              flexDirection="column"
            >
              {/* Logo placeholder */}
              <Flex
                w="52px"
                h="52px"
                borderRadius="full"
                bg="#000"
                align="center"
                justify="center"
                mb={4}
              >
                <Text color="white" fontSize="20px" fontWeight={700}>V</Text>
              </Flex>

              {/* Plan name */}
              <Text
                fontSize="30px"
                fontWeight={700}
                color="#0a0a0a"
                mb={4}
                fontFamily="'IBM Plex Sans', sans-serif"
              >
                Base
              </Text>

              {/* Description */}
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Estruture, organize e higienize seus dados em um clique
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Obtenha insights automaticamente
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • 4 módulos disponíveis: Clientes, Produtos, Pedidos/Vendas, Fornecedores
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Agente de B.I
                </Text>
              </VStack>

              {/* Price */}
              <Box mb={4}>
                <Text
                  fontSize="14px"
                  color="#666"
                  textAlign="right"
                  fontFamily="'IBM Plex Sans', sans-serif"
                >
                  a partir de
                </Text>
                <Text
                  fontSize="42px"
                  fontWeight={600}
                  color="#000"
                  textAlign="right"
                  fontFamily="'IBM Plex Sans', sans-serif"
                >
                  R$999
                </Text>
              </Box>

              {/* CTA Button */}
              <Button
                bg="#000"
                color="white"
                borderRadius="full"
                w="100%"
                h="60px"
                fontSize="14px"
                fontWeight={500}
                onClick={() => setIsSignupOpen(true)}
                _hover={{ bg: "#333" }}
              >
                Começar agora
              </Button>
            </Box>

            {/* Card 2 - Skill */}
            <Box
              bg="white"
              borderRadius="24px"
              p={8}
              w={{ base: "100%", lg: "360px" }}
              minH="520px"
              display="flex"
              flexDirection="column"
            >
              {/* Logo placeholder */}
              <Flex
                w="52px"
                h="52px"
                borderRadius="full"
                bg="#000"
                align="center"
                justify="center"
                mb={4}
              >
                <Text color="white" fontSize="20px" fontWeight={700}>V</Text>
              </Flex>

              {/* Plan name */}
              <Text
                fontSize="30px"
                fontWeight={700}
                color="#0a0a0a"
                mb={4}
                fontFamily="'IBM Plex Sans', sans-serif"
              >
                Vizu Platform
              </Text>

              {/* Description */}
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Tudo do Vizu Base +
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Emissão de NF-e automatizadas
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Registro de vendas, estoque e fluxo de caixa integrados
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Agente Estratégico: Mentor Financeiro
                </Text>
              </VStack>

              {/* Price */}
              <Box mb={4}>
                <Text
                  fontSize="14px"
                  color="#666"
                  textAlign="right"
                  fontFamily="'IBM Plex Sans', sans-serif"
                >
                  a partir de
                </Text>
                <Text
                  fontSize="42px"
                  fontWeight={600}
                  color="#000"
                  textAlign="right"
                  fontFamily="'IBM Plex Sans', sans-serif"
                >
                  R$2.499
                </Text>
              </Box>

              {/* CTA Button */}
              <Button
                bg="#000"
                color="white"
                borderRadius="full"
                w="100%"
                h="60px"
                fontSize="14px"
                fontWeight={500}
                onClick={() => setIsSignupOpen(true)}
                _hover={{ bg: "#333" }}
              >
                Começar agora
              </Button>
            </Box>

            {/* Card 3 - Enterprise */}
            <Box
              bg="white"
              borderRadius="24px"
              p={8}
              w={{ base: "100%", lg: "360px" }}
              minH="520px"
              display="flex"
              flexDirection="column"
            >
              {/* Logo placeholder */}
              <Flex
                w="52px"
                h="52px"
                borderRadius="full"
                bg="#000"
                align="center"
                justify="center"
                mb={4}
              >
                <Text color="white" fontSize="20px" fontWeight={700}>V</Text>
              </Flex>

              {/* Plan name */}
              <Text
                fontSize="30px"
                fontWeight={700}
                color="#0a0a0a"
                mb={4}
                fontFamily="'IBM Plex Sans', sans-serif"
              >
                Vizu Enterprise
              </Text>

              {/* Description */}
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Vizu Platform +
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Desenvolvimento de agentes sob medida
                </Text>
              </VStack>

              {/* Price */}
              <Box mb={4}>
                <Text
                  fontSize="14px"
                  color="#666"
                  textAlign="right"
                  fontFamily="'IBM Plex Sans', sans-serif"
                >
                  &nbsp;
                </Text>
                <Text
                  fontSize="42px"
                  fontWeight={600}
                  color="#000"
                  textAlign="right"
                  fontFamily="'IBM Plex Sans', sans-serif"
                >
                  Fale Conosco
                </Text>
              </Box>

              {/* CTA Button */}
              <Button
                bg="white"
                color="#000"
                border="1px solid #000"
                borderRadius="full"
                w="100%"
                h="60px"
                fontSize="14px"
                fontWeight={500}
                onClick={() => setIsSignupOpen(true)}
                _hover={{ bg: "#f0f0f0" }}
              >
                Agende uma demo
              </Button>
            </Box>
          </Flex>
        </Container>
      </Box>

      {/* ========== CHATBOT / IA SECTION ========== */}
      <Box bg="white">
        <Flex direction={{ base: "column", lg: "row" }} align="stretch" minH={{ base: "auto", lg: "600px" }}>
          {/* Left Content - Vermelho */}
          <Box
            flex={1}
            bg="#ff562c"
            p={{ base: 6, md: 12 }}
            display="flex"
            flexDirection="column"
            justifyContent="space-between"
            minH={{ base: "400px", lg: "auto" }}
          >
            <Heading
              as="h2"
              fontSize={{ base: "32px", md: "44px" }}
              fontWeight={600}
              color="white"
              lineHeight={1.2}
              mb={8}
            >
              Uma Inteligência Útil. Você pergunta e ela te ajuda a decidir de forma estratégica.
            </Heading>
            <Text
              color="white"
              fontSize="24px"
            >
              Chatbot da VIZU é treinado com o nosso DNA. Ele te entrega o contexto para a sua melhor decisão. Rápido. Cirúrgico.
            </Text>
          </Box>

          {/* Right Image - Azul com imagem de fundo */}
          <Box
            flex={1}
            position="relative"
            bgImage="url('/image 316.png')"
            bgSize="cover"
            bgPosition="center"
            minH={{ base: "500px", lg: "600px" }}
          >
            <Image
              src="/Apple iPhone 15 Pro Black Titanium 1.png"
              alt="VIZU App"
              position="absolute"
              top="50%"
              left="50%"
              transform="translate(-50%, -50%)"
              maxH={{ base: "400px", lg: "500px" }}
              zIndex={1}
            />
          </Box>
        </Flex>
      </Box>

      {/* ========== DASHBOARD SECTION ========== */}
      <Box bg="#000">
        <Flex
          direction={{ base: "column", lg: "row" }}
          align="stretch"
          minH="600px"
        >
          <VStack align="start" flex={1} spacing={8} p={{ base: 6, md: 12 }} justify="center">
            <Heading
              as="h2"
              fontSize={{ base: "32px", md: "44px" }}
              fontWeight={600}
              color="white"
              lineHeight={1.2}
            >
              O painél da VIZU te ajuda e gerenciar melhor seus dados e metas de forma simples.
            </Heading>
            <Button
              bg="white"
              color="#0f0f0f"
              border="1px solid #000"
              borderRadius="full"
              px={10}
              py={7}
              fontSize="20px"
              fontWeight={600}
              _hover={{ bg: "#f0f0f0" }}
              onClick={() => setIsSignupOpen(true)}
            >
              Quero testar
            </Button>
          </VStack>
          <Box
            flex={1}
            bg="#1a1a2e"
            display="flex"
            alignItems="center"
            justifyContent="center"
            position="relative"
            overflow="hidden"
            minH={{ base: "400px", lg: "600px" }}
          >
            {/* Software Screenshots Carousel */}
            {softwareImages.map((img, index) => (
              <Image
                key={index}
                src={img}
                alt={`VIZU Software ${index + 1}`}
                position="absolute"
                maxW="90%"
                maxH="85%"
                objectFit="contain"
                opacity={softwareImageIndex === index ? 1 : 0}
                transition="opacity 0.5s ease-in-out"
                borderRadius="12px"
                boxShadow="0 20px 60px rgba(0,0,0,0.3)"
              />
            ))}

            {/* Navigation Arrows */}
            <IconButton
              aria-label="Previous image"
              icon={<ChevronLeftIcon boxSize={8} />}
              position="absolute"
              left={4}
              top="50%"
              transform="translateY(-50%)"
              bg="whiteAlpha.200"
              color="white"
              _hover={{ bg: "whiteAlpha.400" }}
              borderRadius="full"
              size="lg"
              onClick={handlePrevSoftwareImage}
            />
            <IconButton
              aria-label="Next image"
              icon={<ChevronRightIcon boxSize={8} />}
              position="absolute"
              right={4}
              top="50%"
              transform="translateY(-50%)"
              bg="whiteAlpha.200"
              color="white"
              _hover={{ bg: "whiteAlpha.400" }}
              borderRadius="full"
              size="lg"
              onClick={handleNextSoftwareImage}
            />

            {/* Dots indicator */}
            <HStack position="absolute" bottom={6} spacing={2}>
              {softwareImages.map((_, index) => (
                <Box
                  key={index}
                  w={softwareImageIndex === index ? "24px" : "8px"}
                  h="8px"
                  borderRadius="full"
                  bg={softwareImageIndex === index ? "white" : "whiteAlpha.400"}
                  cursor="pointer"
                  transition="all 0.3s ease"
                  onClick={() => setSoftwareImageIndex(index)}
                />
              ))}
            </HStack>
          </Box>
        </Flex>
      </Box>

      {/* ========== CUSTOM SOLUTIONS SECTION ========== */}
      <Box bg="white">
        <Flex direction={{ base: "column", lg: "row" }} minH="600px">
          <VStack
            align="start"
            flex={1}
            p={{ base: 6, md: 12 }}
            spacing={8}
            justify="center"
          >
            <Text
              fontSize={{ base: "24px", md: "34px" }}
              color="#000"
              lineHeight={1.3}
            >
              A VIZU cria um projeto sob medida — para o seu negócio que atenda suas atendendo suas principais necessidades.
            </Text>
            <Button
              bg="white"
              color="#0f0f0f"
              border="1px solid #000"
              borderRadius="full"
              px={10}
              py={7}
              fontSize="20px"
              fontWeight={600}
              _hover={{ bg: "#f0f0f0" }}
              onClick={() => setIsSignupOpen(true)}
            >
              FALE CONOSCO
            </Button>
          </VStack>
          <Box flex={1}>
            <Image
              src="/image 500.png"
              alt="Soluções VIZU"
              w="100%"
              h="100%"
              objectFit="cover"
            />
          </Box>
        </Flex>
      </Box>

      {/* ========== CTA SECTION ========== */}
      <Box bg="#fff856" py={20} px={{ base: 6, md: 12 }}>
        <Container maxW="1200px" textAlign="center">
          <Heading
            as="h2"
            fontSize={{ base: "36px", md: "64px" }}
            fontWeight={600}
            color="#000"
            lineHeight={1.1}
            mb={8}
            fontFamily="'Noto Looped Thai UI', sans-serif"
          >
            Não fique tentando adivinhar <br />
            onde sua receita está escondida.
          </Heading>
          <Image
            src="/image 321.png"
            alt="CTA"
            maxH="300px"
            mx="auto"
            mb={8}
          />
          <Heading
            as="h3"
            fontSize={{ base: "24px", md: "37px" }}
            fontWeight={700}
            color="#000"
            mb={8}
          >
            Deixe a gente te mostrar! Comece a tomar <br />
            as melhores decisões hoje mesmo
          </Heading>
          <Button
            bg="#000"
            color="white"
            borderRadius="full"
            px={10}
            py={7}
            fontSize="20px"
            fontWeight={600}
            _hover={{ bg: "#333" }}
            onClick={() => setIsSignupOpen(true)}
          >
            FALE CONOSCO
          </Button>
        </Container>
      </Box>

      {/* ========== FAQ SECTION ========== */}
      <Box bg="white" py={20} px={{ base: 6, md: 12 }}>
        <Container maxW="1200px">
          <Heading
            as="h2"
            fontSize={{ base: "36px", md: "54px" }}
            fontWeight={600}
            color="#000"
            mb={12}
          >
            FAQ
          </Heading>
          <Accordion allowMultiple>
            {[
              {
                question: "O que acontece depois que eu me inscrevo e começo a usar a VIZU?",
                answer: "O primeiro passo é a conexão. Nossa tecnologia faz a ingestão e a higienização dos seus dados de forma automática. Em poucos minutos, o que era uma confusão de planilhas ou sistemas antigos vira um dashboard limpo e organizado. A partir daí, você já pode acessar os módulos de Clientes, Produtos e Vendas, ou começar a emitir notas e controlar seu estoque pela Vizu Platform."
              },
              {
                question: "Preciso entender de dados para usar a VIZU?",
                answer: "Absolutamente não. Nós construímos a Vizu justamente para que você não precise ser um analista de dados. Com o nosso agente Analista de B.I , você conversa com a plataforma como se estivesse no WhatsApp: basta perguntar \"Qual foi o produto mais vendido na região Sul?\" e a IA te responde em texto claro."
              },
              {
                question: "Como a VIZU transforma meus dados em informação útil?",
                answer: "Nós não apenas \"guardamos\" dados; nós os processamos. A plataforma identifica padrões de comportamento de compra, níveis de estoque e saúde do fluxo de caixa. Ela limpa as duplicidades e organiza tudo em indicadores visuais (KPIs) que mostram exatamente onde você está ganhando ou perdendo dinheiro."
              },
              {
                question: "A plataforma ajuda a definir metas e estratégias?",
                answer: "Sim. No plano Skill, você tem acesso ao módulo de Metas e OKRs. Nele, você consegue desdobrar os objetivos do seu negócio dentro da plataforma e acompanhar o progresso em tempo real, recebendo insights automáticos que avisam se você está no caminho certo para bater a meta do mês."
              },
              {
                question: "Posso automatizar atividades rotineiras da minha empresa?",
                answer: "Com certeza. A Vizu nasceu para eliminar o \"trabalho braçal\". No Vizu ERP, a emissão de NF-e é automatizada e o registro de vendas reflete instantaneamente no seu estoque e fluxo de caixa. Além disso, oferecemos automação de agendamentos e cotações para que sua equipe foque em vender, não em preencher formulários."
              },
              {
                question: "Quais integrações estão disponíveis?",
                answer: "Nós nos conectamos com os principais meios de pagamento, marketplaces e ferramentas de gestão do mercado. Além disso, nossa estrutura de ingestão de dados é flexível para importar informações de diversos formatos, garantindo que nenhum dado valioso fique de fora da sua análise."
              },
              {
                question: "Posso testar antes de contratar?",
                answer: "Sim! Acreditamos que você precisa sentir a facilidade de ter os dados na palma da mão. Oferecemos um período de demonstração para que você explore os módulos e veja como a nossa IA transforma a sua visão sobre o seu próprio negócio."
              },
            ].map((item, index) => (
              <AccordionItem key={index} borderColor="#000">
                <h3>
                  <AccordionButton py={5}>
                    <Box flex="1" textAlign="left">
                      <Text fontSize="20px" fontWeight={500}>
                        {item.question}
                      </Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                </h3>
                <AccordionPanel pb={4}>
                  <Text color="gray.600" lineHeight={1.7}>
                    {item.answer}
                  </Text>
                </AccordionPanel>
              </AccordionItem>
            ))}
          </Accordion>
        </Container>
      </Box>

      {/* ========== FOOTER ========== */}
      <Box bg="#ff3e20" py={16} px={{ base: 6, md: 12 }}>
        <Container maxW="1280px">
          <Grid
            templateColumns={{ base: "1fr", lg: "1fr 1fr" }}
            gap={12}
            mb={12}
          >
            {/* Left - Newsletter */}
            <VStack align="start" spacing={6}>
              <Heading
                as="h3"
                fontSize={{ base: "32px", md: "48px" }}
                fontWeight={600}
                color="white"
                lineHeight={1.2}
              >
                Não perca mais tentando desvendar seus dados, fale conosco
              </Heading>
              <Flex
                w="100%"
                maxW="500px"
                borderBottom="1px solid white"
                pb={2}
              >
                <Input
                  placeholder="E-mail"
                  variant="unstyled"
                  color="white"
                  _placeholder={{ color: "white" }}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  flex={1}
                />
                <Button variant="unstyled" color="white">
                  →
                </Button>
              </Flex>
            </VStack>

            {/* Right - Links */}
            <Grid templateColumns="repeat(2, 1fr)" gap={8}>
              <VStack align="start" spacing={4}>
                <Text color="white" fontWeight={500} fontSize="16px">
                  VIZU
                </Text>
                {["Quem somos", "Porquê a VIZU", "Soluções", "Preços", "Fale conosco"].map(
                  (link) => (
                    <Link key={link} color="white" fontSize="16px">
                      {link}
                    </Link>
                  )
                )}
              </VStack>
              <VStack align="start" spacing={4}>
                <Text color="white" fontWeight={500} fontSize="16px">
                  Redes
                </Text>
                {["Foruns", "Codepen", "LinkedIn", "GitHub", "X"].map((link) => (
                  <Link key={link} color="white" fontSize="16px">
                    {link}
                  </Link>
                ))}
              </VStack>
            </Grid>
          </Grid>

          {/* Bottom */}
          <Flex
            justify="space-between"
            align="center"
            flexWrap="wrap"
            gap={4}
          >
            <Text color="#000" fontSize="14px">
              ©2025 VIZU - Todos os direitos reservados.
            </Text>
            <HStack spacing={4}>
              <Link color="white" fontSize="14px">
                Política de privacidade
              </Link>
              <Text color="white">·</Text>
              <Link color="white" fontSize="14px">
                Termos de uso
              </Link>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* ========== MODAIS DOS CARDS ========== */}
      {activeModal !== null && (
        <Modal
          isOpen={activeModal !== null}
          onClose={() => setActiveModal(null)}
          size="full"
          motionPreset="slideInBottom"
        >
          <ModalOverlay bg="blackAlpha.600" />
          <ModalContent
            bg={cardModals[activeModal].bg}
            m={0}
            borderRadius={0}
            minH="100vh"
          >
            <ModalBody p={0} position="relative">
              {/* Círculo decorativo com botão Fechar dentro */}
              <Flex
                position="absolute"
                top={8}
                right={8}
                bg={cardModals[activeModal].circleBg}
                borderRadius="full"
                w="96px"
                h="96px"
                align="center"
                justify="center"
                cursor="pointer"
                onClick={() => setActiveModal(null)}
                zIndex={10}
                _hover={{ opacity: 0.9 }}
                transition="opacity 0.2s"
              >
                <CloseButton
                  size="lg"
                  color="white"
                  _hover={{ bg: "transparent" }}
                />
              </Flex>

              {/* Conteúdo do Modal */}
              <Container maxW="1200px" py={16}>
                {/* Título */}
                <Heading
                  as="h2"
                  fontSize={{ base: "32px", md: "40px" }}
                  fontWeight={600}
                  color="#000"
                  lineHeight={1.1}
                  mb={6}
                  maxW="500px"
                  fontFamily="'Noto Looped Thai UI', sans-serif"
                >
                  {cardModals[activeModal].title}
                </Heading>

                {/* Subtítulo */}
                <Text
                  fontSize="16px"
                  fontWeight={500}
                  color="#000"
                  mb={12}
                  maxW="400px"
                >
                  {cardModals[activeModal].subtitle}
                </Text>

                {/* Lista de itens como Accordion */}
                <Accordion allowToggle maxW="650px">
                  {cardModals[activeModal].items.map((item, idx) => (
                    <AccordionItem
                      key={idx}
                      border="none"
                      borderTop="1px solid #000"
                      _last={{ borderBottom: "1px solid #000" }}
                    >
                      <AccordionButton py={6} px={0} _hover={{ bg: "transparent" }}>
                        <HStack flex="1" align="center" spacing={4}>
                          <Text
                            fontSize="14px"
                            fontWeight={600}
                            color="#000"
                            fontFamily="'Noto Looped Thai UI', sans-serif"
                          >
                            {item.number}
                          </Text>
                          <Text
                            fontSize="18px"
                            fontWeight={600}
                            color="#101828"
                            fontFamily="'Noto Looped Thai UI', sans-serif"
                            textAlign="left"
                          >
                            {item.title}
                          </Text>
                        </HStack>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel pb={6} pt={0} pl={8}>
                        <Text
                          fontSize="16px"
                          fontWeight={400}
                          color="#000"
                          lineHeight={1.6}
                        >
                          {item.description}
                        </Text>
                      </AccordionPanel>
                    </AccordionItem>
                  ))}
                </Accordion>

                {/* Indicadores de navegação */}
                <HStack spacing={2} mt={12} justify="center">
                  {cardModals.map((_, idx) => (
                    <Box
                      key={idx}
                      w={activeModal === idx ? "48px" : "9px"}
                      h="9px"
                      borderRadius="full"
                      bg={activeModal === idx ? "#000" : "#fff"}
                      cursor="pointer"
                      transition="all 0.3s ease"
                      onClick={() => setActiveModal(idx)}
                    />
                  ))}
                </HStack>
              </Container>
            </ModalBody>
          </ModalContent>
        </Modal>
      )}

      {/* ========== SIGNUP MODAL ========== */}
      <SignupModal isOpen={isSignupOpen} onClose={() => setIsSignupOpen(false)} />
    </Box>
  );
};

export default LandingFinalPage;
