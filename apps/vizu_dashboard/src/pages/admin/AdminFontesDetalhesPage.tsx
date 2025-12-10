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
  MenuItem
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiDatabase, FiMoreVertical, FiTrash2, FiPlus } from 'react-icons/fi';
import { useParams } from 'react-router-dom';

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
  
  // Mock data for files
  const files = [
    { fileName: 'PLANILHA_SOLEDAD_19_10_2017.CVS', uploadDate: '15/10/2024', fileSize: '1GB' },
    { fileName: 'PLANILHA_SOLEDAD_19_10_2017.CVS', uploadDate: '15/10/2024', fileSize: '1GB' },
    { fileName: 'PLANILHA_SOLEDAD_19_10_2017.CVS', uploadDate: '15/10/2024', fileSize: '1GB' },
    { fileName: 'PLANILHA_SOLEDAD_19_10_2017.CVS', uploadDate: '15/10/2024', fileSize: '1GB' },
    { fileName: 'PLANILHA_SOLEDAD_19_10_2017.CVS', uploadDate: '15/10/2024', fileSize: '1GB' },
    { fileName: 'PLANILHA_SOLEDAD_19_10_2017.CVS', uploadDate: '15/10/2024', fileSize: '1GB' },
  ];

  const getTypeTitle = () => {
    switch (type) {
      case 'csv': return '.CSV';
      case 'pdf': return '.PDF';
      case 'bigquery': return 'GOOGLE BIG QUERY';
      case 'hubspot': return 'HUBSPOT';
      default: return type?.toUpperCase() || 'Arquivos';
    }
  };

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
          {files.map((file, index) => (
            <FileItem
              key={index}
              fileName={file.fileName}
              uploadDate={file.uploadDate}
              fileSize={file.fileSize}
              onDelete={() => console.log('Delete', file.fileName)}
            />
          ))}
        </VStack>
      </Box>
    </AdminLayout>
  );
}

export default AdminFontesDetalhesPage;
