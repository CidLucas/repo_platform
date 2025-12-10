import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  Input,
  Button,
  Image,
  Divider,
  Link,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { useAuth } from "../hooks/useAuth";

// Ícones SVG para login social
const GoogleIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
);

const MicrosoftIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M11.4 11.4H2V2h9.4v9.4z" fill="#F25022"/>
    <path d="M22 11.4h-9.4V2H22v9.4z" fill="#7FBA00"/>
    <path d="M11.4 22H2v-9.4h9.4V22z" fill="#00A4EF"/>
    <path d="M22 22h-9.4v-9.4H22V22z" fill="#FFB900"/>
  </svg>
);

const AppleIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" fill="#000"/>
  </svg>
);

// Componente de Input estilizado
const FormInput: React.FC<{
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}> = ({ label, placeholder, value, onChange, type = "text" }) => (
  <VStack align="stretch" spacing={2} w="100%">
    <Text fontSize="15px" fontWeight={600} color="#000">
      {label}
    </Text>
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

// Botão de login social
const SocialButton: React.FC<{
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}> = ({ icon, label, onClick }) => (
  <Button
    w="100%"
    h="54px"
    bg="white"
    border="1px solid #000"
    borderRadius="full"
    onClick={onClick}
    _hover={{ bg: "#f5f5f5" }}
  >
    <HStack spacing={3}>
      {icon}
      <Text fontSize="14px" fontWeight={500} color="#000">
        {label}
      </Text>
    </HStack>
  </Button>
);

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signInWithEmail, signInWithGoogle, signInWithMicrosoft, signInWithApple, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redireciona se já estiver logado
  useEffect(() => {
    if (user) {
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/dashboard";
      navigate(from, { replace: true });
    }
  }, [user, navigate, location]);

  const handleLogin = async () => {
    setError(null);
    setIsLoading(true);
    
    const { error } = await signInWithEmail(email, password);
    
    setIsLoading(false);
    if (error) {
      setError(error.message);
    }
    // O redirecionamento é feito pelo useEffect quando o user muda
  };

  const handleSocialLogin = async (provider: string) => {
    setError(null);
    let result;
    
    switch (provider) {
      case "google":
        result = await signInWithGoogle();
        break;
      case "microsoft":
        result = await signInWithMicrosoft();
        break;
      case "apple":
        result = await signInWithApple();
        break;
      default:
        return;
    }
    
    if (result?.error) {
      setError(result.error.message);
    }
  };

  return (
    <Box w="100%" minH="100vh" bg="white">
      <Flex minH="100vh">
        {/* Left side - Image */}
        <Box
          flex="0 0 50%"
          maxW="720px"
          display={{ base: "none", lg: "block" }}
          position="relative"
          overflow="hidden"
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

        {/* Right side - Login Form */}
        <Flex
          flex={1}
          direction="column"
          justify="center"
          align="center"
          p={{ base: 6, md: 12 }}
        >
          <VStack spacing={8} w="100%" maxW="440px">
            {/* Logo */}
            <HStack spacing={2} mb={4}>
              <Image src="/Group 2049761270.png" alt="VIZU" h="40px" />
            </HStack>

            {/* Título */}
            <VStack spacing={2} textAlign="center">
              <Text
                fontSize={{ base: "32px", md: "40px" }}
                fontWeight={500}
                color="#000"
                fontFamily="'Noto Looped Thai UI', sans-serif"
              >
                Bem-vindo de volta
              </Text>
              <Text fontSize="16px" color="#666">
                Entre na sua conta para continuar
              </Text>
            </VStack>

            {/* Botões de login social */}
            <VStack spacing={3} w="100%">
              <SocialButton
                icon={<GoogleIcon />}
                label="Continuar com Google"
                onClick={() => handleSocialLogin("google")}
              />
              <SocialButton
                icon={<MicrosoftIcon />}
                label="Continuar com Microsoft"
                onClick={() => handleSocialLogin("microsoft")}
              />
              <SocialButton
                icon={<AppleIcon />}
                label="Continuar com Apple"
                onClick={() => handleSocialLogin("apple")}
              />
            </VStack>

            {/* Divider */}
            <HStack w="100%" spacing={4}>
              <Divider borderColor="#d1d5dc" />
              <Text fontSize="14px" color="#666" whiteSpace="nowrap">
                ou continue com e-mail
              </Text>
              <Divider borderColor="#d1d5dc" />
            </HStack>

            {/* Mensagem de erro */}
            {error && (
              <Alert status="error" borderRadius="md">
                <AlertIcon />
                {error}
              </Alert>
            )}

            {/* Form */}
            <VStack spacing={4} w="100%">
              <FormInput
                label="E-mail"
                placeholder="Digite seu e-mail"
                value={email}
                onChange={setEmail}
                type="email"
              />
              <FormInput
                label="Senha"
                placeholder="••••••••"
                value={password}
                onChange={setPassword}
                type="password"
              />

              {/* Esqueci a senha */}
              <Flex w="100%" justify="flex-end">
                <Link
                  fontSize="14px"
                  color="#000"
                  fontWeight={500}
                  _hover={{ textDecoration: "underline" }}
                >
                  Esqueci minha senha
                </Link>
              </Flex>

              {/* Botão de login */}
              <Button
                w="100%"
                h="54px"
                bg="#000"
                color="white"
                borderRadius="full"
                fontSize="18px"
                fontWeight={600}
                onClick={handleLogin}
                isLoading={isLoading}
                _hover={{ bg: "#333" }}
              >
                ENTRAR
              </Button>
            </VStack>

            {/* Link para cadastro */}
            <HStack spacing={1}>
              <Text fontSize="14px" color="#666">
                Não tem uma conta?
              </Text>
              <Link
                fontSize="14px"
                color="#000"
                fontWeight={600}
                onClick={() => navigate("/")}
                _hover={{ textDecoration: "underline" }}
              >
                Cadastre-se
              </Link>
            </HStack>
          </VStack>
        </Flex>
      </Flex>
    </Box>
  );
};

export default LoginPage;
