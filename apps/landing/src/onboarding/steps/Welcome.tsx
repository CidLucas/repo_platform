import React, { useEffect, useState } from "react";
import { Box, Button, HStack, Spinner, Text, VStack } from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout } from "../OnboardingLayout";
import { C } from "../tokens";
import { useOnboarding } from "../state";
import { supabase } from "../../lib/supabase";
import {
  ensureTenantRow,
  getOnboardingState,
  patchOnboardingState,
} from "../services/onboardingService";

// Step 1 – The Promise. Also serves as the OAuth callback: when Supabase
// returns from Google with ?code=..., detectSessionInUrl exchanges the code
// automatically. We wait for the session and hydrate onboarding state.
const Welcome: React.FC = () => {
  const navigate = useNavigate();
  const { update } = useOnboarding();
  const hasCode = typeof window !== "undefined" && window.location.search.includes("code=");
  const [finalizing, setFinalizing] = useState(hasCode);

  useEffect(() => {
    let cancelled = false;

    const hydrateFromSession = async () => {
      const { data } = await supabase.auth.getSession();
      const user = data.session?.user;
      if (user) {
        const meta = user.user_metadata ?? {};
        const fullName =
          (meta.full_name as string | undefined) ||
          (meta.name as string | undefined) ||
          "";
        const authMethod: "google" | "email" =
          (meta.provider as string | undefined) === "email" ? "email" : "google";
        update({
          authMethod,
          nome: fullName || "",
          email: user.email ?? "",
        });

        // Mirror these identity fields to the server so the wizard can be
        // resumed on any device. Row-missing (legacy users) -> self-heal.
        try {
          const record = await getOnboardingState();
          if (record === null) {
            await ensureTenantRow();
          }
          await patchOnboardingState({
            nome: fullName || "",
            email: user.email ?? "",
            authMethod,
          });
        } catch {
          // Non-fatal: state.ts autosave will retry on the next update().
        }
      }
      if (!cancelled) {
        // Clean ?code=... off the URL so a reload doesn't re-trigger exchange.
        if (hasCode) {
          const url = new URL(window.location.href);
          url.search = "";
          window.history.replaceState({}, "", url.toString());
        }
        setFinalizing(false);
      }
    };

    if (hasCode) {
      // Give Supabase one tick to finish detectSessionInUrl, then hydrate.
      const { data: sub } = supabase.auth.onAuthStateChange((event) => {
        if (event === "SIGNED_IN" || event === "INITIAL_SESSION") {
          hydrateFromSession();
        }
      });
      // Fallback in case the event never fires (already-had-session path).
      const timer = window.setTimeout(hydrateFromSession, 800);
      return () => {
        cancelled = true;
        sub.subscription.unsubscribe();
        window.clearTimeout(timer);
      };
    }

    // No code in URL — still opportunistically hydrate name/email.
    hydrateFromSession();
    return () => {
      cancelled = true;
    };
  }, [hasCode, update]);

  if (finalizing) {
    return (
      <OnboardingLayout progress={null}>
        <VStack spacing={5} py={{ base: 16, md: 24 }} textAlign="center">
          <Spinner size="lg" color={C.blueLight} thickness="3px" />
          <Text color={C.textDim} fontSize="15px">
            Finalizando login seguro…
          </Text>
        </VStack>
      </OnboardingLayout>
    );
  }

  return (
    <OnboardingLayout progress={null}>
      <VStack spacing={8} textAlign="center" py={{ base: 4, md: 10 }}>
        <Text
          fontSize="12px"
          fontWeight={600}
          letterSpacing="0.14em"
          textTransform="uppercase"
          color={C.blueLight}
        >
          Boas-vindas ao Blu
        </Text>
        <Box
          as="h1"
          fontFamily="'Playfair Display', serif"
          fontSize={{ base: "34px", md: "52px" }}
          fontWeight={500}
          letterSpacing="-0.02em"
          lineHeight={1.05}
          maxW="640px"
        >
          Quanto mais{" "}
          <Text
            as="span"
            fontStyle="italic"
            bgGradient={`linear(to-r, ${C.orangeLight}, ${C.pink}, ${C.purpleLight})`}
            bgClip="text"
          >
            contexto
          </Text>
          , mais sua é a plataforma.
        </Box>
        <Text color={C.textDim} fontSize={{ base: "16px", md: "19px" }} maxW="520px" lineHeight={1.55}>
          Agentes sugerem. Você decide.
        </Text>

        <HStack spacing={3} pt={4}>
          <VisualDot color={C.orange} />
          <VisualDot color={C.pink} />
          <VisualDot color={C.cyan} />
          <VisualDot color={C.blue} />
        </HStack>

        <Button
          mt={6}
          size="lg"
          h="56px"
          px={8}
          borderRadius="12px"
          bgGradient={`linear(to-r, ${C.blue}, ${C.purple}, ${C.pink})`}
          color="white"
          fontWeight={600}
          fontSize="16px"
          rightIcon={<ArrowForwardIcon />}
          _hover={{ filter: "brightness(1.12)", transform: "translateY(-1px)" }}
          transition="all .2s"
          boxShadow={`0 16px 50px ${C.purple}55`}
          onClick={() => navigate("/onboarding/dna")}
        >
          Montar meu time de agentes
        </Button>
      </VStack>
    </OnboardingLayout>
  );
};

const VisualDot: React.FC<{ color: string }> = ({ color }) => (
  <Box
    w="14px"
    h="14px"
    borderRadius="full"
    bg={color}
    boxShadow={`0 0 24px ${color}99`}
  />
);

export default Welcome;
