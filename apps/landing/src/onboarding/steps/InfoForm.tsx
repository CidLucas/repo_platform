import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  HStack,
  Input,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import { type Vertical, personaToVertical, useOnboarding } from "../state";
import { supabase } from "../../lib/supabase";
import { patchOnboardingState } from "../services/onboardingService";

const VERTICALS: { label: string; value: Exclude<Vertical, null> }[] = [
  { label: "E-commerce / Varejo", value: "ecommerce" },
  { label: "Serviços / Consultoria", value: "servicos" },
  { label: "Indústria / Distribuição", value: "industria" },
  { label: "Saúde", value: "saude" },
  { label: "Educação", value: "educacao" },
  { label: "Financeiro", value: "financeiro" },
  { label: "Agro", value: "agro" },
  { label: "Outro", value: "outro" },
];

const TEAM_SIZES: { label: string; sub: string; value: "solo" | "pequeno" | "estruturado" }[] = [
  { label: "Só eu", sub: "solopreneur", value: "solo" },
  { label: "2 a 10", sub: "pequena equipe", value: "pequeno" },
  { label: "10 a 50", sub: "equipe estruturada", value: "estruturado" },
];

// Step 2 – Info Form. 66% progress.
const InfoForm: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();
  const [nome, setNome] = useState(state.nome);
  const [empresa, setEmpresa] = useState(state.empresa);
  const [website, setWebsite] = useState(state.website);
  const [vertical, setVertical] = useState<Vertical>(state.vertical);
  const [teamSize, setTeamSize] = useState(state.teamSize);
  const [saving, setSaving] = useState(false);

  // Pre-fill name/email from Google session; vertical from ?persona= query param.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const personaParam = params.get("persona") as Parameters<typeof personaToVertical>[0];
    if (personaParam && !state.vertical) {
      const v = personaToVertical(personaParam);
      if (v) {
        setVertical(v);
        update({ vertical: v });
      }
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) return;
      const meta = session.user.user_metadata ?? {};
      if (!state.nome && !nome) {
        const fullName = (meta.full_name as string) || (meta.name as string) || "";
        if (fullName) {
          setNome(fullName);
          update({ nome: fullName });
        }
      }
      if (!state.email && session.user.email) {
        update({ email: session.user.email });
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const canContinue = empresa.trim().length > 0 && vertical !== null;

  const handleNext = async () => {
    if (saving || !canContinue) return;
    const patch = { nome, empresa, website, vertical, teamSize };
    update(patch);
    setSaving(true);
    try {
      await patchOnboardingState(patch);
      navigate("/onboarding/data");
    } catch (err) {
      toast({
        title: "Não foi possível salvar",
        description: err instanceof Error ? err.message : "Tente novamente em instantes.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <OnboardingLayout progress={66}>
      <StepHeader
        eyebrow="Passo 2 de 3 · Sobre sua empresa"
        title="Conta um pouco sobre o negócio."
        subtitle="Com isso já montamos o contexto inicial para seus agentes."
      />

      <VStack spacing={5} align="stretch">
        {/* Nome */}
        <Box>
          <Text fontSize="13px" fontWeight={500} color={C.textDim} mb={2}>
            Seu nome
          </Text>
          <Input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Como você prefere ser chamado"
            bg={C.surface}
            border="1px solid"
            borderColor={C.borderStrong}
            borderRadius="10px"
            color="white"
            fontSize="14px"
            h="46px"
            _placeholder={{ color: C.textMuted }}
            _focus={{ borderColor: C.blue, boxShadow: `0 0 0 2px ${C.blue}22` }}
          />
        </Box>

        {/* Empresa */}
        <Box>
          <Text fontSize="13px" fontWeight={500} color={C.textDim} mb={2}>
            Nome da empresa{" "}
            <Text as="span" color={C.pink}>
              *
            </Text>
          </Text>
          <Input
            value={empresa}
            onChange={(e) => setEmpresa(e.target.value)}
            placeholder="Ex: Distribuidora Norte, Clínica Saúde+"
            bg={C.surface}
            border="1px solid"
            borderColor={C.borderStrong}
            borderRadius="10px"
            color="white"
            fontSize="14px"
            h="46px"
            _placeholder={{ color: C.textMuted }}
            _focus={{ borderColor: C.blue, boxShadow: `0 0 0 2px ${C.blue}22` }}
          />
        </Box>

        {/* Site / Instagram — prominent because we scrape it */}
        <Box>
          <Text fontSize="13px" fontWeight={500} color={C.textDim} mb={1}>
            Site ou Instagram
          </Text>
          <Text fontSize="11px" color={C.textMuted} mb={2}>
            Usamos para entender seu produto, público e tom de voz.
          </Text>
          <Input
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="meusite.com.br  ou  @minha_loja"
            bg={C.surface}
            border="1px solid"
            borderColor={`${C.blue}55`}
            borderRadius="10px"
            color="white"
            fontSize="14px"
            h="46px"
            _placeholder={{ color: C.textMuted }}
            _focus={{ borderColor: C.blue, boxShadow: `0 0 0 2px ${C.blue}22` }}
          />
        </Box>

        {/* Setor */}
        <Box>
          <Text fontSize="13px" fontWeight={500} color={C.textDim} mb={3}>
            Setor{" "}
            <Text as="span" color={C.pink}>
              *
            </Text>
          </Text>
          <HStack spacing={2} flexWrap="wrap">
            {VERTICALS.map((v) => (
              <Button
                key={v.value}
                size="sm"
                h="34px"
                px={4}
                borderRadius="999px"
                fontWeight={500}
                fontSize="13px"
                variant="outline"
                borderColor={vertical === v.value ? `${C.blue}99` : C.borderStrong}
                bg={vertical === v.value ? `${C.blue}22` : "transparent"}
                color="white"
                _hover={{ borderColor: C.blue, bg: `${C.blue}1a` }}
                onClick={() => setVertical(v.value)}
              >
                {v.label}
              </Button>
            ))}
          </HStack>
        </Box>

        {/* Tamanho do time */}
        <Box>
          <Text fontSize="13px" fontWeight={500} color={C.textDim} mb={3}>
            Tamanho do time
          </Text>
          <HStack spacing={3}>
            {TEAM_SIZES.map((t) => (
              <Box
                key={t.value}
                as="button"
                flex={1}
                textAlign="center"
                bg={teamSize === t.value ? `${C.purple}18` : C.surface}
                border="1px solid"
                borderColor={teamSize === t.value ? `${C.purple}77` : C.borderStrong}
                borderRadius="12px"
                py={3}
                px={2}
                transition="all .15s"
                _hover={{ borderColor: teamSize === t.value ? C.purple : C.textDim }}
                onClick={() => setTeamSize(t.value)}
              >
                <Text fontSize="15px" fontWeight={700} color="white">
                  {t.label}
                </Text>
                <Text fontSize="11px" color={C.textMuted} mt={0.5}>
                  {t.sub}
                </Text>
              </Box>
            ))}
          </HStack>
        </Box>
      </VStack>

      <HStack justify="flex-end" mt={8}>
        <Button
          h="48px"
          px={7}
          borderRadius="12px"
          bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
          color="white"
          fontWeight={600}
          fontSize="14px"
          rightIcon={<ArrowForwardIcon />}
          _hover={{ filter: "brightness(1.1)", transform: "translateY(-1px)" }}
          transition="all .18s"
          isDisabled={!canContinue}
          isLoading={saving}
          loadingText="Salvando…"
          onClick={handleNext}
        >
          Continuar
        </Button>
      </HStack>
    </OnboardingLayout>
  );
};

export default InfoForm;
