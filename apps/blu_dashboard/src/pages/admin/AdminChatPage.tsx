import { VStack, HStack, Box, useMediaQuery, Tabs, TabList, Tab, TabPanels, TabPanel, Heading, Text } from '@chakra-ui/react';
import { useContext } from 'react';
import { AuthContext } from '../../contexts/AuthContext';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { AgentSelector } from '../../components/admin/AgentSelector';
import { FileUploadPanel } from '../../components/admin/FileUploadPanel';
import { RequirementsChecklist } from '../../components/admin/RequirementsChecklist';
import { ConfigHelperChat } from '../../components/admin/ConfigHelperChat';
import { useStandaloneAgent } from '../../hooks/useStandaloneAgent';

function AdminChatPage() {
  const auth = useContext(AuthContext);
  const [isMobile] = useMediaQuery('(max-width: 1024px)');
  const {
    agents,
    selectedAgent,
    loadingCatalog,
    currentSession,
    requirements,
    collectedContext,
    uploadedCsvs,
    uploadedDocuments,
    uploadingFile,
    googleConnected,
    savingField,
    selectAgent,
    createNewSession,
    saveField,
    uploadCsv,
    uploadDoc,
    removeFile,
    finalize,
    connectGoogle,
    reloadCatalog,
    activating,
  } = useStandaloneAgent();

  const accessToken = auth?.session?.access_token;
  const isAdmin = auth?.tier === 'ADMIN';

  // If no session selected, show agent selector
  if (!currentSession) {
    return (
      <AdminLayout>
        <Box p={8} maxW="1200px" mx="auto">
          <Box mb={8}>
            <Heading
              size="xl"
              fontFamily="'Playfair Display', serif"
              fontWeight="bold"
              mb={1}
            >
              <Text as="span" color="white">Agent </Text>
              <Text
                as="span"
                bgGradient="linear(to-r, #4361ee, #7209b7)"
                bgClip="text"
              >
                Configuration
              </Text>
            </Heading>
            <Text fontSize="sm" color="gray.400" mt={1}>
              Select an agent to configure
            </Text>
          </Box>
          <AgentSelector
            agents={agents}
            selectedAgent={selectedAgent}
            loading={loadingCatalog}
            onSelectAgent={(agent) => selectAgent(agent.id)}
            onCreateSession={createNewSession}
            onAgentCreated={reloadCatalog}
            isAdmin={isAdmin}
          />
        </Box>
      </AdminLayout>
    );
  }

  // Configuration view with 3 panels
  return (
    <AdminLayout>
      <Box
        p={8}
        maxW="1600px"
        mx="auto"
        sx={{
          '.chakra-tabs__tablist': { borderColor: 'rgba(255,255,255,0.08)' },
          '.chakra-tabs__tab': { color: 'gray.400' },
          '.chakra-input, .chakra-textarea, .chakra-select': {
            bg: '#14151f',
            color: 'white',
            borderColor: 'rgba(255,255,255,0.08)',
          },
          '.chakra-input::placeholder, .chakra-textarea::placeholder': {
            color: 'rgba(255,255,255,0.4)',
          },
          '.chakra-input:hover, .chakra-textarea:hover, .chakra-select:hover': {
            borderColor: 'rgba(255,255,255,0.16)',
          },
          '.chakra-input:focus, .chakra-textarea:focus, .chakra-select:focus': {
            borderColor: '#ff6b35',
            boxShadow: '0 0 0 1px #ff6b35',
          },
        }}
      >
        <Box mb={8}>
          <Heading
            size="xl"
            fontFamily="'Playfair Display', serif"
            fontWeight="bold"
            mb={1}
          >
            <Text as="span" color="white">Configure </Text>
            <Text
              as="span"
              bgGradient="linear(to-r, #ff6b35, #ff006e)"
              bgClip="text"
            >
              {selectedAgent?.name || 'Agent'}
            </Text>
          </Heading>
          <Text fontSize="sm" color="gray.400" mt={1}>
            Upload files and configure your agent settings
          </Text>
        </Box>
        {isMobile ? (
          // Mobile: Tabs layout
          <Tabs isLazy orientation="vertical" variant="unstyled">
            <TabList borderColor="rgba(255,255,255,0.08)" gap={2}>
              <Tab
                color="gray.400"
                _selected={{
                  color: 'white',
                  bgGradient: 'linear(to-r, #ff6b35, #ff006e)',
                  borderRadius: 'lg',
                }}
                _hover={{ bg: 'whiteAlpha.100', color: 'white' }}
                borderRadius="lg"
                mr={2}
              >
                Configuração
              </Tab>
              <Tab
                color="gray.400"
                _selected={{
                  color: 'white',
                  bgGradient: 'linear(to-r, #ff6b35, #ff006e)',
                  borderRadius: 'lg',
                }}
                _hover={{ bg: 'whiteAlpha.100', color: 'white' }}
                borderRadius="lg"
              >
                Chat
              </Tab>
            </TabList>
            <TabPanels>
              <TabPanel>
                <VStack align="stretch" spacing={6}>
                  {/* Files */}
                  <FileUploadPanel
                    csvFiles={uploadedCsvs}
                    documentFiles={uploadedDocuments}
                    uploading={uploadingFile}
                    onUploadCsv={uploadCsv}
                    onUploadDocument={uploadDoc}
                    onRemoveFile={removeFile}
                  />

                  {/* Requirements */}
                  <RequirementsChecklist
                    agent={selectedAgent}
                    requirements={requirements}
                    collectedContext={collectedContext}
                    csvCount={uploadedCsvs.length}
                    docCount={uploadedDocuments.length}
                    googleConnected={googleConnected}
                    onSaveField={saveField}
                    onConnectGoogle={connectGoogle}
                    onFinalize={finalize}
                    saving={savingField}
                    finalizing={activating}
                  />
                </VStack>
              </TabPanel>

              <TabPanel>
                <ConfigHelperChat
                  sessionId={currentSession?.id}
                  accessToken={accessToken}
                  agentName={selectedAgent?.name || 'Agente'}
                />
              </TabPanel>
            </TabPanels>
          </Tabs>
        ) : (
          // Desktop: Side-by-side layout
          <HStack align="flex-start" spacing={8}>
            {/* Left Panel: Configuration */}
            <Box
              flex={1}
              minW="0"
              bg="#1a1b2e"
              borderRadius="xl"
              borderWidth="1px"
              borderColor="rgba(255,255,255,0.08)"
              p={6}
            >
              <VStack align="stretch" spacing={6}>
                {/* Files */}
                <FileUploadPanel
                  csvFiles={uploadedCsvs}
                  documentFiles={uploadedDocuments}
                  uploading={uploadingFile}
                  onUploadCsv={uploadCsv}
                  onUploadDocument={uploadDoc}
                  onRemoveFile={removeFile}
                />

                {/* Requirements */}
                <RequirementsChecklist
                  agent={selectedAgent}
                  requirements={requirements}
                  collectedContext={collectedContext}
                  csvCount={uploadedCsvs.length}
                  docCount={uploadedDocuments.length}
                  googleConnected={googleConnected}
                  onSaveField={saveField}
                  onConnectGoogle={connectGoogle}
                  onFinalize={finalize}
                  saving={savingField}
                  finalizing={activating}
                />
              </VStack>
            </Box>

            {/* Right Panel: Config Helper Chat */}
            <Box
              flex={1}
              minW="0"
              bg="#1a1b2e"
              borderRadius="xl"
              borderWidth="1px"
              borderColor="rgba(255,255,255,0.08)"
              p={6}
            >
              <ConfigHelperChat
                sessionId={currentSession?.id}
                accessToken={accessToken}
                agentName={selectedAgent?.name || 'Agente'}
              />
            </Box>
          </HStack>
        )}
      </Box>
    </AdminLayout>
  );
}

export default AdminChatPage;
