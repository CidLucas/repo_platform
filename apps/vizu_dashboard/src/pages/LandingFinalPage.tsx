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
} from "@chakra-ui/react";
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

// Dados dos modais para cada card
const cardModals = [
  {
    id: "dados",
    bg: "#92daff",
    circleBg: "#77c7f0",
    title: "Transforme qualquer dado em informação",
    subtitle: "Com o VIZU Base, estruturamos seus dados, do diagnóstico a oportunidade em segundos",
    items: [
      { number: "1", title: "Ingestão facilitada", description: "" },
      { number: "2", title: "Limpeza e Normalização", description: "Com vizu data ingestion você consegue subir qualquer dado de qualquer fonte e fazemos merge, joins e normalizamos automaticamente" },
      { number: "3", title: "Liberdade e armazenamento", description: "" },
      { number: "4", title: "Vizualização de dados", description: "" },
    ],
  },
  {
    id: "metas",
    bg: "#fff856",
    circleBg: "#f1e93c",
    title: "Gere metas e insights personalizadas",
    subtitle: "Com o VIZU Insights, tenha a visão estratégica em suas mãos, sem depender de nenhuma outra plataforma.",
    items: [
      { number: "1", title: "Insights automáticos", description: "" },
      { number: "2", title: "Metas e tarefas", description: "Gere e personalize metas e tarefas para o seu negócio a partir dos insights identificados" },
      { number: "3", title: "IA/Robô insights", description: "" },
    ],
  },
  {
    id: "automacao",
    bg: "#f9bbcb",
    circleBg: "#efa8ba",
    title: "Elimine tarefas repetitivas do seu dia a dia",
    subtitle: "Com o VIZU Automação, você não perde tempo com tarefas manuais, use esse tempo com o que realmente importa.",
    items: [
      { number: "1", title: "Melhore sua comunicação com clientes", description: "" },
      { number: "2", title: "Automatize seu dia a dia", description: "Automatize processos repetitivos e ganhe tempo para focar no que realmente importa para o seu negócio." },
      { number: "3", title: "Soluções personalizadas", description: "" },
      { number: "4", title: "Integrações sem limites", description: "" },
    ],
  },
];

// Logo VIZU em SVG
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
    <circle cx="14.09" cy="24.81" r="4" fill={color}/>
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
  const [activeModal, setActiveModal] = useState<number | null>(null);
  const [isSignupOpen, setIsSignupOpen] = useState(false);

  // Carrossel automático
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % heroImages.length);
    }, 5000); // Troca a cada 5 segundos

    return () => clearInterval(interval);
  }, []);

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
                <Box
                  position="absolute"
                  bottom={6}
                  right={6}
                  bg="#77c7f0"
                  borderRadius="full"
                  w="80px"
                  h="80px"
                />
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
                  Gere metas e insights personalizadas
                </Text>
                <Box
                  position="absolute"
                  bottom={6}
                  right={6}
                  bg="#f1e93c"
                  borderRadius="full"
                  w="80px"
                  h="80px"
                />
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
                  Elimine tarefas repetitivas do seu dia a dia
                </Text>
                <Box
                  position="absolute"
                  bottom={6}
                  right={6}
                  bg="#efa8ba"
                  borderRadius="full"
                  w="80px"
                  h="80px"
                />
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
                Skill
              </Text>

              {/* Description */}
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Pacote Base
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Metas e OKR's de negócios para aumento de produtividade
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Automação de agendamento de consultas, cotações e vendas
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Query to Text: Converse com sua base de dados!
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
                Enterprise
              </Text>

              {/* Description */}
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Tudo do Base e do Skill
                </Text>
                <Text fontSize="16px" color="#000" fontFamily="'IBM Plex Sans', sans-serif">
                  • Desenvolvimento de agentes sob medida para automação de qualquer tarefa
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
            bg="#333"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            {/* Placeholder para imagem do software */}
            <Text color="gray.500" fontSize="24px">
              [Imagem do Software]
            </Text>
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

      {/* ========== TESTIMONIAL SECTION ========== */}
      <Box bg="#92daff">
        <Flex direction={{ base: "column", lg: "row" }} minH="600px">
          <Box flex={1}>
            <Image
              src="/image 177.png"
              alt="Depoimento"
              w="100%"
              h="100%"
              objectFit="cover"
            />
          </Box>
          <VStack
            align="start"
            flex={1}
            p={{ base: 6, md: 12 }}
            spacing={6}
            justify="center"
          >
            <Text
                fontSize={{ base: "24px", md: "34px" }}
                color="#000"
                lineHeight={1.3}
              >
                A VIZU encurtou a conversa — paramos de discutir relatórios e passamos a discutir ações.
              </Text>
              <Box>
                <Text fontSize="15px" color="#000" fontWeight={500}>
                  Fábio Santos
                </Text>
                <Text fontSize="12px" color="#000">
                  Coordenador de Operações
                </Text>
              </Box>
            </VStack>
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
              "O que acontece depois que eu me inscrevo e começo a usar a VIZU?",
              "Preciso entender de dados para usar a VIZU?",
              "Como a VIZU transforma meus dados em informação útil?",
              "A plataforma ajuda a definir metas e estratégias?",
              "Posso automatizar atividades rotineiras da minha empresa?",
              "Quais integrações estão disponíveis?",
              "Posso testar antes de contratar?",
            ].map((question, index) => (
              <AccordionItem key={index} borderColor="#000">
                <h3>
                  <AccordionButton py={5}>
                    <Box flex="1" textAlign="left">
                      <Text fontSize="20px" fontWeight={500}>
                        {question}
                      </Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                </h3>
                <AccordionPanel pb={4}>
                  <Text color="gray.600">
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
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
              {/* Botão Fechar */}
              <CloseButton
                position="absolute"
                top={6}
                right={6}
                size="lg"
                onClick={() => setActiveModal(null)}
                zIndex={10}
              />

              {/* Círculo decorativo */}
              <Box
                position="absolute"
                top={8}
                right={24}
                bg={cardModals[activeModal].circleBg}
                borderRadius="full"
                w="96px"
                h="96px"
              />

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

                {/* Lista de itens */}
                <VStack align="stretch" spacing={0} maxW="650px">
                  {cardModals[activeModal].items.map((item, idx) => (
                    <Box
                      key={idx}
                      py={6}
                      borderTop="1px solid #000"
                      _last={{ borderBottom: "1px solid #000" }}
                    >
                      <HStack align="start" spacing={4}>
                        <Text
                          fontSize="14px"
                          fontWeight={600}
                          color="#000"
                          fontFamily="'Noto Looped Thai UI', sans-serif"
                        >
                          {item.number}
                        </Text>
                        <VStack align="start" spacing={2}>
                          <Text
                            fontSize="18px"
                            fontWeight={600}
                            color="#101828"
                            fontFamily="'Noto Looped Thai UI', sans-serif"
                          >
                            {item.title}
                          </Text>
                          {item.description && (
                            <Text
                              fontSize="16px"
                              fontWeight={500}
                              color="#000"
                            >
                              {item.description}
                            </Text>
                          )}
                        </VStack>
                      </HStack>
                    </Box>
                  ))}
                </VStack>

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
