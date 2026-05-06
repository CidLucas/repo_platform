import React, { useState } from "react";
import {
  Box,
  Button,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "../OnboardingLayout";
import { C } from "../tokens";
import { useOnboarding } from "../state";
import { supabase } from "../../lib/supabase";

// Step 1 — Auth. Google-only to reduce friction.
const Auth: React.FC = () => {
  const navigate = useNavigate();
  const { update } = useOnboarding();
  const [loadingGoogle, setLoadingGoogle] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preserve ?persona= through the OAuth round-trip so InfoForm can pre-select the vertical.
  const personaParam = new URLSearchParams(window.location.search).get("persona");
  const infoTarget = personaParam
    ? `${window.location.origin}/onboarding/info?persona=${personaParam}`
    : `${window.location.origin}/onboarding/info`;

  const handleGoogle = async () => {
    setLoadingGoogle(true);
    setError(null);
    update({ authMethod: "google" });
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: infoTarget,
      },
    });
    if (oauthError) {
      setLoadingGoogle(false);
      setError("Não foi possível abrir o Google. Tente novamente.");
    }
    // On success the browser is redirected to Google and back to /onboarding/data.
  };

  return (
    <OnboardingLayout progress={33}>
      <Box textAlign="center" mb={10}>
        <Text
          fontSize="12px"
          fontWeight={600}
          letterSpacing="0.14em"
          textTransform="uppercase"
          color={C.blueLight}
          mb={4}
        >
          Passo 1 de 3 · Criar conta
        </Text>
        <Box
          as="h1"
          fontFamily="'Playfair Display', serif"
          fontSize={{ base: "32px", md: "42px" }}
          fontWeight={500}
          letterSpacing="-0.02em"
          lineHeight={1.08}
          mb={4}
        >
          Seu Centro de Comando{" "}
          <Text
            as="span"
            fontStyle="italic"
            bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight}, ${C.pink})`}
            bgClip="text"
          >
            está a um clique.
          </Text>
        </Box>
        <Text color={C.textDim} fontSize={{ base: "15px", md: "16px" }} maxW="400px" mx="auto">
          Sem cartão de crédito. Seus dados ficam no seu ambiente. Cancela quando quiser.
        </Text>
      </Box>

      <VStack
        spacing={4}
        bg={C.surface}
        border="1px solid"
        borderColor={C.borderStrong}
        borderRadius="18px"
        p={{ base: 6, md: 8 }}
        align="stretch"
        maxW="420px"
        mx="auto"
      >
        <Button
          onClick={handleGoogle}
          h="54px"
          bg="white"
          color="#111"
          fontWeight={600}
          fontSize="15px"
          borderRadius="12px"
          _hover={{ bg: "rgba(255,255,255,0.92)", transform: "translateY(-1px)" }}
          transition="all .18s"
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

        {error && (
          <Text fontSize="13px" color={C.pink} textAlign="center">
            {error}
          </Text>
        )}

        <Text color={C.textMuted} fontSize="12px" textAlign="center">
          Ao continuar você aceita nossos{" "}
          <Text as="span" color={C.blueLight} cursor="pointer" _hover={{ textDecoration: "underline" }}>
            Termos
          </Text>{" "}
          e{" "}
          <Text as="span" color={C.blueLight} cursor="pointer" _hover={{ textDecoration: "underline" }}>
            Política de Privacidade
          </Text>
          .
        </Text>
      </VStack>

      <Text
        fontSize="12px"
        color={C.textMuted}
        textAlign="center"
        mt={5}
        cursor="pointer"
        _hover={{ color: C.textDim }}
        onClick={() => navigate("/")}
      >
        ← Voltar para o início
      </Text>
    </OnboardingLayout>
  );
};

const GoogleIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
    <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.6-6 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 8 3l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z" />
    <path fill="#FF3D00" d="M6.3 14.1l6.6 4.8C14.7 15.1 19 12 24 12c3 0 5.8 1.1 8 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.1z" />
    <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.3C29.3 35 26.8 36 24 36c-5.3 0-9.7-3.4-11.3-8L6 32.7C9.4 39.6 16.1 44 24 44z" />
    <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.2 5.7l6.2 5.3C41 36.2 44 30.9 44 24c0-1.2-.1-2.3-.4-3.5z" />
  </svg>
);

export default Auth;

