import {
  Badge,
  Box,
  Flex,
  HStack,
  Progress,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
} from '@chakra-ui/react';
import { useEffect, useState } from 'react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import {
  type ActivationFunnelResponse,
  type D1EngagementRow,
  getActivationFunnel,
  getD1EngagementMetrics,
} from '../../services/adminService';

const STEP_COLORS = {
  website: '#3b82f6',
  package: '#a855f7',
  connector: '#10b981',
  approval: '#f59e0b',
} as const;

const D1_EVENT_LABELS: Record<string, string> = {
  'mc.insight.click': 'Insight Card CTR',
  'chat.rail.message_sent': 'Chat Rail Message Sent',
  'tenant.sample_data.disabled': 'Demo → Live (switch)',
  'dashboard.insight.ctr': 'Insight CTR',
  'dashboard.chat_rail.opened': 'Chat Rail Aberto',
  'dashboard.demo_live.switch': 'Demo → Live (clique)',
};

const D1_EVENT_COLORS: Record<string, string> = {
  'mc.insight.click': '#a855f7',
  'chat.rail.message_sent': '#3b82f6',
  'tenant.sample_data.disabled': '#10b981',
  'dashboard.insight.ctr': '#a855f7',
  'dashboard.chat_rail.opened': '#3b82f6',
  'dashboard.demo_live.switch': '#10b981',
};

function AdminActivationFunnelPage() {
  const [data, setData] = useState<ActivationFunnelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [d1Data, setD1Data] = useState<D1EngagementRow[]>([]);
  const [d1Loading, setD1Loading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await getActivationFunnel(120);
        if (mounted) setData(response);
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Falha ao carregar funil de ativação');
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    void load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadD1 = async () => {
      setD1Loading(true);
      try {
        const rows = await getD1EngagementMetrics();
        if (mounted) setD1Data(rows);
      } catch {
        // non-fatal: D1 panel stays empty
      } finally {
        if (mounted) setD1Loading(false);
      }
    };
    void loadD1();
    return () => { mounted = false; };
  }, []);

  return (
    <AdminLayout>
      <Box p={8} maxW="1200px" mx="auto">
        <VStack align="stretch" spacing={6}>
          <Box>
            <Text
              fontSize="2rem"
              fontWeight="normal"
              fontFamily="'Playfair Display', serif"
              color="white"
              mb={2}
            >
              Funil de Ativação
            </Text>
            <Text color="whiteAlpha.600">
              Dashboard interno (Phase D): signup {'->'} website {'->'} pacote {'->'} conector {'->'} primeira aprovação D7.
            </Text>
          </Box>

          {loading && (
            <Flex align="center" justify="center" py={12}>
              <Spinner size="xl" color="blue.400" />
            </Flex>
          )}

          {error && (
            <Box bg="#1a1b2e" border="1px solid" borderColor="red.500" borderRadius="lg" p={4}>
              <Text color="red.300">{error}</Text>
            </Box>
          )}

          {!loading && !error && data && (
            <>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 5 }} spacing={4}>
                <StatCard label="Tenants" value={String(data.summary.total_tenants)} color="#64748b" />
                <StatCard
                  label="Website Fornecido"
                  value={`${data.summary.website_provided} (${data.summary.conversion_website}%)`}
                  color={STEP_COLORS.website}
                />
                <StatCard
                  label="Pacote Aceito"
                  value={`${data.summary.package_accepted} (${data.summary.conversion_package}%)`}
                  color={STEP_COLORS.package}
                />
                <StatCard
                  label="1º Conector Sincronizado"
                  value={`${data.summary.first_connector_synced} (${data.summary.conversion_connector}%)`}
                  color={STEP_COLORS.connector}
                />
                <StatCard
                  label="1ª Aprovação em D7"
                  value={`${data.summary.first_approval_acted_d7} (${data.summary.conversion_first_approval_d7}%)`}
                  color={STEP_COLORS.approval}
                />
              </SimpleGrid>

              <Box bg="#1a1b2e" borderRadius="lg" border="1px solid" borderColor="whiteAlpha.200" p={5}>
                <Text color="white" fontWeight="semibold" mb={4}>Conversão por etapa</Text>
                <VStack align="stretch" spacing={4}>
                  <StepProgress label="Website" value={data.summary.conversion_website} color={STEP_COLORS.website} />
                  <StepProgress label="Pacote" value={data.summary.conversion_package} color={STEP_COLORS.package} />
                  <StepProgress label="Conector" value={data.summary.conversion_connector} color={STEP_COLORS.connector} />
                  <StepProgress label="Aprovação D7" value={data.summary.conversion_first_approval_d7} color={STEP_COLORS.approval} />
                </VStack>
              </Box>

              <Box bg="#1a1b2e" borderRadius="lg" border="1px solid" borderColor="whiteAlpha.200" overflowX="auto">
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th color="whiteAlpha.700">Empresa</Th>
                      <Th color="whiteAlpha.700">Dias</Th>
                      <Th color="whiteAlpha.700">Website</Th>
                      <Th color="whiteAlpha.700">Pacote</Th>
                      <Th color="whiteAlpha.700">Conector</Th>
                      <Th color="whiteAlpha.700">1ª Aprovação</Th>
                      <Th color="whiteAlpha.700">Pendentes</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {data.tenants.map((tenant) => (
                      <Tr key={tenant.client_id}>
                        <Td color="white">{tenant.nome_empresa}</Td>
                        <Td color="whiteAlpha.700">{tenant.days_since_signup}</Td>
                        <Td>{tenant.website_provided ? <Badge colorScheme="green">Sim</Badge> : <Badge colorScheme="gray">Não</Badge>}</Td>
                        <Td>{tenant.package_accepted ? <Badge colorScheme="green">Sim</Badge> : <Badge colorScheme="gray">Não</Badge>}</Td>
                        <Td>{tenant.first_connector_synced ? <Badge colorScheme="green">Sim</Badge> : <Badge colorScheme="gray">Não</Badge>}</Td>
                        <Td>{tenant.first_approval_acted ? <Badge colorScheme="green">Sim</Badge> : <Badge colorScheme="gray">Não</Badge>}</Td>
                        <Td>
                          <Badge colorScheme={tenant.pending_approvals > 0 ? 'orange' : 'green'}>
                            {tenant.pending_approvals}
                          </Badge>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>

              {/* D1 Engagement Indicators */}
              <Box>
                <Text color="white" fontWeight="semibold" fontSize="lg" mb={4}>
                  Indicadores D1 — Engajamento no produto
                </Text>
                <Text color="whiteAlpha.600" fontSize="sm" mb={4}>
                  Eventos de interação coletados diretamente do dashboard (insight CTR, chat rail, demo→live).
                </Text>
                {d1Loading ? (
                  <Flex align="center" justify="center" py={6}>
                    <Spinner size="md" color="blue.400" />
                  </Flex>
                ) : d1Data.length === 0 ? (
                  <Box bg="#1a1b2e" borderRadius="lg" border="1px solid" borderColor="whiteAlpha.200" p={4}>
                    <Text color="whiteAlpha.500" fontSize="sm">Nenhum evento registrado ainda.</Text>
                  </Box>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                    {d1Data.map((row) => {
                      const label = D1_EVENT_LABELS[row.event_name] ?? row.event_name;
                      const color = D1_EVENT_COLORS[row.event_name] ?? '#64748b';
                      return (
                        <Box key={row.event_name} bg="#1a1b2e" borderRadius="lg" border="1px solid" borderColor="whiteAlpha.200" p={4}>
                          <Text color="whiteAlpha.700" fontSize="xs" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider" mb={2}>
                            {label}
                          </Text>
                          <Stat>
                            <StatNumber color={color} fontSize="1.5rem">{row.total_events}</StatNumber>
                            <StatLabel color="whiteAlpha.600" fontSize="xs">eventos totais</StatLabel>
                          </Stat>
                          <VStack align="stretch" spacing={1} mt={3}>
                            <HStack justify="space-between">
                              <Text color="whiteAlpha.500" fontSize="xs">Últimas 24h</Text>
                              <Text color="white" fontSize="xs" fontWeight="semibold">{row.events_last_24h}</Text>
                            </HStack>
                            <HStack justify="space-between">
                              <Text color="whiteAlpha.500" fontSize="xs">Últimos 7 dias</Text>
                              <Text color="white" fontSize="xs" fontWeight="semibold">{row.events_last_7d}</Text>
                            </HStack>
                            <HStack justify="space-between">
                              <Text color="whiteAlpha.500" fontSize="xs">Tenants únicos</Text>
                              <Text color="white" fontSize="xs" fontWeight="semibold">{row.unique_tenants}</Text>
                            </HStack>
                          </VStack>
                        </Box>
                      );
                    })}
                  </SimpleGrid>
                )}
              </Box>
            </>
          )}
        </VStack>
      </Box>
    </AdminLayout>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <Box bg="#1a1b2e" borderRadius="lg" border="1px solid" borderColor="whiteAlpha.200" p={4}>
      <Stat>
        <StatLabel color="whiteAlpha.700">{label}</StatLabel>
        <StatNumber color={color} fontSize="1.25rem">{value}</StatNumber>
      </Stat>
    </Box>
  );
}

function StepProgress({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <Box>
      <HStack justify="space-between" mb={1}>
        <Text color="whiteAlpha.800" fontSize="sm">{label}</Text>
        <Text color="whiteAlpha.600" fontSize="sm">{value.toFixed(2)}%</Text>
      </HStack>
      <Progress value={value} borderRadius="full" colorScheme="blue" sx={{ '& > div': { background: color } }} />
    </Box>
  );
}

export default AdminActivationFunnelPage;
