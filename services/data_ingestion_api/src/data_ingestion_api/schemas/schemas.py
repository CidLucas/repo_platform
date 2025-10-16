# services/data_ingestion_api/schemas.py

from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional

# ----------------------------------------------------------------------
# Schemas de Credenciais (Input - O que o cliente/vendedor envia)
# ----------------------------------------------------------------------

class CredencialBase(BaseModel):
    """
    Schema base para qualquer credencial de serviço externo.
    Garante a modularização e agnósticismo do tipo de serviço.
    """
    cliente_vizu_id: str = Field(..., description="ID do Cliente Vizu que está criando a credencial.")
    nome_conexao: str = Field(..., description="Nome dado à conexão (ex: 'BigQuery Produção').")
    tipo_servico: str = Field(..., description="Tipo de serviço externo (ex: 'POSTGRES', 'BIGQUERY', 'VTEX').")

class SQLCredentialCreate(CredencialBase):
    """
    Schema específico para criação de credenciais de bancos de dados SQL (PostgreSQL, MySQL, etc.).
    Inclui os campos sensíveis que serão enviados ao Secret Manager.
    """
    host: str = Field(..., description="Endereço do host do banco de dados.")
    port: int = Field(5432, description="Porta de conexão (Padrão: 5432 para Postgres).")
    database: str = Field(..., description="Nome do banco de dados.")
    user: str = Field(..., description="Usuário para autenticação.")
    password: str = Field(..., description="Senha para autenticação.")
    # Usar Field(..., exclude=True) em Pydantic 2 se precisarmos garantir
    # que o campo não apareça em logs ou saídas acidentais, mas para
    # input inicial, o `password` é necessário.

class BigQueryCredentialCreate(CredencialBase):
    """
    Contrato para credenciais BigQuery. 
    O payload sensível será o JSON da Service Account Key.
    """
    # Detalhes da conexão
    project_id: str = Field(..., description="ID do Projeto GCP que contém o BigQuery.")
    dataset_id: Optional[str] = Field(None, description="ID do Dataset padrão para consultas.")
    
    # O payload sensível que será enviado ao Secret Manager.
    # Usamos Dict[str, Any] para o JSON da Service Account Key
    service_account_json: Dict[str, Any] = Field(..., description="Conteúdo JSON da chave da conta de serviço (Service Account Key).")

# ----------------------------------------------------------------------
# Schemas de Resposta (Output - O que a API retorna)
# ----------------------------------------------------------------------

class CredencialResponse(BaseModel):
    """
    Schema de resposta para a criação de credenciais.
    NUNCA deve retornar os dados sensíveis.
    """
    id_credencial: str = Field(..., description="ID único da credencial salva no nosso banco de dados.")
    secret_manager_id: str = Field(..., description="ID do segredo armazenado no Google Secret Manager.")
    nome_conexao: str
    tipo_servico: str
    status: str = Field("PENDENTE_VALIDACAO", description="Status atual da conexão (Pendente, Validada, Erro).")

    model_config = ConfigDict(from_attributes=True) 