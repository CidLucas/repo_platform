import React, { useState } from "react";
import {
  Box,
  Button,
  Divider,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Text,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "../OnboardingLayout";
import { C } from "../tokens";
import { useOnboarding } from "../state";
import { supabase } from "../../lib/supabase";

type Mode = "signin" | "signup";

// Step 0 – Auth Gate. No progress bar. Zero friction.
const Auth: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();
  const [mode, setMode] = useState<Mode>("signup");
  const [nome, setNome] = useState(state.nome);
  const [email, setEmail] = useState(state.email);
  const [password, setPassword] = useState("");
  const [loadingGoogle, setLoadingGoogle] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);

  const handleGoogle = async () => {
    setLoadingGoogle(true);
    update({ authMethod: "google" });
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/onboarding/website`,
      },
    });
    if (error) {
      setLoadingGoogle(false);
      toast({
        title: "Não foi possível iniciar o Google",
        description: error.message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
    // On success the browser is redirected to Google and back to /onboarding/website.
  };

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loadingEmail) return;
    setLoadingEmail(true);

    const cleanEmail = email.trim();
    const cleanNome = nome.trim();
    update({ authMethod: "email", nome: cleanNome, email: cleanEmail });

    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
          options: {
            data: { full_name: cleanNome },
            emailRedirectTo: `${window.location.origin}/onboarding/website`,
          },
        });
        if (error) throw error;

        // When email confirmation is required, session will be null. Tell the user
        // to check their inbox but still let them continue the onboarding locally.
        if (!data.session) {
          toast({
            title: "Confirme seu e-mail",
            description: `Enviamos um link para ${cleanEmail}. Você pode continuar por aqui.`,
            status: "info",
            duration: 6000,
            isClosable: true,
          });
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password,
        });
        if (error) throw error;
      }
      navigate("/onboarding/website");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Tente novamente.";
      toast({
        title: mode === "signup" ? "Não foi possível criar a conta" : "Não foi possível entrar",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoadingEmail(false);
    }
  };

  return (
    <OnboardingLayout progress={null}>
      <Box textAlign="center" mb={10}>
        <Box
          as="h1"
          fontFamily="'Playfair Display', serif"
          fontSize={{ base: "34px", md: "44px" }}
          fontWeight={500}
          letterSpacing="-0.02em"
          lineHeight={1.05}
          mb={4}
        >
          Entrar no{" "}
          <Text
            as="span"
            fontStyle="italic"
            bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight}, ${C.pink})`}
            bgClip="text"
          >
            Blu
          </Text>
        </Box>
        <Text color={C.textDim} fontSize={{ base: "15px", md: "17px" }}>
          Seu centro de comando está a um clique.
        </Text>
      </Box>

      <VStack
        spacing={5}
        bg={C.surface}
        border="1px solid"
        borderColor={C.borderStrong}
        borderRadius="18px"
        p={{ base: 6, md: 8 }}
        align="stretch"
      >
        <Button
          onClick={handleGoogle}
          h="52px"
          bg="white"
          color="#111"
          fontWeight={600}
          _hover={{ bg: "rgba(255,255,255,0.92)" }}
          isLoading={loadingGoogle}
          loadingText="Abrindo Google…"
          leftIcon={
            <Box as="span" fontSize="18px" lineHeight={1}>
              <GoogleIcon />
            </Box>
          }
        >
          Continuar com Google
        </Button>

        <HStack spacing={3}>
          <Divider borderColor={C.borderStrong} />
          <Text color={C.textMuted} fontSize="12px" whiteSpace="nowrap">
            ou com e-mail
          </Text>
          <Divider borderColor={C.borderStrong} />
        </HStack>

        <form onSubmit={handleEmail}>
          <VStack spacing={3.5}>
            {mode === "signup" && (
              <FormControl isRequired>
                <FormLabel color="white" fontSize="13px" fontWeight={500} mb={1.5}>
                  Nome
                </FormLabel>
                <Input
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  bg="rgba(255,255,255,0.04)"
                  border="1px solid"
                  borderColor={C.borderStrong}
                  color="white"
                  _hover={{ borderColor: C.blueLight }}
                  _focus={{ borderColor: C.blue }}
                />
              </FormControl>
            )}
            <FormControl isRequired>
              <FormLabel color="white" fontSize="13px" fontWeight={500} mb={1.5}>
                E-mail
              </FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                bg="rgba(255,255,255,0.04)"
                border="1px solid"
                borderColor={C.borderStrong}
                color="white"
                _hover={{ borderColor: C.blueLight }}
                _focus={{ borderColor: C.blue }}
              />
            </FormControl>
            <FormControl isRequired>
              <FormLabel color="white" fontSize="13px" fontWeight={500} mb={1.5}>
                Senha
              </FormLabel>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
                minLength={6}
                bg="rgba(255,255,255,0.04)"
                border="1px solid"
                borderColor={C.borderStrong}
                color="white"
                _hover={{ borderColor: C.blueLight }}
                _focus={{ borderColor: C.blue }}
              />
            </FormControl>
            <Button
              type="submit"
              w="full"
              h="48px"
              mt={1}
              bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
              color="white"
              fontWeight={600}
              _hover={{ filter: "brightness(1.1)" }}
              isLoading={loadingEmail}
            >
              {mode === "signup" ? "Criar conta" : "Entrar"}
            </Button>
          </VStack>
        </form>

        <Text color={C.textMuted} fontSize="12px" textAlign="center">
          {mode === "signup" ? (
            <>
              Já tem uma conta?{" "}
              <Text
                as="button"
                type="button"
                color={C.blueLight}
                onClick={() => setMode("signin")}
                _hover={{ textDecoration: "underline" }}
              >
                Entrar
              </Text>
            </>
          ) : (
            <>
              Ainda não tem conta?{" "}
              <Text
                as="button"
                type="button"
                color={C.blueLight}
                onClick={() => setMode("signup")}
                _hover={{ textDecoration: "underline" }}
              >
                Criar agora
              </Text>
            </>
          )}
        </Text>

        <Text color={C.textMuted} fontSize="12px" textAlign="center">
          Ao continuar você aceita nossos Termos e Política de Privacidade.
        </Text>
      </VStack>
    </OnboardingLayout>
  );
};

const GoogleIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
    <path
      fill="#FFC107"
      d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.6-6 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 8 3l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z"
    />
    <path
      fill="#FF3D00"
      d="M6.3 14.1l6.6 4.8C14.7 15.1 19 12 24 12c3 0 5.8 1.1 8 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.1z"
    />
    <path
      fill="#4CAF50"
      d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.3C29.3 35 26.8 36 24 36c-5.3 0-9.7-3.4-11.3-8L6 32.7C9.4 39.6 16.1 44 24 44z"
    />
    <path
      fill="#1976D2"
      d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.2 5.7l6.2 5.3C41 36.2 44 30.9 44 24c0-1.2-.1-2.3-.4-3.5z"
    />
  </svg>
);

export default Auth;
