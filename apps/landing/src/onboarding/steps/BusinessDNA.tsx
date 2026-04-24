import React, { useState } from "react";
import {
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Select,
  Text,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import { useOnboarding, Vertical } from "../state";
import { mapBusinessDNAToCompanyProfile } from "../mappers";
import {
  patchOnboardingState,
  saveContextSections,
  updateClientColumn,
} from "../services/onboardingService";

const VERTICALS: { value: Exclude<Vertical, null>; label: string }[] = [
  { value: "ecommerce", label: "E-commerce / Varejo" },
  { value: "servicos", label: "Serviços" },
  { value: "industria", label: "Indústria" },
  { value: "saude", label: "Saúde" },
  { value: "educacao", label: "Educação" },
  { value: "financeiro", label: "Financeiro" },
  { value: "agro", label: "Agro" },
  { value: "outro", label: "Outro" },
];

// Step 2 – Business DNA. 2 required + 2 optional. ~25% progress.
const BusinessDNA: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { state, update } = useOnboarding();
  const [empresa, setEmpresa] = useState(state.empresa);
  const [vertical, setVertical] = useState<Vertical>(state.vertical);
  const [porte, setPorte] = useState(state.porte);
  const [website, setWebsite] = useState(state.website);
  const [saving, setSaving] = useState(false);

  const canContinue = empresa.trim().length > 1 && !!vertical;

  const handleNext = async () => {
    if (saving) return;
    const nextState = {
      ...state,
      empresa: empresa.trim(),
      vertical,
      porte: porte.trim(),
      website: website.trim(),
    };
    // Update local state first so re-entry shows trimmed values immediately.
    update({
      empresa: nextState.empresa,
      vertical: nextState.vertical,
      porte: nextState.porte,
      website: nextState.website,
    });

    setSaving(true);
    try {
      // Three parallel writes — all scoped to the caller's tenant via RLS.
      // `patch…` is race-free via the `merge_onboarding_state` RPC; the
      // other two are PostgREST updates scoped by external_user_id.
      await Promise.all([
        patchOnboardingState({
          empresa: nextState.empresa,
          vertical: nextState.vertical,
          porte: nextState.porte,
          website: nextState.website,
        }),
        saveContextSections({
          company_profile: {
            ...mapBusinessDNAToCompanyProfile(nextState),
            core_values: [],
          },
        }),
        nextState.empresa
          ? updateClientColumn("nome_empresa", nextState.empresa)
          : Promise.resolve(),
      ]);
      navigate("/onboarding/data");
    } catch (err) {
      toast({
        title: "Não foi possível salvar",
        description:
          err instanceof Error ? err.message : "Tente novamente em instantes.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <OnboardingLayout progress={25}>
      <StepHeader
        eyebrow="Passo 1 de 4"
        title={
          <>
            Conte o{" "}
            <Text
              as="span"
              fontStyle="italic"
              bgGradient={`linear(to-r, ${C.blueLight}, ${C.purpleLight})`}
              bgClip="text"
            >
              DNA
            </Text>{" "}
            do seu negócio.
          </>
        }
        subtitle="Isso calibra a linguagem dos seus agentes."
      />

      <VStack
        spacing={4}
        bg={C.surface}
        border="1px solid"
        borderColor={C.borderStrong}
        borderRadius="18px"
        p={{ base: 6, md: 7 }}
        align="stretch"
      >
        <FormControl isRequired>
          <FormLabel color="white" fontSize="13px" fontWeight={500} mb={1.5}>
            Nome da empresa
          </FormLabel>
          <Input
            value={empresa}
            onChange={(e) => setEmpresa(e.target.value)}
            placeholder="Ex: Acme Comércio Ltda"
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
            Ramo / Vertical
          </FormLabel>
          <Select
            value={vertical ?? ""}
            onChange={(e) => setVertical((e.target.value || null) as Vertical)}
            placeholder="Selecione um setor"
            bg="rgba(255,255,255,0.04)"
            border="1px solid"
            borderColor={C.borderStrong}
            color="white"
            _hover={{ borderColor: C.blueLight }}
            _focus={{ borderColor: C.blue }}
            sx={{ option: { background: C.surface, color: "white" } }}
          >
            {VERTICALS.map((v) => (
              <option key={v.value} value={v.value}>
                {v.label}
              </option>
            ))}
          </Select>
        </FormControl>

        <HStack spacing={4} align="start">
          <FormControl>
            <FormLabel color="white" fontSize="13px" fontWeight={500} mb={1.5}>
              Porte <Text as="span" color={C.textMuted}>(opcional)</Text>
            </FormLabel>
            <Select
              value={porte}
              onChange={(e) => setPorte(e.target.value)}
              placeholder="Selecione"
              bg="rgba(255,255,255,0.04)"
              border="1px solid"
              borderColor={C.borderStrong}
              color="white"
              _hover={{ borderColor: C.blueLight }}
              _focus={{ borderColor: C.blue }}
              sx={{ option: { background: C.surface, color: "white" } }}
            >
              <option value="solo">Autônomo / Solo</option>
              <option value="micro">Até 10 pessoas</option>
              <option value="pequena">11 a 50 pessoas</option>
              <option value="media">51 a 250 pessoas</option>
              <option value="grande">Mais de 250 pessoas</option>
            </Select>
          </FormControl>

          <FormControl>
            <FormLabel color="white" fontSize="13px" fontWeight={500} mb={1.5}>
              Website <Text as="span" color={C.textMuted}>(opcional)</Text>
            </FormLabel>
            <Input
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="acme.com.br"
              bg="rgba(255,255,255,0.04)"
              border="1px solid"
              borderColor={C.borderStrong}
              color="white"
              _hover={{ borderColor: C.blueLight }}
              _focus={{ borderColor: C.blue }}
            />
          </FormControl>
        </HStack>
      </VStack>

      <HStack justify="space-between" mt={8}>
        <Button
          variant="ghost"
          color={C.textDim}
          _hover={{ color: "white", bg: "rgba(255,255,255,0.04)" }}
          onClick={() => navigate(-1)}
        >
          Voltar
        </Button>
        <Button
          h="48px"
          px={7}
          bgGradient={`linear(to-r, ${C.blue}, ${C.purple})`}
          color="white"
          fontWeight={600}
          rightIcon={<ArrowForwardIcon />}
          _hover={{ filter: "brightness(1.1)" }}
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

export default BusinessDNA;
