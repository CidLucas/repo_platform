import { useState, useContext } from 'react';
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
} from '@chakra-ui/react';
import { FiCheck } from 'react-icons/fi';
import * as connectorService from '../../services/connectorService';
import { AuthContext } from '../../contexts/AuthContext';

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
}

// Tipos de formulário por conector
type FormData = Record<string, string>;

const ConnectorModal = ({ isOpen, onClose, connector }: ConnectorModalProps) => {
  const [formData, setFormData] = useState<FormData>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const toast = useToast();
  const auth = useContext(AuthContext);

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
          nome_conexao: formData.nome_conexao || `${connector.name} - Teste`,
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
      case 'bigquery':
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
      case 'postgresql':
      case 'mysql':
        return {
          host: formData.host || '',
          port: parseInt(formData.port || '5432'),
          database: formData.database || '',
          user: formData.user || '',
          password: formData.password || '',
        };
      default:
        return {} as connectorService.CredentialPayload;
    }
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

      const response = await connectorService.createCredential({
        client_id: clienteVizuId,
        nome_conexao: formData.nome_conexao || `${connector.name} - Produção`,
        tipo_servico: tipoServico,
        credentials,
      });

      // Inicia sincronização automática após criar credencial
      try {
        if (!formData.table_name) {
          throw new Error('Table name is required for BigQuery connector');
        }
        await connectorService.startSync(
          response.id_credencial,
          clienteVizuId,
          formData.table_name  // Use ONLY user-provided table name, no fallback
        );
      } catch (syncError) {
        console.warn('Falha ao iniciar sincronização automática:', syncError);
        // Não falha a operação inteira se apenas a sync falhar
      }

      toast({
        title: 'Conector configurado!',
        description: 'A sincronização de dados foi iniciada.',
        status: 'success',
        duration: 5000,
      });

      onClose();
    } catch (error) {
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
      case 'shopify':
        return (
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="sm">Nome da Loja</FormLabel>
              <Input
                placeholder="minha-loja"
                value={formData.shop_name || ''}
                onChange={(e) => handleInputChange('shop_name', e.target.value)}
              />
              <FormHelperText>
                O nome da sua loja (ex: minha-loja.myshopify.com)
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Access Token</FormLabel>
              <Input
                type="password"
                placeholder="shpat_..."
                value={formData.access_token || ''}
                onChange={(e) => handleInputChange('access_token', e.target.value)}
              />
              <FormHelperText>
                Token de acesso da Admin API do Shopify
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Versão da API</FormLabel>
              <Select
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
              <FormLabel fontSize="sm">Nome da Conta</FormLabel>
              <Input
                placeholder="minhaloja"
                value={formData.account_name || ''}
                onChange={(e) => handleInputChange('account_name', e.target.value)}
              />
              <FormHelperText>
                O nome da sua conta VTEX
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">App Key</FormLabel>
              <Input
                placeholder="vtexappkey-minhaloja-XXXXX"
                value={formData.app_key || ''}
                onChange={(e) => handleInputChange('app_key', e.target.value)}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">App Token</FormLabel>
              <Input
                type="password"
                placeholder="..."
                value={formData.app_token || ''}
                onChange={(e) => handleInputChange('app_token', e.target.value)}
              />
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Ambiente</FormLabel>
              <Select
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
              <FormLabel fontSize="sm">Chave da API</FormLabel>
              <Input
                type="password"
                placeholder="Sua chave de API"
                value={formData.api_key || ''}
                onChange={(e) => handleInputChange('api_key', e.target.value)}
              />
              <FormHelperText>
                Encontre em: Painel Admin → Configurações → Integrações → API
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Chave da Aplicação (opcional)</FormLabel>
              <Input
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
              <FormLabel fontSize="sm">Service Account JSON</FormLabel>
              <Textarea
                placeholder='{"type": "service_account", "project_id": "...", ...}'
                value={formData.service_account_json || ''}
                onChange={(e) => handleInputChange('service_account_json', e.target.value)}
                minH="120px"
                fontFamily="mono"
                fontSize="xs"
              />
              <FormHelperText>
                Cole o conteúdo do arquivo JSON da Service Account (contém project_id)
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Dataset ID</FormLabel>
              <Input
                placeholder="dataform"
                value={formData.dataset_id || ''}
                onChange={(e) => handleInputChange('dataset_id', e.target.value)}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Table Name</FormLabel>
              <Input
                placeholder="productsinvoices"
                value={formData.table_name || ''}
                onChange={(e) => handleInputChange('table_name', e.target.value)}
              />
              <FormHelperText>
                Nome da tabela no BigQuery que você deseja sincronizar
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Data Location</FormLabel>
              <Select
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
              <FormHelperText>
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
                <FormLabel fontSize="sm">Host</FormLabel>
                <Input
                  placeholder="localhost"
                  value={formData.host || ''}
                  onChange={(e) => handleInputChange('host', e.target.value)}
                />
              </FormControl>

              <FormControl isRequired flex={1}>
                <FormLabel fontSize="sm">Porta</FormLabel>
                <Input
                  placeholder={connector.id === 'postgresql' ? '5432' : '3306'}
                  value={formData.port || ''}
                  onChange={(e) => handleInputChange('port', e.target.value)}
                />
              </FormControl>
            </HStack>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Banco de Dados</FormLabel>
              <Input
                placeholder="meu_banco"
                value={formData.database || ''}
                onChange={(e) => handleInputChange('database', e.target.value)}
              />
            </FormControl>

            <HStack spacing={4}>
              <FormControl isRequired>
                <FormLabel fontSize="sm">Usuário</FormLabel>
                <Input
                  placeholder="usuario"
                  value={formData.user || ''}
                  onChange={(e) => handleInputChange('user', e.target.value)}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel fontSize="sm">Senha</FormLabel>
                <Input
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
          <Alert status="info">
            <AlertIcon />
            Configuração para este conector em breve.
          </Alert>
        );
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent borderRadius="16px">
        <ModalHeader pb={2}>
          <HStack spacing={3}>
            <Flex
              w="40px"
              h="40px"
              bg="gray.50"
              borderRadius="10px"
              align="center"
              justify="center"
            >
              <Icon
                as={connector.icon}
                boxSize={5}
                color={connector.iconColor}
              />
            </Flex>
            <VStack align="start" spacing={0}>
              <Text fontSize="lg" fontWeight="medium">
                Conectar {connector.name}
              </Text>
              <Text fontSize="sm" color="gray.500" fontWeight="normal">
                Configure as credenciais para sincronizar dados
              </Text>
            </VStack>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody py={4}>
          <VStack spacing={5} align="stretch">
            {/* Nome da conexão */}
            <FormControl>
              <FormLabel fontSize="sm">Nome da Conexão</FormLabel>
              <Input
                placeholder={`${connector.name} - Produção`}
                value={formData.nome_conexao || ''}
                onChange={(e) => handleInputChange('nome_conexao', e.target.value)}
              />
            </FormControl>

            <Divider />

            {/* Campos específicos do conector */}
            {renderFormFields()}

            {/* Resultado do teste */}
            {testResult && (
              <Alert
                status={testResult === 'success' ? 'success' : 'error'}
                borderRadius="md"
              >
                <AlertIcon />
                {testResult === 'success'
                  ? 'Conexão testada com sucesso!'
                  : 'Falha na conexão. Verifique suas credenciais.'}
              </Alert>
            )}
          </VStack>
        </ModalBody>

        <ModalFooter gap={3}>
          <Button
            variant="outline"
            onClick={handleTestConnection}
            isLoading={isTesting}
            loadingText="Testando..."
            leftIcon={testResult === 'success' ? <FiCheck /> : undefined}
            colorScheme={testResult === 'success' ? 'green' : 'gray'}
          >
            Testar Conexão
          </Button>

          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={isLoading}
            loadingText="Conectando..."
            isDisabled={testResult !== 'success'}
          >
            Conectar e Sincronizar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ConnectorModal;
