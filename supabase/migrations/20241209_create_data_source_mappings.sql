-- Migration: Create data_source_mappings table
-- Armazena o mapeamento de colunas entre fontes externas e schema canônico Vizu

CREATE TABLE IF NOT EXISTS data_source_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Referência à credencial/fonte de dados
    credential_id UUID NOT NULL,
    
    -- Tipo de recurso (products, orders, customers, inventory)
    resource_type VARCHAR(50) NOT NULL,
    
    -- Schema descoberto da fonte (array de nomes de colunas)
    source_columns JSONB NOT NULL DEFAULT '[]',
    
    -- Mapeamento confirmado: {"coluna_origem": "coluna_vizu", ...}
    mapping JSONB NOT NULL DEFAULT '{}',
    
    -- Colunas que não foram mapeadas (para referência)
    unmapped_columns JSONB NOT NULL DEFAULT '[]',
    
    -- Confiança do match automático: {"coluna_origem": 0.92, ...}
    confidence_scores JSONB NOT NULL DEFAULT '{}',
    
    -- Status do mapeamento
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'needs_review', 'ready', 'error')),
    
    -- Metadados adicionais (ex: versão do schema, notas)
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Índice único para evitar duplicatas
    CONSTRAINT unique_credential_resource UNIQUE (credential_id, resource_type)
);

-- Índices para queries comuns
CREATE INDEX IF NOT EXISTS idx_mappings_credential ON data_source_mappings(credential_id);
CREATE INDEX IF NOT EXISTS idx_mappings_status ON data_source_mappings(status);
CREATE INDEX IF NOT EXISTS idx_mappings_resource ON data_source_mappings(resource_type);

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_data_source_mappings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_data_source_mappings_updated_at ON data_source_mappings;
CREATE TRIGGER trigger_update_data_source_mappings_updated_at
    BEFORE UPDATE ON data_source_mappings
    FOR EACH ROW
    EXECUTE FUNCTION update_data_source_mappings_updated_at();

-- Comentários
COMMENT ON TABLE data_source_mappings IS 'Armazena mapeamentos de colunas entre fontes externas e schema canônico Vizu';
COMMENT ON COLUMN data_source_mappings.source_columns IS 'Lista de colunas descobertas na fonte original';
COMMENT ON COLUMN data_source_mappings.mapping IS 'Mapeamento coluna_origem -> coluna_vizu confirmado';
COMMENT ON COLUMN data_source_mappings.confidence_scores IS 'Score de confiança (0-1) do match automático por coluna';
COMMENT ON COLUMN data_source_mappings.status IS 'pending=aguardando, needs_review=precisa revisão, ready=pronto, error=erro';
