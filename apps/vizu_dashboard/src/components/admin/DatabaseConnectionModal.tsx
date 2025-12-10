import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  VStack,
  HStack,
  Text,
  Box,
  Input,
  FormControl,
  FormLabel,
  SimpleGrid,
  Icon,
  Spinner,
  useToast,
  InputGroup,
  InputRightElement,
  IconButton,
} from '@chakra-ui/react';
import { useState } from 'react';
import { 
  FiCheck, 
  FiArrowRight, 
  FiArrowLeft,
  FiEye,
  FiEyeOff,
  FiAlertCircle,
  FiServer
} from 'react-icons/fi';
import { 
  SiPostgresql, 
  SiMysql, 
  SiMongodb, 
  SiGooglebigquery,
  SiRedis
} from 'react-icons/si';

interface DatabaseConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface DatabaseType {
  id: string;
  name: string;
  icon: React.ElementType;
  color: string;
  defaultPort: string;
}

const databaseTypes: DatabaseType[] = [
  { id: 'postgresql', name: 'PostgreSQL', icon: SiPostgresql, color: '#336791', defaultPort: '5432' },
  { id: 'mysql', name: 'MySQL', icon: SiMysql, color: '#4479A1', defaultPort: '3306' },
  { id: 'sqlserver', name: 'SQL Server', icon: FiServer, color: '#CC2927', defaultPort: '1433' },
  { id: 'mongodb', name: 'MongoDB', icon: SiMongodb, color: '#47A248', defaultPort: '27017' },
  { id: 'bigquery', name: 'BigQuery', icon: SiGooglebigquery, color: '#4285F4', defaultPort: '' },
  { id: 'redis', name: 'Redis', icon: SiRedis, color: '#DC382D', defaultPort: '6379' },
];

type Step = 'select' | 'credentials' | 'testing' | 'success';

export const DatabaseConnectionModal = ({ isOpen, onClose }: DatabaseConnectionModalProps) => {
  const [step, setStep] = useState<Step>('select');
  const [selectedDb, setSelectedDb] = useState<DatabaseType | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const toast = useToast();

  // Form state
  const [formData, setFormData] = useState({
    connectionName: '',
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
  });

  const handleSelectDatabase = (db: DatabaseType) => {
    setSelectedDb(db);
    setFormData(prev => ({ ...prev, port: db.defaultPort }));
    setStep('credentials');
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setConnectionError(null);
    setStep('testing');

    // Simular teste de conexão
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Simular sucesso (em produção, chamaria a API)
    const success = true; // Math.random() > 0.3;

    if (success) {
      setStep('success');
    } else {
      setConnectionError('Não foi possível conectar ao banco de dados. Verifique as credenciais e tente novamente.');
      setStep('credentials');
    }
    setIsTestingConnection(false);
  };

  const handleSave = () => {
    toast({
      title: 'Conexão salva!',
      description: `A conexão "${formData.connectionName || selectedDb?.name}" foi adicionada com sucesso.`,
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
    handleClose();
  };

  const handleClose = () => {
    setStep('select');
    setSelectedDb(null);
    setFormData({
      connectionName: '',
      host: '',
      port: '',
      database: '',
      username: '',
      password: '',
    });
    setConnectionError(null);
    onClose();
  };

  const handleBack = () => {
    if (step === 'credentials') {
      setStep('select');
      setSelectedDb(null);
    } else if (step === 'success') {
      setStep('credentials');
    }
  };

  const isFormValid = () => {
    return (
      formData.host.trim() !== '' &&
      formData.database.trim() !== '' &&
      formData.username.trim() !== ''
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" isCentered>
      <ModalOverlay bg="blackAlpha.400" backdropFilter="blur(4px)" />
      <ModalContent borderRadius="22px" mx={4}>
        <ModalHeader pt={6} pb={2}>
          <HStack spacing={3}>
            {step !== 'select' && selectedDb && (
              <Box
                w="40px"
                h="40px"
                borderRadius="10px"
                bg={`${selectedDb.color}15`}
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <Icon as={selectedDb.icon} boxSize={5} color={selectedDb.color} />
              </Box>
            )}
            <VStack align="start" spacing={0}>
              <Text fontSize="18px" fontWeight="500">
                {step === 'select' && 'Conectar banco de dados'}
                {step === 'credentials' && `Configurar ${selectedDb?.name}`}
                {step === 'testing' && 'Testando conexão...'}
                {step === 'success' && 'Conexão estabelecida!'}
              </Text>
              <Text fontSize="14px" color="gray.500" fontWeight="normal">
                {step === 'select' && 'Escolha o tipo de banco de dados'}
                {step === 'credentials' && 'Insira as credenciais de acesso'}
                {step === 'testing' && 'Aguarde enquanto verificamos a conexão'}
                {step === 'success' && 'Seu banco de dados foi conectado com sucesso'}
              </Text>
            </VStack>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody py={6}>
          {/* Step 1: Select Database Type */}
          {step === 'select' && (
            <SimpleGrid columns={3} spacing={4}>
              {databaseTypes.map((db) => (
                <Box
                  key={db.id}
                  p={4}
                  borderRadius="14px"
                  border="2px solid"
                  borderColor="gray.200"
                  cursor="pointer"
                  transition="all 0.2s"
                  _hover={{ 
                    borderColor: db.color, 
                    bg: `${db.color}08`,
                    transform: 'scale(1.02)'
                  }}
                  onClick={() => handleSelectDatabase(db)}
                >
                  <VStack spacing={3}>
                    <Box
                      w="48px"
                      h="48px"
                      borderRadius="12px"
                      bg={`${db.color}15`}
                      display="flex"
                      alignItems="center"
                      justifyContent="center"
                    >
                      <Icon as={db.icon} boxSize={6} color={db.color} />
                    </Box>
                    <Text fontSize="14px" fontWeight="500" textAlign="center">
                      {db.name}
                    </Text>
                  </VStack>
                </Box>
              ))}
            </SimpleGrid>
          )}

          {/* Step 2: Credentials Form */}
          {step === 'credentials' && (
            <VStack spacing={4} align="stretch">
              {connectionError && (
                <HStack 
                  p={3} 
                  bg="red.50" 
                  borderRadius="10px" 
                  border="1px solid" 
                  borderColor="red.200"
                >
                  <Icon as={FiAlertCircle} color="red.500" />
                  <Text fontSize="14px" color="red.600">{connectionError}</Text>
                </HStack>
              )}

              <FormControl>
                <FormLabel fontSize="14px" color="gray.600">
                  Nome da conexão (opcional)
                </FormLabel>
                <Input
                  placeholder={`Meu ${selectedDb?.name}`}
                  value={formData.connectionName}
                  onChange={(e) => handleInputChange('connectionName', e.target.value)}
                  borderRadius="10px"
                />
              </FormControl>

              <HStack spacing={4}>
                <FormControl flex={3}>
                  <FormLabel fontSize="14px" color="gray.600">
                    Host / Endereço
                  </FormLabel>
                  <Input
                    placeholder="localhost ou IP"
                    value={formData.host}
                    onChange={(e) => handleInputChange('host', e.target.value)}
                    borderRadius="10px"
                  />
                </FormControl>
                <FormControl flex={1}>
                  <FormLabel fontSize="14px" color="gray.600">
                    Porta
                  </FormLabel>
                  <Input
                    placeholder={selectedDb?.defaultPort}
                    value={formData.port}
                    onChange={(e) => handleInputChange('port', e.target.value)}
                    borderRadius="10px"
                  />
                </FormControl>
              </HStack>

              <FormControl>
                <FormLabel fontSize="14px" color="gray.600">
                  Nome do banco de dados
                </FormLabel>
                <Input
                  placeholder="meu_banco"
                  value={formData.database}
                  onChange={(e) => handleInputChange('database', e.target.value)}
                  borderRadius="10px"
                />
              </FormControl>

              <FormControl>
                <FormLabel fontSize="14px" color="gray.600">
                  Usuário
                </FormLabel>
                <Input
                  placeholder="admin"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  borderRadius="10px"
                />
              </FormControl>

              <FormControl>
                <FormLabel fontSize="14px" color="gray.600">
                  Senha
                </FormLabel>
                <InputGroup>
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    borderRadius="10px"
                  />
                  <InputRightElement>
                    <IconButton
                      aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                      icon={showPassword ? <FiEyeOff /> : <FiEye />}
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowPassword(!showPassword)}
                    />
                  </InputRightElement>
                </InputGroup>
              </FormControl>
            </VStack>
          )}

          {/* Step 3: Testing Connection */}
          {step === 'testing' && (
            <VStack spacing={6} py={8}>
              <Spinner size="xl" color="blue.500" thickness="4px" />
              <VStack spacing={2}>
                <Text fontSize="16px" fontWeight="500">
                  Conectando ao {selectedDb?.name}...
                </Text>
                <Text fontSize="14px" color="gray.500">
                  Verificando credenciais e testando a conexão
                </Text>
              </VStack>
            </VStack>
          )}

          {/* Step 4: Success */}
          {step === 'success' && (
            <VStack spacing={6} py={8}>
              <Box
                w="80px"
                h="80px"
                borderRadius="full"
                bg="green.100"
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <Icon as={FiCheck} boxSize={10} color="green.500" />
              </Box>
              <VStack spacing={2}>
                <Text fontSize="18px" fontWeight="500">
                  Conexão bem-sucedida!
                </Text>
                <Text fontSize="14px" color="gray.500" textAlign="center">
                  O banco de dados <strong>{formData.database || selectedDb?.name}</strong> foi 
                  conectado e está pronto para uso.
                </Text>
              </VStack>
            </VStack>
          )}
        </ModalBody>

        <ModalFooter pb={6}>
          <HStack spacing={3} w="full" justify="space-between">
            {step !== 'select' && step !== 'testing' && (
              <Button
                variant="ghost"
                leftIcon={<FiArrowLeft />}
                onClick={handleBack}
              >
                Voltar
              </Button>
            )}
            {step === 'select' && <Box />}
            
            <HStack spacing={3}>
              <Button variant="ghost" onClick={handleClose}>
                Cancelar
              </Button>
              
              {step === 'credentials' && (
                <Button
                  bg="black"
                  color="white"
                  _hover={{ bg: 'gray.800' }}
                  rightIcon={<FiArrowRight />}
                  onClick={handleTestConnection}
                  isDisabled={!isFormValid()}
                  isLoading={isTestingConnection}
                >
                  Testar conexão
                </Button>
              )}
              
              {step === 'success' && (
                <Button
                  bg="black"
                  color="white"
                  _hover={{ bg: 'gray.800' }}
                  rightIcon={<FiCheck />}
                  onClick={handleSave}
                >
                  Salvar conexão
                </Button>
              )}
            </HStack>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default DatabaseConnectionModal;
