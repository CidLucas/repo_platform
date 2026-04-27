import { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Input,
  Button,
  FormControl,
  FormLabel,
  FormHelperText,
  Icon,
  Flex,
  Alert,
  AlertIcon,
  useToast,
  Textarea,
  Select,
  Divider,
  type InputProps,
  type TextareaProps,
  type SelectProps,
} from '@chakra-ui/react';
import { FiCheck } from 'react-icons/fi';
import * as connectorService from '../../services/connectorService';
import { AuthContext } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import type { SchemaMatchResult } from '../../hooks/useColumnMatching';

interface ConnectorConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  category: string;
  status: string;
}

interface ConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  connector: ConnectorConfig;
  /** When set (e.g. coming from /onboarding/data), the modal returns the user
   * to this URL after Conectar e Sincronizar instead of going to the column
   * mapping page. If a mapping review is required, the URL is appended with
   * `?mapping_review=<credentialId>` so the caller can show a warning. */
  returnTo?: string | null;
}

type FormData = Record<string, string>;

// Shared dark-theme styling for inputs inside the modal so we match the rest
// of the dashboard (#1a1b2e surfaces, blue accents, white text).
const DARK_INPUT_PROPS: Partial<InputProps> = {
  bg: '#0f1128',
  border: '1px solid',
  borderColor: 'rgba(255,255,255,0.08)',
  color: 'white',
  borderRadius: 'md',
  _placeholder: { color: 'whiteAlpha.400' },
  _hover: { borderColor: 'rgba(255,255,255,0.15)' },
  _focus: { borderColor: '#3b82f6', boxShadow: '0 0 0 1px #3b82f6' },
};

const DARK_TEXTAREA_PROPS: Partial<TextareaProps> = {
  bg: '#0f1128',
  border: '1px solid',
  borderColor: 'rgba(255,255,255,0.08)',
  color: 'white',
  borderRadius: 'md',
  _placeholder: { color: 'whiteAlpha.400' },
  _hover: { borderColor: 'rgba(255,255,255,0.15)' },
  _focus: { borderColor: '#3b82f6', boxShadow: '0 0 0 1px #3b82f6' },
};

const DARK_SELECT_PROPS: Partial<SelectProps> = {
  bg: '#0f1128',
  border: '1px solid',
  borderColor: 'rgba(255,255,255,0.08)',
  color: 'white',
  borderRadius: 'md',
  _hover: { borderColor: 'rgba(255,255,255,0.15)' },
  _focus: { borderColor: '#3b82f6', boxShadow: '0 0 0 1px #3b82f6' },
};

// Required canonical fields. If all of these are mapped (and no ambiguous
// matches need user review), we sync without bouncing the user through the
// mapping page.
const REQUIRED_CANONICAL = ['pedido_id', 'data_transacao', 'valor_total'];

const ConnectorModal = ({ isOpen, onClose, connector, returnTo }: ConnectorModalProps) => {
  const [formData, setFormData] = useState<FormData>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const toast = useToast();
  const auth = useContext(AuthContext);
  const navigate = useNavigate();

  // Get real client_id from auth context (from /me endpoint, not Supabase user ID)
  const clienteVizuId = auth?.clientId || '';

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    if (!clienteVizuId) {
      toast({
        title: 'Erro de autenticação',
        description: 'Não foi possível identificar o cliente. Por favor, faça login novamente.',
        status: 'error',
        duration: 5000,
      });
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      const credentials = prepareCredentials();
      let payload;

      if (connector.id === 'bigquery') {
        payload = {
          client_id: clienteVizuId,
          nome_servico: formData.nome_servico || `${connector.name} - Teste`,
          tipo_servico: 'BIGQUERY',
          ...credentials,
        };
      } else {
        payload = credentials;
      }

      const response = await connectorService.testConnection(
        connector.id as connectorService.ConnectorPlatform,
        payload
      );
      // ...restante do código...
      if (response.success) {
        setTestResult('success');
        toast({
          title: 'Conexão testada com sucesso!',
          description: response.message,
          status: 'success',
          duration: 3000,
        });
      } else {
        setTestResult('error');
        toast({
          title: 'Falha no teste de conexão',
          description: response.message,
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error) {
      setTestResult('error');
      toast({
        title: 'Falha no teste de conexão',
        description: error instanceof Error ? error.message : 'Verifique suas credenciais e tente novamente.',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsTesting(false);
    }
  };

  // Prepara as credenciais no formato esperado pela API
  const prepareCredentials = (): connectorService.CredentialPayload => {
    switch (connector.id) {
      case 'shopify':
        return {
          shop_name: formData.shop_name || '',
          access_token: formData.access_token || '',
          api_version: formData.api_version || '2024-01',
        };
      case 'vtex':
        return {
          account_name: formData.account_name || '',
          app_key: formData.app_key || '',
          app_token: formData.app_token || '',
          environment: formData.environment || 'vtexcommercestable',
        };
      case 'loja_integrada':
        return {
          api_key: formData.api_key || '',
          application_key: formData.application_key,
        };
      case 'bigquery': {
        const serviceAccountJson = formData.service_account_json
          ? JSON.parse(formData.service_account_json)
          : {};

        // Extract project_id from service account JSON automatically
        const projectId = serviceAccountJson.project_id || '';

        return {
          project_id: projectId,
          dataset_id: formData.dataset_id,
          table_name: formData.table_name || '',
          location: formData.location || 'southamerica-east1',
          service_account_json: serviceAccountJson,
        };
      }
      case 'postgresql':
      case 'mysql':
        return {
          host: formData.host || '',
          port: parseInt(formData.port || '5432'),
          database: formData.database || '',
          user: formData.user || '',
          password: formData.password || '',
        };
      case 'whatsapp':
        // WhatsApp uses a shared Twilio account at the platform level — we only
        // store the per-client sender number + an optional contact label so the
        // agent knows which number to use as `from`.
        return {
          whatsapp_number: formData.whatsapp_number || '',
          contact_label: formData.contact_label || '',
        } as unknown as connectorService.CredentialPayload;
      default:
        return {} as connectorService.CredentialPayload;
    }
  };

  /** Run column discovery + the match-columns edge function and decide whether
   * we have enough mapping coverage to sync straight away. Returns null when
   * we can't run the analysis (caller falls back to the mapping page). */
  const analyseSchema = async (
    credentialId: number,
  ): Promise<{ canAutoSync: boolean; matchResult: SchemaMatchResult | null }> => {
    // 1. Trigger column discovery (BigQuery-only RPC today; other connectors
    //    surface columns via async sync jobs, so we defer them to the mapping page).
    if (connector.id !== 'bigquery') {
      return { canAutoSync: false, matchResult: null };
    }

    const { data: discoveryResult, error: discoveryError } = await supabase.rpc(
      'trigger_column_discovery',
      { p_credential_id: credentialId },
    );
    if (discoveryError || !discoveryResult?.success) {
      return { canAutoSync: false, matchResult: null };
    }

    // 2. Pull discovered source columns.
    const { data: dataSource } = await supabase
      .from('client_data_sources')
      .select('source_columns, column_mapping, unmapped_columns, needs_review_columns, match_confidence, detected_entity_context')
      .eq('credential_id', credentialId)
      .maybeSingle();

    if (!dataSource?.source_columns) {
      return { canAutoSync: false, matchResult: null };
    }

    const columns = Array.isArray(dataSource.source_columns)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ? dataSource.source_columns.map((col: any) => (typeof col === 'object' ? col.name : col))
      : Object.keys(dataSource.source_columns as Record<string, unknown>);

    // 3. Call the match-columns edge function.
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'http://localhost:54321';
    const matchResp = await fetch(`${supabaseUrl}/functions/v1/match-columns`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ source_columns: columns, schema_type: 'invoices' }),
    });
    if (!matchResp.ok) {
      return { canAutoSync: false, matchResult: null };
    }
    const matchResult = (await matchResp.json()) as SchemaMatchResult;

    // 4. Persist the auto-mapping back so the mapping page stays in sync.
    await supabase
      .from('client_data_sources')
      .update({
        column_mapping: matchResult.matched,
        auto_column_mapping: matchResult.matched,
        unmapped_columns: matchResult.unmatched,
        needs_review_columns: matchResult.needs_review,
        match_confidence: matchResult.confidence_scores,
        detected_entity_context: matchResult.detected_context || 'neutral',
      })
      .eq('credential_id', credentialId);

    // 5. Mapping is "complete" when all required canonical fields are mapped
    //    and there are no ambiguous matches awaiting user review.
    const matchedCanonicals = new Set(Object.values(matchResult.matched || {}));
    const allRequired = REQUIRED_CANONICAL.every((c) => matchedCanonicals.has(c));
    const noAmbiguity = (matchResult.needs_review?.length ?? 0) === 0;

    return { canAutoSync: allRequired && noAmbiguity, matchResult };
  };

  const startBackgroundSync = async (credentialId: number, clientId: string) => {
    // Fire-and-forget — onboarding doesn't need to block on the sync run.
    try {
      await supabase.functions.invoke('run-sync', {
        body: {
          client_id: clientId,
          credential_id: credentialId,
          force_full_sync: true,
        },
      });
    } catch (err) {
      console.warn('run-sync invocation failed:', err);
    }
  };

  /** Bounce the user back to the URL passed via `?return=` (typically the
   * onboarding page), optionally appending hints so the caller can render a
   * warning + link to the mapping page. */
  const goBackToReturnTo = (params?: Record<string, string>) => {
    if (!returnTo) return false;
    const url = new URL(returnTo, window.location.origin);
    if (params) {
      for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
    }
    window.location.href = url.toString();
    return true;
  };

  const handleSubmit = async () => {
    if (!clienteVizuId) {
      toast({
        title: 'Erro de autenticação',
        description: 'Não foi possível identificar o cliente. Por favor, faça login novamente.',
        status: 'error',
        duration: 5000,
      });
      return;
    }

    setIsLoading(true);

    try {
      const credentials = prepareCredentials();
      const tipoServico = connector.id.toUpperCase().replace('-', '_');

      // 1. Persist the credential.
      const response = await connectorService.createCredential({
        client_id: clienteVizuId,
        nome_servico: formData.nome_servico || `${connector.name} - Produção`,
        tipo_servico: tipoServico,
        credentials,
      });

      const credentialId = parseInt(response.id);

      // Non-data-source integrations (WhatsApp, Slack, etc.) skip the column
      // discovery / mapping flow entirely — they're configured the moment the
      // credential is saved.
      if (connector.id === 'whatsapp') {
        toast({
          title: 'WhatsApp configurado!',
          description: 'O número foi vinculado ao seu cliente.',
          status: 'success',
          duration: 4000,
        });
        onClose();
        return;
      }

      // 2. Discover + match columns (BigQuery only today).
      toast({
        title: 'Analisando esquema...',
        description: 'Estamos descobrindo as colunas e mapeando para o nosso modelo.',
        status: 'info',
        duration: null,
        isClosable: false,
        id: 'connector-analysis-toast',
      });

      const { canAutoSync } = await analyseSchema(credentialId);
      toast.close('connector-analysis-toast');

      // 3. Decide where to send the user.
      if (canAutoSync) {
        // Mapping is complete — kick off sync and bounce back to onboarding.
        await startBackgroundSync(credentialId, clienteVizuId);
        toast({
          title: 'Conector configurado!',
          description: 'A sincronização começou em segundo plano.',
          status: 'success',
          duration: 4000,
        });
        onClose();
        if (!goBackToReturnTo({ connector_synced: connector.id })) {
          navigate(`/dashboard/admin/connectors/${response.id}/mapping`);
        }
        return;
      }

      // Mapping requires review (or discovery wasn't possible).
      onClose();
      if (returnTo) {
        toast({
          title: 'Quase lá!',
          description: 'Precisamos confirmar alguns mapeamentos antes de sincronizar.',
          status: 'warning',
          duration: 5000,
        });
        goBackToReturnTo({
          mapping_review: String(credentialId),
          connector: connector.id,
        });
        return;
      }
      navigate(`/dashboard/admin/connectors/${response.id}/mapping`);
    } catch (error) {
      toast.close('connector-analysis-toast');
      toast({
        title: 'Erro ao configurar conector',
        description: error instanceof Error ? error.message : 'Tente novamente mais tarde.',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Renderiza campos específicos por tipo de conector
  const renderFormFields = () => {
    switch (connector.id) {
      case 'whatsapp':
        return (
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Número WhatsApp</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="+5511999999999"
                value={formData.whatsapp_number || ''}
                onChange={(e) => handleInputChange('whatsapp_number', e.target.value)}
              />
              <FormHelperText color="whiteAlpha.500">
                Número (com código do país) que será usado para enviar e receber mensagens.
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Identificação (opcional)</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="Ex: WhatsApp Comercial"
                value={formData.contact_label || ''}
                onChange={(e) => handleInputChange('contact_label', e.target.value)}
              />
              <FormHelperText color="whiteAlpha.500">
                Rótulo amigável para identificar este número internamente.
              </FormHelperText>
            </FormControl>
          </VStack>
        );

      case 'shopify':
        return (
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Nome da Loja</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="minha-loja"
                value={formData.shop_name || ''}
                onChange={(e) => handleInputChange('shop_name', e.target.value)}
              />
              <FormHelperText color="whiteAlpha.500">
                O nome da sua loja (ex: minha-loja.myshopify.com)
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Access Token</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                type="password"
                placeholder="shpat_..."
                value={formData.access_token || ''}
                onChange={(e) => handleInputChange('access_token', e.target.value)}
              />
              <FormHelperText color="whiteAlpha.500">
                Token de acesso da Admin API do Shopify
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Versão da API</FormLabel>
              <Select
                {...DARK_SELECT_PROPS}
                value={formData.api_version || '2024-01'}
                onChange={(e) => handleInputChange('api_version', e.target.value)}
              >
                <option value="2024-01">2024-01 (Recomendado)</option>
                <option value="2023-10">2023-10</option>
                <option value="2023-07">2023-07</option>
              </Select>
            </FormControl>
          </VStack>
        );

      case 'vtex':
        return (
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Nome da Conta</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="minhaloja"
                value={formData.account_name || ''}
                onChange={(e) => handleInputChange('account_name', e.target.value)}
              />
              <FormHelperText color="whiteAlpha.500">O nome da sua conta VTEX</FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">App Key</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="vtexappkey-minhaloja-XXXXX"
                value={formData.app_key || ''}
                onChange={(e) => handleInputChange('app_key', e.target.value)}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">App Token</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                type="password"
                placeholder="..."
                value={formData.app_token || ''}
                onChange={(e) => handleInputChange('app_token', e.target.value)}
              />
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Ambiente</FormLabel>
              <Select
                {...DARK_SELECT_PROPS}
                value={formData.environment || 'vtexcommercestable'}
                onChange={(e) => handleInputChange('environment', e.target.value)}
              >
                <option value="vtexcommercestable">Produção (stable)</option>
                <option value="vtexcommercebeta">Beta</option>
              </Select>
            </FormControl>
          </VStack>
        );

      case 'loja_integrada':
        return (
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Chave da API</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                type="password"
                placeholder="Sua chave de API"
                value={formData.api_key || ''}
                onChange={(e) => handleInputChange('api_key', e.target.value)}
              />
              <FormHelperText color="whiteAlpha.500">
                Encontre em: Painel Admin → Configurações → Integrações → API
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Chave da Aplicação (opcional)</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="Para apps parceiros"
                value={formData.application_key || ''}
                onChange={(e) => handleInputChange('application_key', e.target.value)}
              />
            </FormControl>
          </VStack>
        );

      case 'bigquery':
        return (
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Service Account JSON</FormLabel>
              <Textarea
                {...DARK_TEXTAREA_PROPS}
                placeholder='{"type": "service_account", "project_id": "...", ...}'
                value={formData.service_account_json || ''}
                onChange={(e) => handleInputChange('service_account_json', e.target.value)}
                minH="120px"
                fontFamily="mono"
                fontSize="xs"
              />
              <FormHelperText color="whiteAlpha.500">
                Cole o conteúdo do arquivo JSON da Service Account (contém project_id)
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Dataset ID</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="dataform"
                value={formData.dataset_id || ''}
                onChange={(e) => handleInputChange('dataset_id', e.target.value)}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Table Name</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="productsinvoices"
                value={formData.table_name || ''}
                onChange={(e) => handleInputChange('table_name', e.target.value)}
              />
              <FormHelperText color="whiteAlpha.500">
                Nome da tabela no BigQuery que você deseja sincronizar
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Data Location</FormLabel>
              <Select
                {...DARK_SELECT_PROPS}
                placeholder="Selecione a região dos dados"
                value={formData.location || 'southamerica-east1'}
                onChange={(e) => handleInputChange('location', e.target.value)}
              >
                <option value="southamerica-east1">South America - São Paulo (southamerica-east1)</option>
                <option value="US">United States (US)</option>
                <option value="EU">European Union (EU)</option>
                <option value="us-east1">US East (us-east1)</option>
                <option value="us-west1">US West (us-west1)</option>
                <option value="asia-northeast1">Asia Northeast - Tokyo (asia-northeast1)</option>
              </Select>
              <FormHelperText color="whiteAlpha.500">
                Região onde seus dados do BigQuery estão armazenados
              </FormHelperText>
            </FormControl>
          </VStack>
        );

      case 'postgresql':
      case 'mysql':
        return (
          <VStack spacing={4} align="stretch">
            <HStack spacing={4}>
              <FormControl isRequired flex={3}>
                <FormLabel fontSize="sm" color="whiteAlpha.700">Host</FormLabel>
                <Input
                  {...DARK_INPUT_PROPS}
                  placeholder="localhost"
                  value={formData.host || ''}
                  onChange={(e) => handleInputChange('host', e.target.value)}
                />
              </FormControl>

              <FormControl isRequired flex={1}>
                <FormLabel fontSize="sm" color="whiteAlpha.700">Porta</FormLabel>
                <Input
                  {...DARK_INPUT_PROPS}
                  placeholder={connector.id === 'postgresql' ? '5432' : '3306'}
                  value={formData.port || ''}
                  onChange={(e) => handleInputChange('port', e.target.value)}
                />
              </FormControl>
            </HStack>

            <FormControl isRequired>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Banco de Dados</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder="meu_banco"
                value={formData.database || ''}
                onChange={(e) => handleInputChange('database', e.target.value)}
              />
            </FormControl>

            <HStack spacing={4}>
              <FormControl isRequired>
                <FormLabel fontSize="sm" color="whiteAlpha.700">Usuário</FormLabel>
                <Input
                  {...DARK_INPUT_PROPS}
                  placeholder="usuario"
                  value={formData.user || ''}
                  onChange={(e) => handleInputChange('user', e.target.value)}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontSize="sm" color="whiteAlpha.700">Senha</FormLabel>
                <Input
                  {...DARK_INPUT_PROPS}
                  type="password"
                  placeholder="••••••••"
                  value={formData.password || ''}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                />
              </FormControl>
            </HStack>
          </VStack>
        );

      default:
        return (
          <Alert status="info" bg="rgba(59,130,246,0.12)" color="white" borderRadius="md">
            <AlertIcon color="#3b82f6" />
            Configuração para este conector em breve.
          </Alert>
        );
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" isCentered>
      <ModalOverlay bg="rgba(8,9,22,0.7)" backdropFilter="blur(6px)" />
      <ModalContent
        bg="#1a1b2e"
        color="white"
        border="1px solid"
        borderColor="rgba(255,255,255,0.08)"
        borderRadius="1rem"
        boxShadow="0 24px 60px rgba(0,0,0,0.45)"
      >
        <ModalHeader pb={2} borderBottom="1px solid" borderColor="rgba(255,255,255,0.06)">
          <HStack spacing={3}>
            <Flex
              w="44px"
              h="44px"
              bg={`${connector.iconColor}1f`}
              borderRadius="12px"
              align="center"
              justify="center"
            >
              <Icon as={connector.icon} boxSize={5} color={connector.iconColor} />
            </Flex>
            <VStack align="start" spacing={0}>
              <Text
                fontSize="1.25rem"
                fontWeight="normal"
                fontFamily="'Playfair Display', serif"
                color="white"
                lineHeight="1.2"
              >
                Conectar {connector.name}
              </Text>
              <Text fontSize="sm" color="whiteAlpha.500" fontWeight="normal">
                Configure as credenciais para sincronizar dados
              </Text>
            </VStack>
          </HStack>
        </ModalHeader>
        <ModalCloseButton color="whiteAlpha.700" _hover={{ bg: 'whiteAlpha.100', color: 'white' }} />

        <ModalBody py={5}>
          <VStack spacing={5} align="stretch">
            <FormControl>
              <FormLabel fontSize="sm" color="whiteAlpha.700">Nome da Conexão</FormLabel>
              <Input
                {...DARK_INPUT_PROPS}
                placeholder={`${connector.name} - Produção`}
                value={formData.nome_servico || ''}
                onChange={(e) => handleInputChange('nome_servico', e.target.value)}
              />
            </FormControl>

            <Divider borderColor="rgba(255,255,255,0.06)" />

            {renderFormFields()}

            {testResult && (
              <Alert
                status={testResult === 'success' ? 'success' : 'error'}
                borderRadius="md"
                bg={testResult === 'success' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)'}
                color="white"
                border="1px solid"
                borderColor={testResult === 'success' ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)'}
              >
                <AlertIcon color={testResult === 'success' ? '#10b981' : '#ef4444'} />
                {testResult === 'success'
                  ? 'Conexão testada com sucesso!'
                  : 'Falha na conexão. Verifique suas credenciais.'}
              </Alert>
            )}
          </VStack>
        </ModalBody>

        <ModalFooter gap={3} borderTop="1px solid" borderColor="rgba(255,255,255,0.06)">
          {connector.id !== 'whatsapp' && (
            <Button
              variant="outline"
              onClick={handleTestConnection}
              isLoading={isTesting}
              loadingText="Testando..."
              leftIcon={testResult === 'success' ? <FiCheck /> : undefined}
              borderColor="rgba(255,255,255,0.15)"
              color="white"
              bg="transparent"
              borderRadius="full"
              _hover={{ bg: 'whiteAlpha.100', borderColor: 'rgba(255,255,255,0.25)' }}
            >
              Testar Conexão
            </Button>
          )}

          <Button
            onClick={handleSubmit}
            isLoading={isLoading}
            loadingText={connector.id === 'whatsapp' ? 'Salvando...' : 'Conectando...'}
            isDisabled={connector.id !== 'whatsapp' && testResult !== 'success'}
            bgGradient="linear(to-r, #3b82f6, #2563eb)"
            color="white"
            borderRadius="full"
            _hover={{ bgGradient: 'linear(to-r, #2563eb, #1d4ed8)' }}
            _disabled={{
              bgGradient: 'none',
              bg: 'whiteAlpha.100',
              color: 'whiteAlpha.500',
              cursor: 'not-allowed',
            }}
            boxShadow={
              connector.id === 'whatsapp' || testResult === 'success'
                ? '0 4px 12px rgba(59,130,246,0.4)'
                : 'none'
            }
          >
            {connector.id === 'whatsapp' ? 'Salvar configuração' : 'Conectar e Sincronizar'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ConnectorModal;
