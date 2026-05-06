import React, { useState } from "react";
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Badge,
  Box,
  Button,
  HStack,
  Icon,
  Progress,
  Select,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useToast,
  VStack,
} from "@chakra-ui/react";
import {
  ArrowForwardIcon,
  CheckCircleIcon,
  NotAllowedIcon,
  WarningIcon,
} from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { OnboardingLayout, StepHeader } from "../OnboardingLayout";
import { C } from "../tokens";
import { useOnboarding, type ColumnMappingDecision } from "../state";
import { patchOnboardingState } from "../services/onboardingService";

// ── Blu schema fields available as mapping targets ──────────────────────────
const BLU_FIELDS: { value: string; label: string }[] = [
  { value: "data_emissao", label: "Data de emissão" },
  { value: "nr_pedido", label: "Número do pedido" },
  { value: "valor_total", label: "Valor total" },
  { value: "nome_cliente", label: "Nome do cliente" },
  { value: "cpf_cnpj", label: "CPF/CNPJ" },
  { value: "cidade", label: "Cidade" },
  { value: "estado", label: "Estado" },
  { value: "qtd_itens", label: "Quantidade de itens" },
  { value: "desc_produto", label: "Descrição do produto" },
  { value: "cod_produto", label: "Código do produto" },
  { value: "valor_unitario", label: "Valor unitário" },
  { value: "forma_pagamento", label: "Forma de pagamento" },
  { value: "status_pedido", label: "Status do pedido" },
  { value: "data_entrega", label: "Data de entrega prevista" },
  { value: "vendedor", label: "Vendedor" },
  { value: "ref_interna", label: "Referência interna" },
  { value: "observacoes", label: "Observações" },
  { value: "margem_bruta", label: "Margem bruta" },
];

// ── Auto-mapped rows (confidence ≥ 85%) ─────────────────────────────────────
const INITIAL_AUTO: Array<{ source: string; bluField: string; bluLabel: string; confidence: number }> = [
  { source: "dt_emissao",   bluField: "data_emissao",    bluLabel: "Data de emissão",          confidence: 98 },
  { source: "nr_pedido",    bluField: "nr_pedido",        bluLabel: "Número do pedido",         confidence: 97 },
  { source: "vl_total",     bluField: "valor_total",      bluLabel: "Valor total",              confidence: 96 },
  { source: "nome_cliente", bluField: "nome_cliente",     bluLabel: "Nome do cliente",          confidence: 95 },
  { source: "cpf_cnpj",    bluField: "cpf_cnpj",         bluLabel: "CPF/CNPJ",                confidence: 94 },
  { source: "cidade",       bluField: "cidade",           bluLabel: "Cidade",                   confidence: 97 },
  { source: "uf",           bluField: "estado",           bluLabel: "Estado",                   confidence: 99 },
  { source: "qtd_itens",   bluField: "qtd_itens",        bluLabel: "Quantidade de itens",      confidence: 91 },
  { source: "desc_produto", bluField: "desc_produto",     bluLabel: "Descrição do produto",     confidence: 89 },
  { source: "cod_produto",  bluField: "cod_produto",      bluLabel: "Código do produto",        confidence: 93 },
  { source: "vl_unitario",  bluField: "valor_unitario",   bluLabel: "Valor unitário",           confidence: 92 },
  { source: "forma_pagto",  bluField: "forma_pagamento",  bluLabel: "Forma de pagamento",       confidence: 87 },
  { source: "status_pedido",bluField: "status_pedido",    bluLabel: "Status do pedido",         confidence: 88 },
  { source: "dt_entrega",   bluField: "data_entrega",     bluLabel: "Data de entrega prevista", confidence: 85 },
];

// ── Columns needing human disambiguation ────────────────────────────────────
const INITIAL_PENDING: Array<{
  source: string;
  options: { value: string; label: string }[];
}> = [
  {
    source: "cd_vendedor",
    options: [
      { value: "vendedor",     label: "Vendedor" },
      { value: "ref_interna",  label: "Representante" },
      { value: "_ignore",      label: "Ignorar este campo" },
    ],
  },
  {
    source: "ref_interna",
    options: [
      { value: "ref_interna",  label: "Referência interna" },
      { value: "cod_produto",  label: "Código do produto" },
      { value: "_ignore",      label: "Ignorar este campo" },
    ],
  },
  {
    source: "obs",
    options: [
      { value: "observacoes",  label: "Observações do pedido" },
      { value: "_ignore",      label: "Ignorar este campo" },
    ],
  },
  {
    source: "margem",
    options: [
      { value: "margem_bruta", label: "Margem bruta" },
      { value: "_ignore",      label: "Ignorar este campo" },
    ],
  },
];

// ── Unknown columns ──────────────────────────────────────────────────────────
const INITIAL_UNKNOWN: string[] = ["campo_aux1"];

// ── Helpers ──────────────────────────────────────────────────────────────────
const confidenceColor = (n: number) => (n >= 95 ? C.green : n >= 88 ? C.green : C.greenLight);

// ── Component ────────────────────────────────────────────────────────────────
const ColumnMapping: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { update } = useOnboarding();

  // Confirmed selections for "needs confirmation" rows: source → blu field value
  const [confirmations, setConfirmations] = useState<Record<string, string>>({});
  // Actions for unknown rows: source → action
  const [unknownActions, setUnknownActions] = useState<Record<string, "ignore" | "flag" | "map">>({});
  // Manual field mapping for unknown rows
  const [manualMappings, setManualMappings] = useState<Record<string, string>>({});

  const [saving, setSaving] = useState(false);

  // Derived counts
  const autoCount = INITIAL_AUTO.length;
  const confirmedCount = Object.values(confirmations).filter((v) => v && v !== "_ignore").length;
  const pendingUnconfirmed = INITIAL_PENDING.filter((r) => !confirmations[r.source]).length;
  const ignoredCount = [
    ...Object.values(confirmations).filter((v) => v === "_ignore"),
    ...Object.values(unknownActions).filter((v) => v === "ignore"),
  ].length;
  const flaggedCount = Object.values(unknownActions).filter((v) => v === "flag").length;

  const canContinue = pendingUnconfirmed === 0;

  const handleConfirm = async () => {
    if (saving) return;
    setSaving(true);

    const decisions: ColumnMappingDecision[] = [
      ...INITIAL_AUTO.map((r) => ({
        sourceColumn: r.source,
        bluField: r.bluField,
        status: "auto" as const,
        confidence: r.confidence,
      })),
      ...INITIAL_PENDING.map((r) => {
        const selected = confirmations[r.source];
        return {
          sourceColumn: r.source,
          bluField: selected === "_ignore" ? null : (selected ?? null),
          status: selected === "_ignore" ? ("ignored" as const) : ("confirmed" as const),
        };
      }),
      ...INITIAL_UNKNOWN.map((src) => {
        const action = unknownActions[src];
        return {
          sourceColumn: src,
          bluField: action === "map" ? (manualMappings[src] ?? null) : null,
          status:
            action === "flag"
              ? ("flagged" as const)
              : action === "map"
              ? ("confirmed" as const)
              : ("ignored" as const),
        };
      }),
    ];

    update({ columnMapping: decisions });

    try {
      await patchOnboardingState({ columnMapping: decisions });
      navigate("/onboarding/launch");
    } catch (err) {
      toast({
        title: "Não foi possível salvar o mapeamento",
        description: err instanceof Error ? err.message : "Tente novamente em instantes.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };

  // Shared table header
  const TableHeader = () => (
    <Thead>
      <Tr>
        <Th
          fontSize="10px"
          letterSpacing="0.1em"
          textTransform="uppercase"
          color={C.textMuted}
          borderColor={C.borderStrong}
          w="40%"
        >
          Sua coluna
        </Th>
        <Th
          fontSize="10px"
          letterSpacing="0.1em"
          textTransform="uppercase"
          color={C.textMuted}
          borderColor={C.borderStrong}
          w="40%"
        >
          Campo Blu
        </Th>
        <Th
          fontSize="10px"
          letterSpacing="0.1em"
          textTransform="uppercase"
          color={C.textMuted}
          borderColor={C.borderStrong}
          w="20%"
          textAlign="right"
        >
          Confiança
        </Th>
      </Tr>
    </Thead>
  );

  return (
    <OnboardingLayout progress={87} maxW="880px">
      <StepHeader
        eyebrow="Passo 4 de 4"
        title="Confirmar mapeamento de colunas"
        subtitle="Verificamos sua base e mapeamos automaticamente a maioria dos campos. Revise os que precisam de atenção."
      />

      {/* Summary chips */}
      <HStack spacing={3} mb={6} flexWrap="wrap">
        <HStack spacing={1.5}>
          <Box w="6px" h="6px" borderRadius="full" bg={C.green} />
          <Text fontSize="12px" color={C.textDim}>
            {autoCount} mapeados
          </Text>
        </HStack>
        {confirmedCount > 0 && (
          <HStack spacing={1.5}>
            <Box w="6px" h="6px" borderRadius="full" bg={C.blue} />
            <Text fontSize="12px" color={C.textDim}>
              {confirmedCount} confirmados
            </Text>
          </HStack>
        )}
        {pendingUnconfirmed > 0 && (
          <HStack spacing={1.5}>
            <Box w="6px" h="6px" borderRadius="full" bg={C.yellow} />
            <Text fontSize="12px" color={C.textDim}>
              {pendingUnconfirmed} pendentes
            </Text>
          </HStack>
        )}
        {ignoredCount > 0 && (
          <HStack spacing={1.5}>
            <Box w="6px" h="6px" borderRadius="full" bg={C.textMuted} />
            <Text fontSize="12px" color={C.textDim}>
              {ignoredCount} ignorados
            </Text>
          </HStack>
        )}
        {flaggedCount > 0 && (
          <HStack spacing={1.5}>
            <Box w="6px" h="6px" borderRadius="full" bg={C.red} />
            <Text fontSize="12px" color={C.textDim}>
              {flaggedCount} sinalizados
            </Text>
          </HStack>
        )}
      </HStack>

      <Accordion
        allowMultiple
        defaultIndex={[1]} // open "needs confirmation" by default
        reduceMotion
      >
        {/* ── GROUP 1: Auto-mapped ────────────────────────────────────── */}
        <AccordionItem
          border="1px solid"
          borderColor={`${C.green}40`}
          borderRadius="14px"
          mb={3}
          bg={`${C.green}08`}
          overflow="hidden"
        >
          <AccordionButton py={3.5} px={5} _hover={{ bg: `${C.green}12` }}>
            <HStack flex={1} spacing={3}>
              <Icon as={CheckCircleIcon} color={C.green} boxSize={4} />
              <Text fontSize="14px" fontWeight={600} color="white">
                Mapeados automaticamente
              </Text>
              <Badge
                fontSize="10px"
                px={2}
                py={0.5}
                borderRadius="6px"
                bg={`${C.green}22`}
                color={C.green}
              >
                {autoCount} campos
              </Badge>
            </HStack>
            <AccordionIcon color={C.textMuted} />
          </AccordionButton>
          <AccordionPanel pb={0} px={0}>
            <Box overflowX="auto">
              <Table size="sm" variant="unstyled">
                <TableHeader />
                <Tbody>
                  {INITIAL_AUTO.map((row) => (
                    <Tr
                      key={row.source}
                      _hover={{ bg: "rgba(255,255,255,0.02)" }}
                      transition="background .1s"
                    >
                      <Td
                        borderColor={C.borderStrong}
                        py={2.5}
                        px={5}
                        fontFamily="mono"
                        fontSize="12px"
                        color={C.textDim}
                      >
                        {row.source}
                      </Td>
                      <Td borderColor={C.borderStrong} py={2.5} fontSize="13px" color="white">
                        {row.bluLabel}
                      </Td>
                      <Td borderColor={C.borderStrong} py={2.5} px={5} isNumeric>
                        <HStack justify="flex-end" spacing={2}>
                          <Progress
                            value={row.confidence}
                            size="xs"
                            w="50px"
                            borderRadius="full"
                            bg="rgba(255,255,255,0.08)"
                            sx={{
                              "& > div": {
                                background: confidenceColor(row.confidence),
                              },
                            }}
                          />
                          <Text
                            fontFamily="mono"
                            fontSize="11px"
                            color={confidenceColor(row.confidence)}
                            minW="30px"
                            textAlign="right"
                          >
                            {row.confidence}%
                          </Text>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </AccordionPanel>
        </AccordionItem>

        {/* ── GROUP 2: Needs confirmation ──────────────────────────────── */}
        <AccordionItem
          border="1px solid"
          borderColor={`${C.yellow}50`}
          borderRadius="14px"
          mb={3}
          bg={`${C.yellow}08`}
          overflow="hidden"
        >
          <AccordionButton py={3.5} px={5} _hover={{ bg: `${C.yellow}12` }}>
            <HStack flex={1} spacing={3}>
              <Icon as={WarningIcon} color={C.yellow} boxSize={4} />
              <Text fontSize="14px" fontWeight={600} color="white">
                Precisam de confirmação
              </Text>
              <Badge
                fontSize="10px"
                px={2}
                py={0.5}
                borderRadius="6px"
                bg={`${C.yellow}22`}
                color={C.yellow}
              >
                {INITIAL_PENDING.length} campos
              </Badge>
              {pendingUnconfirmed > 0 && (
                <Text fontSize="11px" color={C.yellow} opacity={0.7}>
                  {pendingUnconfirmed} pendente{pendingUnconfirmed !== 1 ? "s" : ""}
                </Text>
              )}
            </HStack>
            <AccordionIcon color={C.textMuted} />
          </AccordionButton>
          <AccordionPanel pb={0} px={0}>
            <Box overflowX="auto">
              <Table size="sm" variant="unstyled">
                <Thead>
                  <Tr>
                    <Th
                      fontSize="10px"
                      letterSpacing="0.1em"
                      textTransform="uppercase"
                      color={C.textMuted}
                      borderColor={C.borderStrong}
                      w="35%"
                    >
                      Sua coluna
                    </Th>
                    <Th
                      fontSize="10px"
                      letterSpacing="0.1em"
                      textTransform="uppercase"
                      color={C.textMuted}
                      borderColor={C.borderStrong}
                    >
                      Selecionar campo Blu
                    </Th>
                    <Th
                      fontSize="10px"
                      letterSpacing="0.1em"
                      textTransform="uppercase"
                      color={C.textMuted}
                      borderColor={C.borderStrong}
                      w="100px"
                      textAlign="center"
                    >
                      Status
                    </Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {INITIAL_PENDING.map((row) => {
                    const selected = confirmations[row.source];
                    const isDone = !!selected;
                    const isIgnored = selected === "_ignore";
                    return (
                      <Tr
                        key={row.source}
                        _hover={{ bg: "rgba(255,255,255,0.02)" }}
                        transition="background .1s"
                      >
                        <Td
                          borderColor={C.borderStrong}
                          py={2.5}
                          px={5}
                          fontFamily="mono"
                          fontSize="12px"
                          color={C.textDim}
                        >
                          {row.source}
                        </Td>
                        <Td borderColor={C.borderStrong} py={2} pr={5}>
                          <Select
                            size="sm"
                            placeholder="Selecionar →"
                            value={confirmations[row.source] ?? ""}
                            onChange={(e) =>
                              setConfirmations((prev) => ({
                                ...prev,
                                [row.source]: e.target.value,
                              }))
                            }
                            bg="rgba(255,255,255,0.04)"
                            borderColor={
                              isDone
                                ? isIgnored
                                  ? C.textMuted
                                  : C.blue
                                : C.borderStrong
                            }
                            color="white"
                            fontSize="12px"
                            _hover={{ borderColor: C.yellow }}
                            sx={{
                              "& option": {
                                background: "#151734",
                                color: "white",
                              },
                            }}
                          >
                            {row.options.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </Select>
                        </Td>
                        <Td borderColor={C.borderStrong} py={2.5} textAlign="center">
                          {!isDone ? (
                            <Badge
                              fontSize="9px"
                              px={2}
                              py={0.5}
                              borderRadius="6px"
                              bg={`${C.yellow}22`}
                              color={C.yellow}
                            >
                              Pendente
                            </Badge>
                          ) : isIgnored ? (
                            <Badge
                              fontSize="9px"
                              px={2}
                              py={0.5}
                              borderRadius="6px"
                              bg="rgba(255,255,255,0.08)"
                              color={C.textMuted}
                            >
                              Ignorado
                            </Badge>
                          ) : (
                            <Badge
                              fontSize="9px"
                              px={2}
                              py={0.5}
                              borderRadius="6px"
                              bg={`${C.blue}22`}
                              color={C.blue}
                            >
                              Confirmado
                            </Badge>
                          )}
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
            </Box>
          </AccordionPanel>
        </AccordionItem>

        {/* ── GROUP 3: Unknown ─────────────────────────────────────────── */}
        <AccordionItem
          border="1px solid"
          borderColor="rgba(239,68,68,0.35)"
          borderRadius="14px"
          mb={3}
          bg="rgba(239,68,68,0.06)"
          overflow="hidden"
        >
          <AccordionButton py={3.5} px={5} _hover={{ bg: "rgba(239,68,68,0.1)" }}>
            <HStack flex={1} spacing={3}>
              <Icon as={NotAllowedIcon} color={C.red} boxSize={4} />
              <Text fontSize="14px" fontWeight={600} color="white">
                Não reconhecidos
              </Text>
              <Badge
                fontSize="10px"
                px={2}
                py={0.5}
                borderRadius="6px"
                bg="rgba(239,68,68,0.18)"
                color={C.red}
              >
                {INITIAL_UNKNOWN.length} campo{INITIAL_UNKNOWN.length !== 1 ? "s" : ""}
              </Badge>
            </HStack>
            <AccordionIcon color={C.textMuted} />
          </AccordionButton>
          <AccordionPanel pb={4} px={5}>
            <VStack align="stretch" spacing={3}>
              {INITIAL_UNKNOWN.map((src) => {
                const action = unknownActions[src];
                return (
                  <Box
                    key={src}
                    p={4}
                    borderRadius="10px"
                    bg="rgba(255,255,255,0.03)"
                    border="1px solid"
                    borderColor={C.borderStrong}
                  >
                    <HStack justify="space-between" align="flex-start" flexWrap="wrap" gap={3}>
                      <VStack align="start" spacing={0.5}>
                        <Text
                          fontFamily="mono"
                          fontSize="13px"
                          color={C.textDim}
                        >
                          {src}
                        </Text>
                        <Text fontSize="11px" color={C.textMuted}>
                          Blu não identificou este campo automaticamente
                        </Text>
                      </VStack>
                      <HStack spacing={2} flexWrap="wrap">
                        <Button
                          size="xs"
                          h="28px"
                          px={3}
                          variant="outline"
                          borderColor={action === "map" ? C.blue : C.borderStrong}
                          bg={action === "map" ? `${C.blue}18` : "transparent"}
                          color={action === "map" ? C.blue : C.textDim}
                          _hover={{ borderColor: C.blue, color: C.blue }}
                          onClick={() =>
                            setUnknownActions((prev) => ({
                              ...prev,
                              [src]: "map",
                            }))
                          }
                        >
                          Mapear
                        </Button>
                        <Button
                          size="xs"
                          h="28px"
                          px={3}
                          variant="outline"
                          borderColor={action === "ignore" ? C.textMuted : C.borderStrong}
                          bg={action === "ignore" ? "rgba(255,255,255,0.06)" : "transparent"}
                          color={action === "ignore" ? "white" : C.textMuted}
                          _hover={{ borderColor: C.textMuted, color: "white" }}
                          onClick={() =>
                            setUnknownActions((prev) => ({
                              ...prev,
                              [src]: "ignore",
                            }))
                          }
                        >
                          Ignorar
                        </Button>
                        <Button
                          size="xs"
                          h="28px"
                          px={3}
                          variant="outline"
                          borderColor={action === "flag" ? C.red : C.borderStrong}
                          bg={action === "flag" ? "rgba(239,68,68,0.12)" : "transparent"}
                          color={action === "flag" ? C.red : C.textMuted}
                          _hover={{ borderColor: C.red, color: C.red }}
                          onClick={() =>
                            setUnknownActions((prev) => ({
                              ...prev,
                              [src]: "flag",
                            }))
                          }
                        >
                          Sinalizar erro
                        </Button>
                      </HStack>
                    </HStack>
                    {/* Manual mapping select */}
                    {action === "map" && (
                      <Box mt={3}>
                        <Select
                          size="sm"
                          placeholder="Selecionar campo Blu →"
                          value={manualMappings[src] ?? ""}
                          onChange={(e) =>
                            setManualMappings((prev) => ({
                              ...prev,
                              [src]: e.target.value,
                            }))
                          }
                          bg="rgba(255,255,255,0.04)"
                          borderColor={C.borderStrong}
                          color="white"
                          fontSize="12px"
                          _hover={{ borderColor: C.blue }}
                          sx={{
                            "& option": {
                              background: "#151734",
                              color: "white",
                            },
                          }}
                        >
                          {BLU_FIELDS.map((f) => (
                            <option key={f.value} value={f.value}>
                              {f.label}
                            </option>
                          ))}
                        </Select>
                      </Box>
                    )}
                  </Box>
                );
              })}
            </VStack>
          </AccordionPanel>
        </AccordionItem>
      </Accordion>

      {/* Navigation */}
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
          onClick={handleConfirm}
          title={!canContinue ? "Confirme todos os campos pendentes antes de continuar" : undefined}
        >
          Confirmar mapeamento
        </Button>
      </HStack>

      {!canContinue && (
        <Text fontSize="12px" color={C.yellow} textAlign="right" mt={2}>
          {pendingUnconfirmed} campo{pendingUnconfirmed !== 1 ? "s" : ""} ainda{" "}
          {pendingUnconfirmed !== 1 ? "precisam" : "precisa"} de confirmação
        </Text>
      )}
    </OnboardingLayout>
  );
};

export default ColumnMapping;
