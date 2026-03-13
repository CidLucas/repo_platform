import { VStack, HStack, Box, useMediaQuery, Tabs, TabList, Tab, TabPanels, TabPanel } from '@chakra-ui/react';
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
    configStatus,
    requirements,
    collectedContext,
    uploadedCsvs,
    uploadedDocuments,
    uploadingFile,
    googleConnected,
    googleEmail,
    creating,
    activating,
    savingField,
    selectAgent,
    createNewSession,
    resumeSession,
    saveField,
    uploadCsv,
    uploadDoc,
    removeFile,
    finalize,
    activate,
    connectGoogle,
  } = useStandaloneAgent();

  const accessToken = auth?.session?.access_token;

  // If no session selected, show agent selector
  if (!currentSession) {
    return (
      <AdminLayout>
        <Box p={8} maxW="1200px" mx="auto">
          <AgentSelector
            agents={agents}
            selectedAgent={selectedAgent}
            loading={loadingCatalog}
            onSelectAgent={(agent) => selectAgent(agent.id)}
            onCreateSession={createNewSession}
          />
        </Box>
      </AdminLayout>
    );
  }

  // Configuration view with 3 panels
  return (
    <AdminLayout>
      <Box p={8} maxW="1600px" mx="auto">
        {isMobile ? (
          // Mobile: Tabs layout
          <Tabs isLazy orientation="vertical">
            <TabList>
              <Tab>Configuração</Tab>
              <Tab>Chat</Tab>
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
            <Box flex={1} minW="0">
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
            <Box flex={1} minW="0">
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
