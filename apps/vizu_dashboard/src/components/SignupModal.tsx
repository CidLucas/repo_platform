import React, { useState, useContext } from "react";
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
  Select,
  CloseButton,
} from "@chakra-ui/react";
import { AuthContext } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";

interface SignupModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Componente de Step Indicator
const StepIndicator: React.FC<{ currentStep: number }> = ({ currentStep }) => {
  const steps = [
    { number: 1, label: "Empresa", bgColor: "#000", borderColor: "#000" },
    { number: 2, label: "Detalhes da conta", bgColor: "#ffec3e", borderColor: "#e9d62a" },
    { number: 3, label: "Confirmação", bgColor: "#f9bbcb", borderColor: "#f5a59d" },
  ];

  const getStepStyle = (step: typeof steps[0]) => {
    const isComplete = currentStep > step.number;
    const isCurrent = currentStep === step.number;
    
    if (isComplete) {
      return { bg: "#000", borderColor: "#000", textColor: "white" };
    }
    if (isCurrent) {
      return { bg: step.bgColor, borderColor: step.borderColor, textColor: step.number === 1 ? "white" : "#000" };
    }
    // Pending step
    return { bg: step.bgColor, borderColor: step.borderColor, textColor: "#000" };
  };

  return (
    <HStack spacing={0} justify="center" w="100%" maxW="624px" mx="auto">
      {steps.map((step, idx) => {
        const style = getStepStyle(step);
        return (
          <React.Fragment key={step.number}>
            {/* Linha antes (exceto primeiro) */}
            {idx > 0 && (
              <Box
                flex={1}
                h="2px"
                bg={currentStep >= step.number ? "#000" : "#d1d5dc"}
              />
            )}
            
            {/* Step circle */}
            <VStack spacing={1}>
              <Flex
                w="40px"
                h="40px"
                borderRadius="full"
                bg={style.bg}
                border="1px solid"
                borderColor={style.borderColor}
                align="center"
                justify="center"
              >
                <Text
                  color={style.textColor}
                  fontSize="16px"
                  fontWeight={400}
                  fontFamily="'Noto Looped Thai UI', sans-serif"
                >
                  {step.number}
                </Text>
              </Flex>
              <Text 
                fontSize="12px" 
                color="#0a0a0a"
                fontFamily="'Noto Looped Thai UI', sans-serif"
              >
                {step.label}
              </Text>
            </VStack>

            {/* Linha depois (exceto último) */}
            {idx < steps.length - 1 && (
              <Box
                flex={1}
                h="2px"
                bg={currentStep > step.number ? "#000" : "#d1d5dc"}
              />
            )}
          </React.Fragment>
        );
      })}
    </HStack>
  );
};

// Componente de Input estilizado
const FormInput: React.FC<{
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}> = ({ label, placeholder, value, onChange, type = "text", required = true }) => (
  <VStack align="stretch" spacing={2} w="100%">
    <HStack spacing={1}>
      <Text fontSize="15px" fontWeight={600} color="#000">
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
      h="54px"
      px={6}
      fontSize="14px"
      _placeholder={{ color: "#717182" }}
      _focus={{ borderColor: "#000", boxShadow: "none" }}
    />
  </VStack>
);

// Componente de Select estilizado
const FormSelect: React.FC<{
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  required?: boolean;
}> = ({ label, placeholder, value, onChange, options, required = true }) => (
  <VStack align="stretch" spacing={2} w="100%">
    <HStack spacing={1}>
      <Text fontSize="15px" fontWeight={600} color="#000">
        {label}
      </Text>
      {required && (
        <Text fontSize="12px" color="#030712">*</Text>
      )}
    </HStack>
    <Select
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      border="1px solid #000"
      borderRadius="full"
      h="54px"
      px={6}
      fontSize="14px"
      _focus={{ borderColor: "#000", boxShadow: "none" }}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </Select>
  </VStack>
);

// Info Row para tela de confirmação
const InfoRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Box py={6} borderTop="1px solid #000">
    <Text fontSize="18px" fontWeight={600} color="#101828" mb={2}>
      {label}
    </Text>
    <Text fontSize="16px" fontWeight={500} color="#000">
      {value}
    </Text>
  </Box>
);

const SignupModal: React.FC<SignupModalProps> = ({ isOpen, onClose }) => {
  const [step, setStep] = useState(1);
  const navigate = useNavigate();
  const auth = useContext(AuthContext);
  
  // Form state
  const [formData, setFormData] = useState({
    nome: "",
    cnpj: "",
    cidade: "",
    telefone: "",
    atividade: "",
    usuario: "",
    senha: "",
    confirmarSenha: "",
    termos: false,
  });

  const updateField = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleClose = () => {
    setStep(1);
    setFormData({
      nome: "",
      cnpj: "",
      cidade: "",
      telefone: "",
      atividade: "",
      usuario: "",
      senha: "",
      confirmarSenha: "",
      termos: false,
    });
    onClose();
  };

  // Adiciona estado para erros e loading
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Função para cadastro com Supabase
  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    if (!auth) {
      setError("Erro de autenticação. Tente novamente mais tarde.");
      setLoading(false);
      return;
    }
    if (!formData.usuario || !formData.senha) {
      setError("Usuário e senha são obrigatórios.");
      setLoading(false);
      return;
    }
    // Usa o campo usuario como email (ajuste conforme seu modelo)
    const { error } = await auth.signUp(
      formData.usuario,
      formData.senha,
      {
        nome: formData.nome,
        cnpj: formData.cnpj,
        cidade: formData.cidade,
        telefone: formData.telefone,
        atividade: formData.atividade,
      }
    );
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      handleNext();
      // Redireciona para dashboard após sucesso
      navigate("/dashboard");
    }
  };

  // Função para login social Google
  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    if (!auth) {
      setError("Erro de autenticação. Tente novamente mais tarde.");
      setLoading(false);
      return;
    }
    const { error } = await auth.signInWithGoogle();
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      // O Supabase já faz o redirect automático para /dashboard
    }
  };

  // Atividades de exemplo
  const atividades = [
    { value: "tecnologia", label: "Tecnologia" },
    { value: "varejo", label: "Varejo" },
    { value: "servicos", label: "Serviços" },
    { value: "industria", label: "Indústria" },
    { value: "alimentacao", label: "Alimentação" },
    { value: "saude", label: "Saúde" },
    { value: "educacao", label: "Educação" },
    { value: "outros", label: "Outros" },
  ];

  // Cidades de exemplo
  const cidades = [
    { value: "sao-paulo", label: "São Paulo" },
    { value: "rio-de-janeiro", label: "Rio de Janeiro" },
    { value: "belo-horizonte", label: "Belo Horizonte" },
    { value: "brasilia", label: "Brasília" },
    { value: "curitiba", label: "Curitiba" },
    { value: "porto-alegre", label: "Porto Alegre" },
    { value: "salvador", label: "Salvador" },
    { value: "fortaleza", label: "Fortaleza" },
  ];

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="full">
      <ModalOverlay bg="blackAlpha.600" />
      <ModalContent bg="white" m={0} borderRadius={0}>
        <ModalBody p={0}>
          <Flex minH="100vh">
            {/* Left side - Image (changes per step) */}
            {step < 4 && (
              <Box
                flex="0 0 50%"
                maxW="720px"
                display={{ base: "none", lg: "block" }}
                position="relative"
                overflow="hidden"
              >
                <Image
                  src={step === 1 ? "/image 60.png" : step === 2 ? "/image 61.png" : "/image 62.png"}
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
              flex={step < 4 ? 1 : "none"}
              w={step < 4 ? "auto" : "100%"}
              p={{ base: 6, md: 12 }}
              position="relative"
            >
              {/* Close button */}
              <CloseButton
                position="absolute"
                top={6}
                right={6}
                size="lg"
                onClick={handleClose}
              />

              {/* Step indicator (hidden on step 4) */}
              {step < 4 && (
                <Box mb={12} mt={4}>
                  <StepIndicator currentStep={step} />
                </Box>
              )}

              {/* Step 1: Empresa */}
              {step === 1 && (
                <VStack spacing={6} maxW="795px" mx="auto">
                  <FormInput
                    label="Nome"
                    placeholder="Digite o nome da empresa"
                    value={formData.nome}
                    onChange={(v) => updateField("nome", v)}
                  />
                  <FormInput
                    label="CNPJ"
                    placeholder="Digite o CNPJ"
                    value={formData.cnpj}
                    onChange={(v) => updateField("cnpj", v)}
                  />
                  <HStack spacing={6} w="100%">
                    <FormSelect
                      label="Cidade"
                      placeholder="Selecione a cidade"
                      value={formData.cidade}
                      onChange={(v) => updateField("cidade", v)}
                      options={cidades}
                    />
                    <FormInput
                      label="Telefone"
                      placeholder="DDD | 9999-99999"
                      value={formData.telefone}
                      onChange={(v) => updateField("telefone", v)}
                    />
                  </HStack>
                  <FormSelect
                    label="Atividade"
                    placeholder="Selecione a atividade"
                    value={formData.atividade}
                    onChange={(v) => updateField("atividade", v)}
                    options={atividades}
                  />
                  
                  <HStack w="100%" pt={4}>
                    <Checkbox
                      isChecked={formData.termos}
                      onChange={(e) => updateField("termos", e.target.checked)}
                      borderColor="#000"
                    >
                      <Text fontSize="14px">
                        Concordo com nossos Termos de Serviço e Política de Privacidade *
                      </Text>
                    </Checkbox>
                  </HStack>

                  <HStack w="100%" justify="flex-start" pt={6}>
                    <Button
                      bg="#000"
                      color="white"
                      borderRadius="full"
                      px={10}
                      py={6}
                      fontSize="18px"
                      fontWeight={600}
                      onClick={handleNext}
                      _hover={{ bg: "#333" }}
                    >
                      SEGUIR
                    </Button>
                  </HStack>
                </VStack>
              )}

              {/* Step 2: Detalhes da conta */}
              {step === 2 && (
                <VStack spacing={6} maxW="795px" mx="auto">
                  <FormInput
                    label="Usuário"
                    placeholder="Digite seu usuário"
                    value={formData.usuario}
                    onChange={(v) => updateField("usuario", v)}
                  />
                  <FormInput
                    label="Senha"
                    placeholder="••••••••"
                    value={formData.senha}
                    onChange={(v) => updateField("senha", v)}
                    type="password"
                  />
                  <FormInput
                    label="Confirme a senha"
                    placeholder="••••••••"
                    value={formData.confirmarSenha}
                    onChange={(v) => updateField("confirmarSenha", v)}
                    type="password"
                  />

                  <Button
                    bg="#4285F4"
                    color="white"
                    borderRadius="full"
                    px={10}
                    py={6}
                    fontSize="18px"
                    fontWeight={600}
                    leftIcon={<Image src="/google-icon.svg" alt="Google" boxSize="24px" />}
                    onClick={handleGoogleLogin}
                    isLoading={loading}
                    _hover={{ bg: "#357ae8" }}
                  >
                    Entrar com Google
                  </Button>
                  {error && (
                    <Text color="red.500" fontSize="sm">{error}</Text>
                  )}

                  <HStack w="100%" justify="space-between" pt={6}>
                    <Button
                      bg="#000"
                      color="white"
                      borderRadius="full"
                      px={10}
                      py={6}
                      fontSize="18px"
                      fontWeight={600}
                      onClick={handleBack}
                      _hover={{ bg: "#333" }}
                    >
                      VOLTAR
                    </Button>
                    <Button
                      bg="#000"
                      color="white"
                      borderRadius="full"
                      px={10}
                      py={6}
                      fontSize="18px"
                      fontWeight={600}
                      onClick={handleNext}
                      _hover={{ bg: "#333" }}
                    >
                      SEGUIR
                    </Button>
                  </HStack>
                </VStack>
              )}

              {/* Step 3: Confirmação */}
              {step === 3 && (
                <VStack spacing={0} maxW="795px" mx="auto" align="stretch">
                  <Text
                    fontSize="48px"
                    fontWeight={500}
                    color="#000"
                    mb={2}
                    fontFamily="'Noto Looped Thai UI', sans-serif"
                  >
                    Confirmação
                  </Text>
                  <Text fontSize="20px" color="#000" mb={8}>
                    Por favor, revise suas informações
                  </Text>

                  <VStack spacing={0} align="stretch">
                    <InfoRow label="EMPRESA" value={formData.nome || "-"} />
                    <InfoRow 
                      label="LOCALIZAÇÃO" 
                      value={cidades.find(c => c.value === formData.cidade)?.label || "-"} 
                    />
                    <InfoRow label="CNPJ" value={formData.cnpj || "-"} />
                    <InfoRow label="USUÁRIO" value={formData.usuario || "-"} />
                    <InfoRow 
                      label="ATUAÇÃO" 
                      value={atividades.find(a => a.value === formData.atividade)?.label || "-"} 
                    />
                    <Box py={6} borderTop="1px solid #000" borderBottom="1px solid #000">
                      <Text fontSize="18px" fontWeight={600} color="#101828" mb={2}>
                        TELEFONE
                      </Text>
                      <Text fontSize="16px" fontWeight={500} color="#000">
                        {formData.telefone || "-"}
                      </Text>
                    </Box>
                  </VStack>

                  <HStack w="100%" justify="space-between" pt={8}>
                    <Button
                      bg="#000"
                      color="white"
                      borderRadius="full"
                      px={10}
                      py={6}
                      fontSize="18px"
                      fontWeight={600}
                      onClick={handleBack}
                      _hover={{ bg: "#333" }}
                    >
                      VOLTAR
                    </Button>
                    <Button
                      bg="#000"
                      color="white"
                      borderRadius="full"
                      px={10}
                      py={6}
                      fontSize="18px"
                      fontWeight={600}
                      onClick={handleSubmit}
                      _hover={{ bg: "#333" }}
                    >
                      CONFIRMAR
                    </Button>
                  </HStack>
                </VStack>
              )}

              {/* Step 4: Sucesso */}
              {step === 4 && (
                <VStack spacing={6} justify="center" align="center" minH="80vh">
                  <Text
                    fontSize={{ base: "48px", md: "74px" }}
                    fontWeight={500}
                    color="#000"
                    fontFamily="'Noto Looped Thai UI', sans-serif"
                  >
                    Deu tudo certo!
                  </Text>
                  <Text fontSize="20px" color="#000" textAlign="center">
                    Obrigado pelas informações. Verifique seu e-mail
                  </Text>
                  
                  {/* Success image */}
                  <Image
                    src="/image 63.png"
                    alt="Sucesso"
                    maxW="300px"
                    maxH="300px"
                    objectFit="contain"
                    my={8}
                  />

                  <Button
                    bg="#000"
                    color="white"
                    borderRadius="full"
                    px={10}
                    py={6}
                    fontSize="18px"
                    fontWeight={600}
                    onClick={handleClose}
                    _hover={{ bg: "#333" }}
                  >
                    COMEÇAR
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
