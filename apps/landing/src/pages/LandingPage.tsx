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
} from "@chakra-ui/react";
import { ChevronLeftIcon, ChevronRightIcon } from "@chakra-ui/icons";

// Imagens do carrossel Hero
const heroImages = [
  "/images/image 82.png",
  "/images/image 317.png",
  "/images/image 319.png",
  "/images/image 320.png",
  "/images/image 3212.png",
  "/images/image 499.png",
  "/images/image 501.png",
];

// Imagens do carrossel do Software/Dashboard
const softwareImages = [
  "/images/home.png",
  "/images/fontesdedados.png",
  "/images/lista.png",
  "/images/chat.png",
  "/images/fornecedores.png",
];

// Dados dos modais para cada card
const cardModals = [
  {
    id: "dados",
    bg: "#92daff",
    circleBg: "#77c7f0",
    title: "Transforme suas notas fiscais em insights",
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
        description: "Réguas de Conversão Automática: A VIZU identifica o timing de recompra e reativa clientes inativos automaticamente. É receita recorrente com esforço zero."
      },
      { 
        number: "3", 
        title: "Radar de Oportunidades e Antecipação", 
        description: "Não reaja ao mercado, antecipe-se. Identifique padrões de churn (cancelamento) antes que aconteçam ou descubra o momento exato em que um cliente está pronto para sua próxima compra."
      },
      { 
        number: "4", 
        title: "Interface Conversacional", 
        description: "Todos os produtos e módulos da Vizu contam com Agentes para te ajudar com sua operação a partir de linguagem natural. Gere relatórios, programe promoções para seus clientes, emita notas sem esforço e muito mais." 
      },
    ],
  },
];

// ========== SIGNUP MODAL COMPONENT ==========
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Erro ao enviar");
      }
      
      toast({
        title: "Cadastro realizado!",
        description: data.existing 
          ? "Seus dados já estão em nossa base. Entraremos em contato em breve."
          : "Entraremos em contato em breve.",
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
      <ModalOverlay bg="blackAlpha.600" />
      <ModalContent borderRadius="24px" p={6}>
        <ModalBody>
          <CloseButton 
            position="absolute" 
            top={4} 
            right={4} 
            onClick={onClose}
          />
          <Heading size="lg" mb={2}>Fale Conosco</Heading>
          <Text color="gray.600" mb={6}>
            Preencha seus dados e entraremos em contato.
          </Text>
          
          <form onSubmit={handleSubmit}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Nome</FormLabel>
                <Input
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  placeholder="Seu nome"
                  borderRadius="12px"
                />
              </FormControl>
              
              <FormControl isRequired>
                <FormLabel>E-mail</FormLabel>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="seu@email.com"
                  borderRadius="12px"
                />
              </FormControl>
              
              <FormControl>
                <FormLabel>Empresa</FormLabel>
                <Input
                  value={formData.empresa}
                  onChange={(e) => setFormData({ ...formData, empresa: e.target.value })}
                  placeholder="Nome da empresa"
                  borderRadius="12px"
                />
              </FormControl>
              
              <FormControl>
                <FormLabel>Telefone</FormLabel>
                <Input
                  value={formData.telefone}
                  onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                  placeholder="(11) 99999-9999"
                  borderRadius="12px"
                />
              </FormControl>
              
              <Button
                type="submit"
                bg="#000"
                color="white"
                w="100%"
                h="50px"
                borderRadius="full"
                isLoading={isLoading}
                _hover={{ bg: "#333" }}
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

// ========== LANDING PAGE COMPONENT ==========
const LandingPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [softwareImageIndex, setSoftwareImageIndex] = useState(0);
  const [activeModal, setActiveModal] = useState<number | null>(null);
  const [isSignupOpen, setIsSignupOpen] = useState(false);

  // Carrossel automático do Hero
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % heroImages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Carrossel automático do Software
  useEffect(() => {
    const interval = setInterval(() => {
      setSoftwareImageIndex((prev) => (prev + 1) % softwareImages.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handlePrevSoftwareImage = () => {
    setSoftwareImageIndex((prev) => (prev === 0 ? softwareImages.length - 1 : prev - 1));
  };

  const handleNextSoftwareImage = () => {
    setSoftwareImageIndex((prev) => (prev + 1) % softwareImages.length);
  };

  return (
    <Box w="100%" minH="100vh" bg="#9dc5f6">
      {/* ========== HERO SECTION ========== */}
      <Box minH="796px" position="relative" overflow="hidden">
        {/* Header */}
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
            <Image src="/images/Group 2049761270.png" alt="VIZU" h="28px" />
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
          </HStack>
        </Flex>

        {/* Imagens do carrossel */}
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
          >
            Sua estratégia não <br />
            pode ser um palpite.
          </Heading>

          {/* Feature Cards */}
          <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={8}>
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
                <Text fontSize={{ base: "24px", md: "34px" }} fontWeight={600} color="#000" lineHeight={1.2}>
                  Transforme suas notas fiscais em insights
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
                <Text fontSize={{ base: "24px", md: "34px" }} fontWeight={600} color="#000" lineHeight={1.2}>
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
                <Text fontSize={{ base: "24px", md: "34px" }} fontWeight={600} color="#000" lineHeight={1.2}>
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
          <Heading
            as="h2"
            fontSize={{ base: "36px", md: "48px" }}
            fontWeight={700}
            color="#000"
            textAlign="center"
            mb={4}
          >
            Visão Estratégica Sem Surpresas.
          </Heading>
          
          <Text
            fontSize={{ base: "16px", md: "20px" }}
            color="#000"
            textAlign="center"
            maxW="605px"
            mx="auto"
            mb={12}
          >
            Escolha o nível de contexto necessário para o seu crescimento. Nenhum contrato é vago.
          </Text>

          {/* Pricing Cards */}
          <Flex direction={{ base: "column", lg: "row" }} gap={6} justify="center" align="stretch">
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
              <Flex w="52px" h="52px" borderRadius="full" bg="#000" align="center" justify="center" mb={4}>
                <Text color="white" fontSize="20px" fontWeight={700}>V</Text>
              </Flex>
              <Text fontSize="30px" fontWeight={700} color="#0a0a0a" mb={4}>Base</Text>
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000">• Estruture, organize e higienize suas notas fiscais em um clique</Text>
                <Text fontSize="16px" color="#000">• Obtenha insights automaticamente</Text>
                <Text fontSize="16px" color="#000">• 4 módulos disponíveis: Clientes, Produtos, Pedidos/Vendas, Fornecedores</Text>
                <Text fontSize="16px" color="#000">• Agente de B.I</Text>
              </VStack>
              <Box mb={4}>
                <Text fontSize="14px" color="#666" textAlign="right">a partir de</Text>
                <Text fontSize="42px" fontWeight={600} color="#000" textAlign="right">R$999</Text>
              </Box>
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
                Fale Conosco
              </Button>
            </Box>

            {/* Card 2 - Platform */}
            <Box
              bg="white"
              borderRadius="24px"
              p={8}
              w={{ base: "100%", lg: "360px" }}
              minH="520px"
              display="flex"
              flexDirection="column"
            >
              <Flex w="52px" h="52px" borderRadius="full" bg="#000" align="center" justify="center" mb={4}>
                <Text color="white" fontSize="20px" fontWeight={700}>V</Text>
              </Flex>
              <Text fontSize="30px" fontWeight={700} color="#0a0a0a" mb={4}>Vizu Platform</Text>
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000">• Tudo do Vizu Base +</Text>
                <Text fontSize="16px" color="#000">• Emissão de NF-e automatizadas</Text>
                <Text fontSize="16px" color="#000">• Registro de vendas, estoque e fluxo de caixa integrados</Text>
                <Text fontSize="16px" color="#000">• Agente Estratégico: Mentor Financeiro</Text>
              </VStack>
              <Box mb={4}>
                <Text fontSize="14px" color="#666" textAlign="right">a partir de</Text>
                <Text fontSize="42px" fontWeight={600} color="#000" textAlign="right">R$1.499</Text>
              </Box>
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
                Fale Conosco
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
              <Flex w="52px" h="52px" borderRadius="full" bg="#000" align="center" justify="center" mb={4}>
                <Text color="white" fontSize="20px" fontWeight={700}>V</Text>
              </Flex>
              <Text fontSize="30px" fontWeight={700} color="#0a0a0a" mb={4}>Vizu Enterprise</Text>
              <VStack align="stretch" spacing={3} flex={1} mb={6}>
                <Text fontSize="16px" color="#000">• Vizu Platform +</Text>
                <Text fontSize="16px" color="#000">• Desenvolvimento de agentes sob medida</Text>
              </VStack>
              <Box mb={4}>
                <Text fontSize="14px" color="#666" textAlign="right">&nbsp;</Text>
                <Text fontSize="42px" fontWeight={600} color="#000" textAlign="right">Sob Medida</Text>
              </Box>
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
                Fale Conosco
              </Button>
            </Box>
          </Flex>
        </Container>
      </Box>

      {/* ========== CHATBOT SECTION ========== */}
      <Box bg="white">
        <Flex direction={{ base: "column", lg: "row" }} align="stretch" minH={{ base: "auto", lg: "600px" }}>
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
            <Text color="white" fontSize="24px">
              Chatbot da VIZU é treinado com o nosso DNA. Ele te entrega o contexto para a sua melhor decisão. Rápido. Cirúrgico.
            </Text>
          </Box>
          <Box 
            flex={1} 
            position="relative"
            bgImage="url('/images/image 316.png')"
            bgSize="cover"
            bgPosition="center"
            minH={{ base: "500px", lg: "600px" }}
          >
            <Image
              src="/images/Apple iPhone 15 Pro Black Titanium 1.png"
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
        <Flex direction={{ base: "column", lg: "row" }} align="stretch" minH="600px">
          <VStack align="start" flex={1} spacing={8} p={{ base: 6, md: 12 }} justify="center">
            <Heading
              as="h2"
              fontSize={{ base: "32px", md: "44px" }}
              fontWeight={600}
              color="white"
              lineHeight={1.2}
            >
              O painél da VIZU te ajuda a gerenciar melhor seus dados e metas de forma simples.
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
          <VStack align="start" flex={1} p={{ base: 6, md: 12 }} spacing={8} justify="center">
            <Text fontSize={{ base: "24px", md: "34px" }} color="#000" lineHeight={1.3}>
              A VIZU cria um projeto sob medida — para o seu negócio que atenda suas principais necessidades.
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
            <Image src="/images/image 500.png" alt="Soluções VIZU" w="100%" h="100%" objectFit="cover" />
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
          >
            Não fique tentando adivinhar <br />
            onde sua receita está escondida.
          </Heading>
          <Image src="/images/image 321.png" alt="CTA" maxH="300px" mx="auto" mb={8} />
          <Heading as="h3" fontSize={{ base: "24px", md: "37px" }} fontWeight={700} color="#000" mb={8}>
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
          <Heading as="h2" fontSize={{ base: "36px", md: "54px" }} fontWeight={600} color="#000" mb={12}>
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
                answer: "Absolutamente não. Nós construímos a Vizu justamente para que você não precise ser um analista de dados. Com o nosso agente Analista de B.I, você conversa com a plataforma como se estivesse no WhatsApp: basta perguntar \"Qual foi o produto mais vendido na região Sul?\" e a IA te responde em texto claro."
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
                      <Text fontSize="20px" fontWeight={500}>{item.question}</Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                </h3>
                <AccordionPanel pb={4}>
                  <Text color="gray.600" lineHeight={1.7}>{item.answer}</Text>
                </AccordionPanel>
              </AccordionItem>
            ))}
          </Accordion>
        </Container>
      </Box>

      {/* ========== FOOTER ========== */}
      <Box bg="#ff3e20" py={16} px={{ base: 6, md: 12 }}>
        <Container maxW="1280px">
          <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={12} mb={12}>
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
              <Flex w="100%" maxW="500px" borderBottom="1px solid white" pb={2}>
                <Input
                  placeholder="E-mail"
                  variant="unstyled"
                  color="white"
                  _placeholder={{ color: "white" }}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  flex={1}
                />
                <Button variant="unstyled" color="white">→</Button>
              </Flex>
            </VStack>

            <Grid templateColumns="repeat(2, 1fr)" gap={8}>
              <VStack align="start" spacing={4}>
                <Text color="white" fontWeight={500} fontSize="16px">VIZU</Text>
                {["Quem somos", "Porquê a VIZU", "Soluções", "Preços", "Fale conosco"].map((link) => (
                  <Link key={link} color="white" fontSize="16px" href="#">{link}</Link>
                ))}
              </VStack>
              <VStack align="start" spacing={4}>
                <Text color="white" fontWeight={500} fontSize="16px">Redes</Text>
                {["LinkedIn", "Instagram", "YouTube"].map((link) => (
                  <Link key={link} color="white" fontSize="16px" href="#">{link}</Link>
                ))}
              </VStack>
            </Grid>
          </Grid>

          <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
            <Text color="#000" fontSize="14px">©2025 VIZU - Todos os direitos reservados.</Text>
            <HStack spacing={4}>
              <Link color="white" fontSize="14px" href="#">Política de privacidade</Link>
              <Text color="white">·</Text>
              <Link color="white" fontSize="14px" href="#">Termos de uso</Link>
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
          <ModalContent bg={cardModals[activeModal].bg} m={0} borderRadius={0} minH="100vh">
            <ModalBody p={0} position="relative">
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
                <CloseButton size="lg" color="white" _hover={{ bg: "transparent" }} />
              </Flex>

              <Container maxW="1200px" py={16}>
                <Heading
                  as="h2"
                  fontSize={{ base: "32px", md: "40px" }}
                  fontWeight={600}
                  color="#000"
                  lineHeight={1.1}
                  mb={6}
                  maxW="500px"
                >
                  {cardModals[activeModal].title}
                </Heading>

                <Text fontSize="16px" fontWeight={500} color="#000" mb={12} maxW="400px">
                  {cardModals[activeModal].subtitle}
                </Text>

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
                          <Text fontSize="14px" fontWeight={600} color="#000">{item.number}</Text>
                          <Text fontSize="18px" fontWeight={600} color="#101828" textAlign="left">
                            {item.title}
                          </Text>
                        </HStack>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel pb={6} pt={0} pl={8}>
                        <Text fontSize="16px" fontWeight={400} color="#000" lineHeight={1.6}>
                          {item.description}
                        </Text>
                      </AccordionPanel>
                    </AccordionItem>
                  ))}
                </Accordion>

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

export default LandingPage;
