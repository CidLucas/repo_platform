import {
  Box,
  Flex,
  HStack,
  Text,
  Spinner,
  Alert,
  AlertIcon,
  Button,
  Badge,
  IconButton,
  useToast,
  Select,
  Divider,
  Stack,
  Switch,
} from '@chakra-ui/react';
import { RepeatIcon, DownloadIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { MainLayout } from '../components/layouts/MainLayout';
import { PeriodSelector } from '../components/PeriodSelector';
import {
  listReportTemplates,
  listReportRuns,
  listReportSchedules,
  generateReport,
  upsertReportSchedule,
  disableReportSchedule,
  downloadReportRun,
  type ReportTemplate,
  type ReportRun,
  type ReportSchedule,
  type ReportFormat,
  type ReportCadence,
  type StandardPeriod,
} from '../services/analyticsService';

const FORMAT_OPTIONS: { value: ReportFormat; label: string }[] = [
  { value: 'pdf', label: 'PDF' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'xlsx', label: 'Excel (XLSX)' },
  { value: 'gdoc', label: 'Google Docs' },
  { value: 'gsheet', label: 'Google Sheets' },
];

const CADENCE_OPTIONS: { value: ReportCadence; label: string }[] = [
  { value: 'daily', label: 'Diária' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'monthly', label: 'Mensal' },
];

const STATUS_COLORS: Record<string, string> = {
  pending: 'gray',
  running: 'yellow',
  success: 'green',
  failed: 'red',
};

const isStandardPeriod = (value: string): value is StandardPeriod =>
  ['7d', '30d', '90d', 'mtd', 'ytd', 'custom'].includes(value);

const toStandardPeriod = (value: string): StandardPeriod =>
  (isStandardPeriod(value) ? value : '30d');

const formatDate = (iso: string | null): string => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
};

function ReportsPage() {
  const toast = useToast();
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [runs, setRuns] = useState<ReportRun[]>([]);
  const [schedules, setSchedules] = useState<ReportSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [period, setPeriod] = useState<StandardPeriod>('30d');
  const [format, setFormat] = useState<ReportFormat>('pdf');
  const [cadence, setCadence] = useState<ReportCadence>('monthly');
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [generating, setGenerating] = useState(false);

  const activeTemplate = useMemo(
    () => templates.find((t) => t.id === activeTemplateId) ?? null,
    [templates, activeTemplateId],
  );

  const refreshAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [tpls, rs, sch] = await Promise.all([
        listReportTemplates(),
        listReportRuns(50),
        listReportSchedules().catch(() => [] as ReportSchedule[]),
      ]);
      setTemplates(tpls);
      setRuns(rs);
      setSchedules(sch);
      if (!activeTemplateId && tpls.length > 0) {
        setActiveTemplateId(tpls[0].id);
        setPeriod(toStandardPeriod(tpls[0].default_period));
        setFormat(tpls[0].default_format);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao carregar relatórios');
    } finally {
      setLoading(false);
    }
  }, [activeTemplateId]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  // Reset format/period defaults when switching templates.
  useEffect(() => {
    if (!activeTemplate) return;
    setPeriod(toStandardPeriod(activeTemplate.default_period));
    setFormat(activeTemplate.default_format);
    const existing = schedules.find((s) => s.template_id === activeTemplate.id);
    setCadence((existing?.cadence ?? 'monthly') as ReportCadence);
    setScheduleEnabled(existing?.enabled ?? false);
  }, [activeTemplate, schedules]);

  const handleGenerate = async () => {
    if (!activeTemplate) return;
    try {
      setGenerating(true);
      const result = await generateReport(activeTemplate.id, { period, format });
      toast({
        status: result.status === 'success' ? 'success' : 'info',
        title:
          result.status === 'success'
            ? 'Relatório gerado'
            : `Relatório: ${result.status}`,
      });
      await refreshAll();
    } catch (e) {
      toast({
        status: 'error',
        title: 'Falha ao gerar relatório',
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveSchedule = async () => {
    if (!activeTemplate) return;
    try {
      if (!scheduleEnabled) {
        const existing = schedules.find(
          (s) => s.template_id === activeTemplate.id && s.cadence === cadence,
        );
        if (existing) await disableReportSchedule(existing.id);
        toast({ status: 'info', title: 'Agendamento desativado' });
      } else {
        await upsertReportSchedule({
          template_id: activeTemplate.id,
          period,
          format,
          cadence,
          enabled: true,
        });
        toast({ status: 'success', title: 'Agendamento salvo' });
      }
      await refreshAll();
    } catch (e) {
      toast({
        status: 'error',
        title: 'Falha ao salvar agendamento',
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const handleDownload = async (run: ReportRun) => {
    try {
      await downloadReportRun(run);
    } catch (e) {
      toast({
        status: 'error',
        title: 'Falha ao baixar relatório',
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  return (
    <MainLayout>
      <Flex direction="column" h="calc(100vh - 80px)" p={4} gap={3}>
        <HStack>
          <Text fontSize="2xl" fontWeight="bold">
            Relatórios
          </Text>
          <IconButton
            aria-label="Atualizar"
            icon={<RepeatIcon />}
            size="sm"
            onClick={refreshAll}
            isLoading={loading}
          />
        </HStack>

        {error && (
          <Alert status="error">
            <AlertIcon />
            {error}
          </Alert>
        )}

        <Flex flex={1} gap={3} minH={0}>
          {/* Template catalog */}
          <Box
            w="280px"
            borderWidth="1px"
            borderRadius="md"
            overflowY="auto"
            bg="white"
          >
            <Box p={3} borderBottomWidth="1px">
              <Text fontWeight="semibold">Templates</Text>
            </Box>
            {loading && (
              <Flex justify="center" p={6}>
                <Spinner />
              </Flex>
            )}
            {!loading && templates.length === 0 && (
              <Text p={4} color="gray.500" fontSize="sm">
                Nenhum template disponível.
              </Text>
            )}
            {templates.map((t) => {
              const isActive = t.id === activeTemplateId;
              return (
                <Box
                  key={t.id}
                  p={3}
                  cursor="pointer"
                  bg={isActive ? 'blue.50' : 'transparent'}
                  borderBottomWidth="1px"
                  onClick={() => setActiveTemplateId(t.id)}
                  _hover={{ bg: isActive ? 'blue.50' : 'gray.50' }}
                >
                  <Text fontWeight="semibold" noOfLines={1}>
                    {t.title}
                  </Text>
                  <Text fontSize="xs" color="gray.500" noOfLines={2}>
                    {t.description}
                  </Text>
                  <HStack mt={1} spacing={2}>
                    <Badge colorScheme="purple" fontSize="0.65em">
                      {t.domain}
                    </Badge>
                    <Badge colorScheme="gray" fontSize="0.65em">
                      {t.tier_required}
                    </Badge>
                  </HStack>
                </Box>
              );
            })}
          </Box>

          {/* Generate + schedule controls */}
          <Flex
            flex={1}
            direction="column"
            borderWidth="1px"
            borderRadius="md"
            bg="white"
            minH={0}
            overflowY="auto"
          >
            {!activeTemplate ? (
              <Flex flex={1} justify="center" align="center">
                <Text color="gray.500">Selecione um template</Text>
              </Flex>
            ) : (
              <Box p={4}>
                <Text fontSize="lg" fontWeight="bold">
                  {activeTemplate.title}
                </Text>
                <Text color="gray.600" fontSize="sm" mb={4}>
                  {activeTemplate.description}
                </Text>

                <Stack direction={{ base: 'column', md: 'row' }} spacing={3}>
                  <Box flex={1}>
                    <Text fontSize="sm" mb={1}>
                      Período
                    </Text>
                    <PeriodSelector
                      value={period}
                      onChange={setPeriod}
                      size="sm"
                      width="100%"
                      excludeOptions={['custom']}
                    />
                  </Box>
                  <Box flex={1}>
                    <Text fontSize="sm" mb={1}>
                      Formato
                    </Text>
                    <Select
                      value={format}
                      onChange={(e) => setFormat(e.target.value as ReportFormat)}
                      size="sm"
                    >
                      {FORMAT_OPTIONS.map((f) => (
                        <option key={f.value} value={f.value}>
                          {f.label}
                        </option>
                      ))}
                    </Select>
                  </Box>
                </Stack>

                <Button
                  mt={4}
                  colorScheme="blue"
                  onClick={handleGenerate}
                  isLoading={generating}
                >
                  Gerar agora
                </Button>

                <Divider my={6} />

                <Text fontWeight="semibold" mb={2}>
                  Agendamento (PRO)
                </Text>
                <HStack spacing={3} align="end">
                  <Box flex={1}>
                    <Text fontSize="sm" mb={1}>
                      Cadência
                    </Text>
                    <Select
                      value={cadence}
                      onChange={(e) => setCadence(e.target.value as ReportCadence)}
                      size="sm"
                    >
                      {CADENCE_OPTIONS.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </Select>
                  </Box>
                  <HStack>
                    <Text fontSize="sm">Ativo</Text>
                    <Switch
                      isChecked={scheduleEnabled}
                      onChange={(e) => setScheduleEnabled(e.target.checked)}
                    />
                  </HStack>
                  <Button size="sm" onClick={handleSaveSchedule}>
                    Salvar
                  </Button>
                </HStack>
              </Box>
            )}
          </Flex>

          {/* Recent runs */}
          <Box
            w="380px"
            borderWidth="1px"
            borderRadius="md"
            overflowY="auto"
            bg="white"
          >
            <Box p={3} borderBottomWidth="1px">
              <Text fontWeight="semibold">Execuções recentes</Text>
            </Box>
            {runs.length === 0 && (
              <Text p={4} color="gray.500" fontSize="sm">
                Nenhum relatório gerado ainda.
              </Text>
            )}
            {runs.map((run) => {
              const tpl = templates.find((t) => t.id === run.template_id);
              return (
                <Box key={run.id} p={3} borderBottomWidth="1px">
                  <HStack justify="space-between">
                    <Text fontWeight="semibold" noOfLines={1}>
                      {tpl?.title ?? run.template_id}
                    </Text>
                    <Badge colorScheme={STATUS_COLORS[run.status] ?? 'gray'}>
                      {run.status}
                    </Badge>
                  </HStack>
                  <Text fontSize="xs" color="gray.500">
                    {run.format.toUpperCase()} · {run.period} · {formatDate(run.created_at)}
                  </Text>
                  {run.error_message && (
                    <Text fontSize="xs" color="red.600" mt={1} noOfLines={2}>
                      {run.error_message}
                    </Text>
                  )}
                  {run.status === 'success' && (
                    <HStack mt={2} spacing={2}>
                      <Button
                        size="xs"
                        leftIcon={<DownloadIcon />}
                        onClick={() => handleDownload(run)}
                      >
                        Baixar
                      </Button>
                      {run.output_url && (
                        <Button
                          size="xs"
                          leftIcon={<ExternalLinkIcon />}
                          variant="outline"
                          as="a"
                          href={run.output_url}
                          target="_blank"
                        >
                          Abrir
                        </Button>
                      )}
                    </HStack>
                  )}
                </Box>
              );
            })}
          </Box>
        </Flex>
      </Flex>
    </MainLayout>
  );
}

export default ReportsPage;
