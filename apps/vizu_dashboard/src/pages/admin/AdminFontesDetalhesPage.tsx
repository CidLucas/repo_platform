import {
  Box,
  VStack,
  HStack,
  Text,
  Icon,
  Button,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Spinner,
  useToast
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiDatabase, FiMoreVertical, FiTrash2, FiPlus, FiAlertCircle, FiFileText } from 'react-icons/fi';
import { useParams } from 'react-router-dom';
import { useUploadedFiles } from '../../hooks/useUploadedFiles';

// File item component
interface FileItemProps {
  fileName: string;
  uploadDate: string;
  fileSize: string;
  onDelete?: () => void;
}

const FileItem = ({ fileName, uploadDate, fileSize, onDelete }: FileItemProps) => {
  return (
    <Box
      bg="white"
      borderRadius="22px"
      border="1px solid"
      borderColor="gray.200"
      p={6}
      w="full"
    >
      <HStack justify="space-between" align="center">
        <VStack align="start" spacing={1}>
          <Text 
            fontSize="16px" 
            fontWeight="normal" 
            color="gray.900"
            letterSpacing="-0.3px"
          >
            {fileName}
          </Text>
          <Text 
            fontSize="14px" 
            color="gray.500" 
            lineHeight="20px"
            letterSpacing="-0.15px"
          >
            Upload: {uploadDate}  Arquivo: {fileSize}
          </Text>
        </VStack>
        
        <Menu>
          <MenuButton
            as={IconButton}
            icon={<FiMoreVertical />}
            variant="ghost"
            borderRadius="full"
            aria-label="Opções"
          />
          <MenuList bg="black" borderColor="gray.700" borderRadius="lg" minW="120px">
            <MenuItem 
              icon={<FiTrash2 />} 
              onClick={onDelete}
              bg="black"
              color="white"
              _hover={{ bg: 'gray.800' }}
              fontSize="12px"
            >
              Deletar arquivo
            </MenuItem>
          </MenuList>
        </Menu>
      </HStack>
    </Box>
  );
};

function AdminFontesDetalhesPage() {
  const { type } = useParams<{ type: string }>();
  const toast = useToast();

  // Fetch real file data
  const { files: filesData, loading, error, deleteFile } = useUploadedFiles();

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Handle delete with confirmation
  const handleDelete = async (fileId: string, fileName: string) => {
    if (!confirm(`Tem certeza que deseja deletar ${fileName}?`)) return;

    try {
      await deleteFile(fileId);
      toast({
        title: 'Arquivo deletado',
        description: `${fileName} foi deletado com sucesso.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (err) {
      toast({
        title: 'Erro ao deletar',
        description: err instanceof Error ? err.message : 'Falha ao deletar arquivo',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const getTypeTitle = () => {
    switch (type) {
      case 'csv': return '.CSV';
      case 'pdf': return '.PDF';
      case 'bigquery': return 'GOOGLE BIG QUERY';
      case 'hubspot': return 'HUBSPOT';
      default: return type?.toUpperCase() || 'Arquivos';
    }
  };

  // Loading state
  if (loading) {
    return (
      <AdminLayout>
        <Box p={8} textAlign="center">
          <Spinner size="xl" />
          <Text mt={4}>Carregando arquivos...</Text>
        </Box>
      </AdminLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <AdminLayout>
        <Box p={8} textAlign="center">
          <Icon as={FiAlertCircle} boxSize={12} color="red.500" mb={4} />
          <Text fontSize="18px" color="gray.700">Erro ao carregar arquivos</Text>
          <Text fontSize="14px" color="gray.500" mt={2}>{error.message}</Text>
        </Box>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        {/* Header Section */}
        <VStack spacing={6} mb={8}>
          {/* Icon */}
          <Box
            w="114px"
            h="114px"
            borderRadius="full"
            bg="gray.100"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Icon as={FiDatabase} boxSize={12} color="gray.600" />
          </Box>
          
          {/* Title */}
          <Text 
            fontSize="34px" 
            fontWeight="normal" 
            color="gray.900"
            letterSpacing="-0.3px"
            textAlign="center"
          >
            Minhas Fontes / {getTypeTitle()}
          </Text>
          
          <Text 
            fontSize="16px" 
            color="black" 
            textAlign="center"
            maxW="413px"
            lineHeight="24px"
            letterSpacing="-0.3px"
          >
            As fontes permitem que a VIZU faça uma leitura precisa sobre o seu negócio
          </Text>
          
          {/* Add Button */}
          <Button
            leftIcon={<FiPlus />}
            bg="black"
            color="white"
            borderRadius="full"
            px={8}
            py={6}
            fontWeight="medium"
            fontSize="18px"
            _hover={{ bg: 'gray.800' }}
          >
            Add arquivo
          </Button>
        </VStack>
        
        {/* Files List */}
        <VStack spacing={3} align="stretch">
          {filesData && filesData.files.length > 0 ? (
            filesData.files.map((file) => (
              <FileItem
                key={file.id}
                fileName={file.file_name}
                uploadDate={new Date(file.uploaded_at).toLocaleDateString('pt-BR')}
                fileSize={formatFileSize(file.file_size_bytes)}
                onDelete={() => handleDelete(file.id, file.file_name)}
              />
            ))
          ) : (
            <Box textAlign="center" py={12} bg="gray.50" borderRadius="16px">
              <Icon as={FiFileText} boxSize={10} color="gray.300" mb={4} />
              <Text fontSize="16px" color="gray.500">
                Nenhum arquivo encontrado
              </Text>
            </Box>
          )}
        </VStack>
      </Box>
    </AdminLayout>
  );
}

export default AdminFontesDetalhesPage;
