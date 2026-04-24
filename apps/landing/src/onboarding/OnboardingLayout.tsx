import React from "react";
import { Box, Container, Flex, HStack, Text, Progress } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import { C } from "./tokens";

interface OnboardingLayoutProps {
  progress?: number | null; // 0-100 or null to hide
  children: React.ReactNode;
}

// Shared shell: dark bg, gradient glows, brand mark, optional progress bar.
export const OnboardingLayout: React.FC<OnboardingLayoutProps> = ({ progress, children }) => {
  return (
    <Box bg={C.bg} color="white" minH="100vh" position="relative" overflow="hidden">
      {/* Ambient gradient glows */}
      <Box
        position="fixed"
        top="-20%"
        left="-10%"
        w="60%"
        h="60%"
        bgGradient={`radial(closest-side, ${C.blue}33, transparent 70%)`}
        pointerEvents="none"
        zIndex={0}
      />
      <Box
        position="fixed"
        bottom="-30%"
        right="-10%"
        w="70%"
        h="70%"
        bgGradient={`radial(closest-side, ${C.purple}33, transparent 70%)`}
        pointerEvents="none"
        zIndex={0}
      />
      <Box
        position="fixed"
        top="30%"
        right="-20%"
        w="50%"
        h="50%"
        bgGradient={`radial(closest-side, ${C.pink}22, transparent 70%)`}
        pointerEvents="none"
        zIndex={0}
      />

      {/* Dotted grid */}
      <Box
        position="fixed"
        inset={0}
        pointerEvents="none"
        zIndex={0}
        opacity={0.3}
        bgImage={`radial-gradient(${C.borderStrong} 1px, transparent 1px)`}
        bgSize="22px 22px"
      />

      {/* Top bar */}
      <Box position="relative" zIndex={2} borderBottom="1px solid" borderColor={C.border}>
        <Container maxW="1160px" px={{ base: 5, md: 8 }} py={4}>
          <Flex align="center" justify="space-between">
            <RouterLink to="/">
              <HStack spacing={2.5}>
                <Box
                  w="32px"
                  h="32px"
                  borderRadius="9px"
                  bgGradient={`linear(135deg, ${C.blue}, ${C.purple})`}
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                  fontSize="15px"
                  fontWeight={700}
                >
                  B
                </Box>
                <Text fontWeight={600} fontSize="15px" letterSpacing="-0.01em">
                  Blu
                </Text>
              </HStack>
            </RouterLink>
            <Text fontSize="12px" color={C.textMuted} letterSpacing="0.08em" textTransform="uppercase">
              Onboarding
            </Text>
          </Flex>
        </Container>
        {progress != null && (
          <Progress
            value={progress}
            size="xs"
            bg="transparent"
            sx={{
              "& > div": {
                background: `linear-gradient(90deg, ${C.blue}, ${C.purple}, ${C.pink})`,
              },
            }}
          />
        )}
      </Box>

      {/* Body */}
      <Box position="relative" zIndex={1}>
        <Container maxW="720px" px={{ base: 5, md: 8 }} py={{ base: 10, md: 16 }}>
          {children}
        </Container>
      </Box>
    </Box>
  );
};

// Shared step header used by every inner step.
export const StepHeader: React.FC<{ eyebrow?: string; title: React.ReactNode; subtitle?: React.ReactNode }> = ({
  eyebrow,
  title,
  subtitle,
}) => (
  <Box mb={8}>
    {eyebrow && (
      <Text
        fontSize="12px"
        fontWeight={600}
        letterSpacing="0.14em"
        textTransform="uppercase"
        color={C.blueLight}
        mb={3}
      >
        {eyebrow}
      </Text>
    )}
    <Box
      as="h1"
      fontFamily="'Playfair Display', serif"
      fontSize={{ base: "32px", md: "40px" }}
      fontWeight={500}
      letterSpacing="-0.02em"
      lineHeight={1.1}
      color="white"
      mb={subtitle ? 4 : 0}
    >
      {title}
    </Box>
    {subtitle && (
      <Text color={C.textDim} fontSize={{ base: "15px", md: "17px" }} lineHeight={1.55} maxW="560px">
        {subtitle}
      </Text>
    )}
  </Box>
);
