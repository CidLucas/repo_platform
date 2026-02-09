import React, { useState } from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  Input,
  Button,
  Checkbox,
  Image,
  CloseButton,
} from "@chakra-ui/react";

interface SignupModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Componente de Input estilizado
const FormInput: React.FC<{
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}> = ({ label, placeholder, value, onChange, type = "text", required = true }) => (
  <VStack align="stretch" spacing={1} w="100%">
    <HStack spacing={1}>
      <Text fontSize="14px" fontWeight={600} color="#000">
        {label}
      </Text>
      {required && (
        <Text fontSize="12px" color="#030712">*</Text>
      )}
    </HStack>
    <Input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      border="1px solid #000"
      borderRadius="full"
      h="48px"
      px={5}
      fontSize="14px"
      _placeholder={{ color: "#717182" }}
      _focus={{ borderColor: "#000", boxShadow: "none" }}
    />
  </VStack>
);

const SignupModal: React.FC<SignupModalProps> = ({ isOpen, onClose }) => {
  const [showSuccess, setShowSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state - simplified
  const [formData, setFormData] = useState({
    nome: "",
    email: "",
    empresa: "",
    telefone: "",
    termos: false,
  });

  const updateField = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleClose = () => {
    setShowSuccess(false);
    setFormData({
      nome: "",
      email: "",
      empresa: "",
      telefone: "",
      termos: false,
    });
    setError(null);
    onClose();
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    // Validação básica
    if (!formData.nome || !formData.email || !formData.empresa || !formData.telefone) {
      setError("Por favor, preencha todos os campos obrigatórios.");
      setLoading(false);
      return;
    }

    if (!formData.termos) {
      setError("Por favor, aceite os termos de serviço.");
      setLoading(false);
      return;
    }

    // Simular envio (aqui você pode integrar com um backend/webhook)
    try {
      // TODO: Integrar com backend para salvar lead
      console.log("Lead data:", formData);
      
      // Simula delay de envio
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setShowSuccess(true);
    } catch {
      setError("Erro ao enviar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="full">
      <ModalOverlay bg="blackAlpha.600" />
      <ModalContent bg="white" m={0} borderRadius={0} overflow="hidden">
        <ModalBody p={0} overflow="hidden">
          <Flex h="100vh" overflow="hidden">
            {/* Left side - Image */}
            {!showSuccess && (
              <Box
                flex="0 0 50%"
                maxW="50vw"
                display={{ base: "none", lg: "block" }}
                position="relative"
                overflow="hidden"
                h="100vh"
              >
                <Image
                  src="/image 82.png"
                  alt="VIZU"
                  w="100%"
                  h="100%"
                  objectFit="cover"
                  objectPosition="center center"
                />
              </Box>
            )}

            {/* Right side - Form */}
            <Box
              flex={!showSuccess ? 1 : "none"}
              w={!showSuccess ? "auto" : "100%"}
              p={{ base: 6, md: 10 }}
              position="relative"
              display="flex"
              flexDirection="column"
              justifyContent="center"
              h="100vh"
              overflow="hidden"
            >
              {/* Close button */}
              <CloseButton
                position="absolute"
                top={6}
                right={6}
                size="lg"
                onClick={handleClose}
              />

              {/* Form Content */}
              {!showSuccess && (
                <VStack spacing={4} maxW="460px" mx="auto" w="100%">
                  {/* Header */}
                  <VStack spacing={1} w="100%" align="flex-start" mb={2}>
                    <Text
                      fontSize={{ base: "28px", md: "36px" }}
                      fontWeight={600}
                      color="#000"
                      fontFamily="'Noto Looped Thai UI', sans-serif"
                      lineHeight={1.1}
                    >
                      Fale Conosco
                    </Text>
                    <Text fontSize="14px" color="#666">
                      Preencha seus dados e entraremos em contato
                    </Text>
                  </VStack>

                  <FormInput
                    label="Nome"
                    placeholder="Digite seu nome completo"
                    value={formData.nome}
                    onChange={(v) => updateField("nome", v)}
                  />

                  <FormInput
                    label="Email"
                    placeholder="Digite seu email"
                    type="email"
                    value={formData.email}
                    onChange={(v) => updateField("email", v)}
                  />

                  <FormInput
                    label="Nome da Empresa"
                    placeholder="Digite o nome da sua empresa"
                    value={formData.empresa}
                    onChange={(v) => updateField("empresa", v)}
                  />

                  <FormInput
                    label="Telefone"
                    placeholder="(11) 99999-9999"
                    type="tel"
                    value={formData.telefone}
                    onChange={(v) => updateField("telefone", v)}
                  />

                  {/* Error message */}
                  {error && (
                    <Text color="red.500" fontSize="14px" w="100%">
                      {error}
                    </Text>
                  )}

                  {/* Terms checkbox */}
                  <HStack w="100%" spacing={2} align="flex-start" mt={2}>
                    <Checkbox
                      isChecked={formData.termos}
                      onChange={(e) => updateField("termos", e.target.checked)}
                      colorScheme="blackAlpha"
                      borderColor="black"
                      mt={1}
                    />
                    <Text fontSize="12px" color="#666" lineHeight={1.4}>
                      Concordo com os{" "}
                      <Text as="span" textDecoration="underline" cursor="pointer">
                        Termos de Serviço
                      </Text>{" "}
                      e{" "}
                      <Text as="span" textDecoration="underline" cursor="pointer">
                        Política de Privacidade
                      </Text>
                    </Text>
                  </HStack>

                  {/* Submit button */}
                  <Button
                    w="100%"
                    h="52px"
                    bg="#000"
                    color="white"
                    borderRadius="full"
                    fontSize="16px"
                    fontWeight={600}
                    _hover={{ bg: "#333" }}
                    onClick={handleSubmit}
                    isLoading={loading}
                    loadingText="Enviando..."
                    mt={2}
                  >
                    ENVIAR
                  </Button>
                </VStack>
              )}

              {/* Success state */}
              {showSuccess && (
                <VStack spacing={6} maxW="500px" mx="auto" textAlign="center">
                  <Box
                    w="80px"
                    h="80px"
                    borderRadius="full"
                    bg="#92daff"
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                  >
                    <Text fontSize="40px">✓</Text>
                  </Box>
                  <Text
                    fontSize={{ base: "28px", md: "36px" }}
                    fontWeight={600}
                    color="#000"
                    fontFamily="'Noto Looped Thai UI', sans-serif"
                  >
                    Mensagem enviada!
                  </Text>
                  <Text fontSize="16px" color="#666" maxW="400px">
                    Obrigado pelo seu interesse! Nossa equipe entrará em contato em breve.
                  </Text>
                  <Button
                    bg="#000"
                    color="white"
                    borderRadius="full"
                    px={10}
                    py={6}
                    fontSize="16px"
                    fontWeight={600}
                    _hover={{ bg: "#333" }}
                    onClick={handleClose}
                  >
                    FECHAR
                  </Button>
                </VStack>
              )}
            </Box>
          </Flex>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default SignupModal;
