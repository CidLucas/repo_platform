import { useEffect, useState } from "react";
import { Box, HStack, Link, Text } from "@chakra-ui/react";
import { FiArrowRight, FiZap } from "react-icons/fi";
import { supabase } from "../lib/supabase";

/**
 * OnboardingBanner — one-line "continue onboarding" gate shown when
 * clientes_vizu.onboarding_completed_at IS NULL for the current tenant.
 *
 * Source of truth: Phase 1/4 of the Landing Onboarding Wire-up
 * (supabase/migrations/20260423130100_onboarding_state_column.sql).
 *
 * Links to the landing origin's /onboarding/dna step — not a dashboard
 * route — to avoid a redirect loop with PrivateRoute.
 */
export function OnboardingBanner() {
  const [incomplete, setIncomplete] = useState<boolean>(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session || cancelled) return;

      // RLS scopes this to the caller's clientes_vizu row.
      const { data, error } = await supabase
        .from("clientes_vizu")
        .select("onboarding_completed_at, client_id")
        .maybeSingle();
      if (cancelled || error || !data) return;
      if (!data.client_id) return;
      setIncomplete(data.onboarding_completed_at === null);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!incomplete) return null;

  const env =
    (import.meta as unknown as { env?: Record<string, string | undefined> })
      .env ?? {};
  const landingUrl = env.VITE_LANDING_URL || "/";
  const href = `${landingUrl.replace(/\/$/, "")}/onboarding/dna`;

  return (
    <Box
      mx={6}
      mt={4}
      px={4}
      py={3}
      borderRadius="10px"
      bg="linear-gradient(90deg, rgba(59,130,246,0.12), rgba(168,85,247,0.12))"
      border="1px solid"
      borderColor="rgba(168,85,247,0.35)"
    >
      <HStack justify="space-between" flexWrap="wrap" spacing={3}>
        <HStack spacing={2}>
          <Box as={FiZap} color="#a855f7" />
          <Text fontSize="14px" color="white">
            Seu onboarding ainda não foi concluído. Ative seus agentes para
            liberar os insights.
          </Text>
        </HStack>
        <Link
          href={href}
          color="#a855f7"
          fontSize="14px"
          fontWeight={600}
          _hover={{ color: "#c084fc", textDecoration: "none" }}
        >
          <HStack spacing={1}>
            <Text>Continuar onboarding</Text>
            <Box as={FiArrowRight} />
          </HStack>
        </Link>
      </HStack>
    </Box>
  );
}

export default OnboardingBanner;
