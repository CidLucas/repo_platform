📋 CONTEXTO DO PROJETO
Arquitetura do Monorepo vizu-mono
O repositório vizubr/vizu-mono é um monorepo Python (81. 4%) com arquitetura de microserviços:

Estrutura Principal:

libs/ - Bibliotecas compartilhadas (vizu_auth, vizu_context_service, vizu_db_connector, vizu_models, etc.)
services/ - Microserviços FastAPI (tool_pool_api, atendente_core, clients_api, clientes_finais_api, etc.)
docker-compose.yml - Orquestração local com perfil local para infra e perfil padrão para aplicação
Poetry para gerenciamento de dependências
Python 3.11+
PostgreSQL local + Supabase em produção
Redis para sessões/cache
Padrão de observabilidade (OpenTelemetry, Langfuse)
Serviços Relevantes:

tool_pool_api (porta 8006) - MCP server que expõe tools para agentes LLM
vizu_context_service - Gerencia contexto e credenciais por usuário/tenant
vizu_auth (em implementação, ver VIZU_AUTH_PLAN.md) - Autenticação JWT + API-Key centralizada
Padrões de Implementação:

Cada serviço tem src/{service_name}/ com main. py, api/, core/
Config via Pydantic Settings (BaseSettings) com env vars
PYTHONPATH ajustado no docker-compose
Health checks e depends_on para ordem de inicialização
FastAPI com routers modulares
🎯 OBJETIVO DA INTEGRAÇÃO
Adicionar ao MCP server (tool_pool_api) uma tool plugável que permite agentes LLM interagirem com Google Suite (Sheets, Gmail, Calendar) de forma multiusuário/multi-tenant, onde:

Cada usuário/cliente Vizu tem suas próprias credenciais OAuth2 Google armazenadas de forma segura
Autenticação OAuth2 é gerenciada via expansão da vizu_auth
Tokens de acesso/refresh são armazenados no safe vizu context (não em . env)
Funções utilitárias (Sheets/Gmail/Calendar) vivem em lib compartilhada vizu_google_suite_client
Endpoints REST no MCP server orquestram o fluxo OAuth e execução das operações
🔍 ANÁLISE DE ARQUITETURA (5 Perguntas Críticas Revisadas)
1. Onde implementar o conector Google API?
Resposta Revisada: Criar duas bibliotecas em libs/:

A) libs/vizu_google_suite_client/ - Cliente puro para Google APIs

Módulos: google_sheets.py, google_gmail.py, google_calendar. py
Funções que recebem tokens OAuth já validados
Sem dependência de vizu_auth, apenas Google API clients
Wrappers high-level para operações comuns
B) Expansão de libs/vizu_auth/ - OAuth2 flow para provedores externos

Novo módulo: src/vizu_auth/oauth2/ com:
base. py - Interface abstrata OAuth2Provider
google_provider.py - Implementação Google OAuth2
oauth_manager.py - Orquestrador de flows
Responsável por gerar URLs, processar callbacks, renovar tokens
Integra com vizu_context_service para persistir tokens por usuário
Justificativa: Separação de responsabilidades - vizu_auth gerencia autenticação/autorização, vizu_google_suite_client gerencia operações de negócio.

2. Como orquestrar o fluxo OAuth2 multiusuário?
Resposta Revisada: Fluxo OAuth2 Authorization Code com PKCE:

Endpoints no tool_pool_api (ou novo serviço integration_api):

POST /integrations/google/auth/initiate

Input: cliente_vizu_id (do contexto autenticado via vizu_auth)
Gera URL de consentimento Google com state/PKCE
Salva state temporário no Redis (5min TTL)
Output: { "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..." }
GET /integrations/google/auth/callback

Recebe: code, state (query params do redirect Google)
Valida state contra Redis
Troca code por tokens (access_token + refresh_token)
Persiste tokens no vizu_context_service associado ao cliente_vizu_id
Redireciona para frontend com status de sucesso
DELETE /integrations/google/auth/revoke

Remove tokens do contexto
Opcionalmente revoga no Google
Storage de Tokens:

Armazenados em tabela client_integrations (ou similar) no PostgreSQL
Criptografados com CREDENTIALS_ENCRYPTION_KEY (padrão já usado no clients_api, linha 114 docker-compose)
Indexados por (cliente_vizu_id, provider, provider_type)
Campos: access_token_encrypted, refresh_token_encrypted, expires_at, scopes, metadata_json
3. Como provisionar credenciais Google API (client_id, secret, scopes)?
Resposta Revisada: NUNCA via . env global - usar tabela de configuração por tenant:

Modelo no libs/vizu_models:

Python
class IntegrationConfig(SQLModel, table=True):
    __tablename__ = "integration_configs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    cliente_vizu_id: UUID = Field(foreign_key="clientes_vizu.id")
    provider: str  # "google"
    config_type: str  # "oauth2_client"

    # Configurações criptografadas
    client_id_encrypted: str
    client_secret_encrypted: str

    # Configurações públicas
    redirect_uri: str
    scopes: List[str] = Field(sa_column=Column(JSON))

    created_at: datetime
    updated_at: datetime
Provisionamento:

Cada cliente Vizu cria seu próprio Google Cloud Project
Configura OAuth2 credentials no Google Cloud Console
Usa clients_api (porta 8005) para POST /integrations/config:
Envia client_id, client_secret, redirect_uri
API criptografa e salva na tabela
Frontend mostra URL de consentimento usando esses dados
Scopes Necessários:

Python
GOOGLE_SUITE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # Sheets read/write
    "https://www.googleapis.com/auth/gmail.readonly",  # Gmail read
    "https://www.googleapis.com/auth/gmail.send",  # Gmail send
    "https://www.googleapis.com/auth/calendar.readonly",  # Calendar read
    "https://www.googleapis.com/auth/calendar.events",  # Calendar write
    "openid",
    "email",
    "profile"
]
4. Como registrar e expor a tool no MCP server?
Resposta Revisada: Seguir padrão existente do tool_pool_api:

Estrutura da Tool (baseada em análise do código):

Python
# services/tool_pool_api/src/tool_pool_api/tools/google_suite_tool.py

from mcp.server import Server
from vizu_auth import AuthResult
from vizu_context_service import ContextService
from vizu_google_suite_client import GoogleSheetsClient, GoogleGmailClient, GoogleCalendarClient

class GoogleSuiteTool:
    def __init__(self, context_service: ContextService):
        self.context_service = context_service

    async def _get_user_tokens(self, cliente_vizu_id: UUID) -> dict:
        """Recupera tokens OAuth do vizu_context_service"""
        integration = await self.context_service.get_integration_tokens(
            cliente_vizu_id=cliente_vizu_id,
            provider="google"
        )
        if not integration or not integration.is_valid():
            raise ValueError("Google integration not configured or expired")
        return integration. get_decrypted_tokens()

    @mcp.tool()
    async def write_to_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        cliente_vizu_id: UUID  # Injetado pelo auth middleware
    ) -> dict:
        """Escreve dados em uma planilha Google Sheets"""
        tokens = await self._get_user_tokens(cliente_vizu_id)
        client = GoogleSheetsClient(access_token=tokens['access_token'])
        result = await client.append_values(spreadsheet_id, range_name, values)
        return {"status": "success", "updated_cells": result.updated_cells}

    @mcp.tool()
    async def read_emails(
        self,
        query: str,
        max_results: int = 10,
        cliente_vizu_id: UUID
    ) -> List[dict]:
        """Busca e lê emails do Gmail"""
        tokens = await self._get_user_tokens(cliente_vizu_id)
        client = GoogleGmailClient(access_token=tokens['access_token'])
        emails = await client.search_messages(query, max_results)
        return [email.to_dict() for email in emails]

    @mcp. tool()
    async def query_calendar(
        self,
        time_min: datetime,
        time_max: datetime,
        calendar_id: str = "primary",
        cliente_vizu_id: UUID
    ) -> List[dict]:
        """Consulta eventos do Google Calendar"""
        tokens = await self._get_user_tokens(cliente_vizu_id)
        client = GoogleCalendarClient(access_token=tokens['access_token'])
        events = await client. list_events(calendar_id, time_min, time_max)
        return [event.to_dict() for event in events]
Registro no MCP Server:

Python
# services/tool_pool_api/src/tool_pool_api/main.py

from tool_pool_api.tools.google_suite_tool import GoogleSuiteTool

app = FastAPI(...)
mcp_server = Server("tool-pool")

# Registro da tool
google_tool = GoogleSuiteTool(context_service=get_context_service())
mcp_server.register_tool(google_tool)
5. Como organizar funções por serviço (Sheets/Gmail/Calendar)?
Resposta Confirmada: Módulos separados em libs/vizu_google_suite_client/src/vizu_google_suite_client/:

Estrutura:

Code
libs/vizu_google_suite_client/
├── pyproject.toml
├── README.md
├── src/
│   └── vizu_google_suite_client/
│       ├── __init__.py
│       ├── base.py              # Cliente base com refresh logic
│       ├── exceptions.py        # GoogleAPIError, QuotaExceededError, etc.
│       ├── models.py            # Pydantic models para responses
│       ├── sheets/
│       │   ├── __init__.py
│       │   ├── client.py        # GoogleSheetsClient
│       │   └── models.py        # SheetRange, CellData, etc.
│       ├── gmail/
│       │   ├── __init__. py
│       │   ├── client.py        # GoogleGmailClient
│       │   └── models.py        # EmailMessage, Attachment, etc.
│       └── calendar/
│           ├── __init__.py
│           ├── client.py        # GoogleCalendarClient
│           └── models.py        # CalendarEvent, Attendee, etc.
└── tests/
    ├── test_sheets.py
    ├── test_gmail.py
    └── test_calendar.py
Dependências (pyproject.toml):

TOML
[tool.poetry.dependencies]
python = "^3.11"
google-api-python-client = "^2.110.0"
google-auth = "^2.25.0"
google-auth-httplib2 = "^0. 2.0"
google-auth-oauthlib = "^1.2.0"
pydantic = "^2.5.0"
httpx = "^0.25.0"
📐 FASES DE IMPLEMENTAÇÃO COM CHECKPOINTS
FASE 0: Preparação e Setup (Checkpoint: Infraestrutura)
Task 0. 1: Criar Google Cloud Project e OAuth Credentials
Objetivo: Configurar aplicação OAuth no Google Cloud Console

Passos:

Acesse Google Cloud Console
Crie projeto "Vizu Integration - Dev"
Habilite APIs:
Google Sheets API
Gmail API
Google Calendar API
Configure OAuth Consent Screen:
User Type: External
Scopes: adicionar os 5 scopes listados acima
Test users: adicionar seu email
Crie OAuth 2.0 Client ID:
Application type: Web application
Authorized redirect URIs: http://localhost:8006/integrations/google/auth/callback
Baixe JSON de credenciais
Checkpoint:

bash
# Verificar que você tem:
# - Client ID (formato: *. apps.googleusercontent.com)
# - Client Secret (string aleatória)
# - Redirect URI configurada
Task 0.2: Adicionar Modelo de Dados para Integrations
Objetivo: Criar schema SQL para armazenar tokens OAuth

Instruções:

Crie migration em libs/vizu_db_connector/alembic/versions/:
Python
# {timestamp}_add_integration_tables.py

def upgrade():
    op.create_table(
        'integration_configs',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('cliente_vizu_id', postgresql.UUID(), nullable=False),
        sa. Column('provider', sa.String(50), nullable=False),
        sa.Column('config_type', sa.String(50), nullable=False),
        sa.Column('client_id_encrypted', sa.Text(), nullable=False),
        sa.Column('client_secret_encrypted', sa.Text(), nullable=False),
        sa.Column('redirect_uri', sa.String(500), nullable=False),
        sa.Column('scopes', postgresql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['cliente_vizu_id'], ['clientes_vizu.id']),
        sa.UniqueConstraint('cliente_vizu_id', 'provider', 'config_type')
    )

    op.create_table(
        'integration_tokens',
        sa.Column('id', postgresql. UUID(), nullable=False),
        sa.Column('cliente_vizu_id', postgresql.UUID(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_type', sa.String(50), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scopes', postgresql.JSON(), nullable=False),
        sa. Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa. PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['cliente_vizu_id'], ['clientes_vizu. id']),
        sa.UniqueConstraint('cliente_vizu_id', 'provider')
    )

    op.create_index('idx_integration_tokens_cliente_provider',
                    'integration_tokens',
                    ['cliente_vizu_id', 'provider'])
Adicione models em libs/vizu_models/src/vizu_models/integration. py
Rode migration: make migrate (conforme MIGRATIONS. md do repo)
Checkpoint:

bash
# Verificar tabelas criadas
docker compose exec postgres psql -U user -d vizu_db -c "\dt integration*"

# Deve listar:
# - integration_configs
# - integration_tokens
FASE 1: Biblioteca vizu_google_suite_client (Checkpoint: Funções Google)
Task 1.1: Criar Estrutura da Lib
Objetivo: Scaffold da biblioteca compartilhada

Instruções:

Criar estrutura conforme item 5 da análise
Criar pyproject.toml seguindo padrão de vizu_context_service
poetry install para validar
Checkpoint:

bash
cd libs/vizu_google_suite_client
poetry check
# Deve retornar "All set!"

poetry install
# Deve instalar todas as dependências
Task 1.2: Implementar Base Client
Objetivo: Cliente base com lógica de refresh de token

Instruções: Criar libs/vizu_google_suite_client/src/vizu_google_suite_client/base.py:

Python
from abc import ABC
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable
import httpx
from google.oauth2. credentials import Credentials
from googleapiclient.discovery import build

class BaseGoogleClient(ABC):
    """Cliente base para Google APIs com refresh automático"""

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        token_refresh_callback: Optional[Callable[[str, str], Awaitable[None]]] = None
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=1))
        self.token_refresh_callback = token_refresh_callback
        self._credentials: Optional[Credentials] = None

    def _get_credentials(self) -> Credentials:
        """Retorna credenciais Google, refreshando se necessário"""
        if self._credentials is None:
            self._credentials = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token
            )

        if self._credentials.expired and self._credentials. refresh_token:
            self._credentials.refresh(Request())
            # Callback para persistir novo token
            if self.token_refresh_callback:
                asyncio.create_task(
                    self.token_refresh_callback(
                        self._credentials.token,
                        self._credentials. refresh_token
                    )
                )

        return self._credentials

    def _build_service(self, service_name: str, version: str):
        """Constrói cliente Google API"""
        return build(
            service_name,
            version,
            credentials=self._get_credentials(),
            cache_discovery=False
        )
Checkpoint:

Python
# Teste de importação
poetry run python -c "
from vizu_google_suite_client.base import BaseGoogleClient
print('BaseClient imported successfully')
"
Task 1.3: Implementar Google Sheets Client
Objetivo: Wrapper para operações em planilhas

Instruções: Criar libs/vizu_google_suite_client/src/vizu_google_suite_client/sheets/client.py:

Python
from typing import List, Any, Optional
from vizu_google_suite_client.base import BaseGoogleClient
from vizu_google_suite_client.sheets.models import SheetWriteResult, SheetReadResult

class GoogleSheetsClient(BaseGoogleClient):
    """Cliente para Google Sheets API"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = None

    @property
    def service(self):
        if self._service is None:
            self._service = self._build_service('sheets', 'v4')
        return self._service

    async def append_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED"
    ) -> SheetWriteResult:
        """
        Adiciona linhas ao final de uma planilha

        Args:
            spreadsheet_id: ID da planilha (da URL)
            range_name: Range no formato "Sheet1!A1" ou "Sheet1"
            values: Lista de linhas, cada linha é lista de valores
            value_input_option: "RAW" ou "USER_ENTERED"

        Returns:
            SheetWriteResult com metadados da operação
        """
        body = {'values': values}
        result = self.service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()

        return SheetWriteResult(
            spreadsheet_id=spreadsheet_id,
            updated_range=result.get('updates', {}).get('updatedRange'),
            updated_rows=result.get('updates', {}).get('updatedRows'),
            updated_columns=result.get('updates', {}).get('updatedColumns'),
            updated_cells=result.get('updates', {}).get('updatedCells')
        )

    async def read_values(
        self,
        spreadsheet_id: str,
        range_name: str
    ) -> SheetReadResult:
        """
        Lê valores de uma planilha

        Args:
            spreadsheet_id: ID da planilha
            range_name: Range no formato "Sheet1!A1:C10"

        Returns:
            SheetReadResult com os valores lidos
        """
        result = self.service.spreadsheets(). values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        return SheetReadResult(
            spreadsheet_id=spreadsheet_id,
            range=result.get('range'),
            values=result.get('values', []),
            major_dimension=result.get('majorDimension', 'ROWS')
        )

    async def update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED"
    ) -> SheetWriteResult:
        """Atualiza valores em range específico"""
        body = {'values': values}
        result = self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()

        return SheetWriteResult(
            spreadsheet_id=spreadsheet_id,
            updated_range=result.get('updatedRange'),
            updated_rows=result.get('updatedRows'),
            updated_columns=result.get('updatedColumns'),
            updated_cells=result.get('updatedCells')
        )
Criar models em sheets/models.py:

Python
from pydantic import BaseModel
from typing import List, Any, Optional

class SheetWriteResult(BaseModel):
    spreadsheet_id: str
    updated_range: Optional[str]
    updated_rows: Optional[int]
    updated_columns: Optional[int]
    updated_cells: Optional[int]

class SheetReadResult(BaseModel):
    spreadsheet_id: str
    range: str
    values: List[List[Any]]
    major_dimension: str
Checkpoint:

Python
# Teste unitário com mock
poetry run pytest tests/test_sheets.py -v

# Teste de integração manual (requer token válido)
poetry run python -c "
import asyncio
from vizu_google_suite_client. sheets import GoogleSheetsClient

async def test():
    client = GoogleSheetsClient(access_token='YOUR_TOKEN')
    result = await client.read_values('SPREADSHEET_ID', 'Sheet1!A1:B10')
    print(f'Read {len(result.values)} rows')

asyncio.run(test())
"
Task 1.4: Implementar Gmail Client
Objetivo: Wrapper para ler e enviar emails

Instruções: Criar gmail/client.py seguindo padrão do Sheets Client:

Python
class GoogleGmailClient(BaseGoogleClient):
    """Cliente para Gmail API"""

    async def search_messages(
        self,
        query: str,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None
    ) -> List[EmailMessage]:
        """
        Busca mensagens usando query do Gmail

        Args:
            query: Query no formato Gmail (ex: "from:user@example.com is:unread")
            max_results: Número máximo de resultados
            label_ids: Filtro por labels (ex: ["INBOX", "UNREAD"])
        """
        # Implementação usando gmail. users(). messages().list()
        pass

    async def get_message(self, message_id: str) -> EmailMessage:
        """Recupera mensagem completa por ID"""
        pass

    async def send_message(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> str:
        """Envia email, retorna message_id"""
        pass
Checkpoint: Testes passando para search, get e send.

Task 1.5: Implementar Calendar Client
Objetivo: Wrapper para consultar e criar eventos

Instruções: Criar calendar/client.py:

Python
class GoogleCalendarClient(BaseGoogleClient):
    """Cliente para Google Calendar API"""

    async def list_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Lista eventos em período"""
        pass

    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: datetime,
        end: datetime,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> CalendarEvent:
        """Cria novo evento"""
        pass

    async def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent:
        """Recupera evento por ID"""
        pass
Checkpoint: Testes unitários com mocks passando.

FASE 2: Expansão vizu_auth para OAuth2 (Checkpoint: OAuth Flow)
Task 2.1: Criar Módulo OAuth2 em vizu_auth
Objetivo: Adicionar suporte a OAuth2 flows externos

Instruções:

Criar estrutura em libs/vizu_auth/src/vizu_auth/oauth2/:

base.py - Interface OAuth2Provider(ABC)
google_provider.py - Implementação Google
oauth_manager.py - Orquestrador
models.py - OAuthConfig, TokenResponse, etc.
Implementar OAuth2Provider:

Python
from abc import ABC, abstractmethod
from typing import Dict, Optional
from pydantic import BaseModel

class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str]
    expires_in: int
    token_type: str
    scope: str

class OAuth2Provider(ABC):
    @abstractmethod
    async def get_authorization_url(self, state: str, **kwargs) -> str:
        """Gera URL de consentimento"""
        pass

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str, **kwargs) -> TokenResponse:
        """Troca authorization code por tokens"""
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Renova access token usando refresh token"""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revoga token"""
        pass
Implementar GoogleOAuth2Provider:
Python
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

class GoogleOAuth2Provider(OAuth2Provider):
    def __init__(self, config: OAuthConfig):
        self.config = config
        self.flow = Flow. from_client_config(
            {
                "web": {
                    "client_id": config. client_id,
                    "client_secret": config.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2. googleapis.com/token",
                    "redirect_uris": [config.redirect_uri]
                }
            },
            scopes=config.scopes
        )
        self.flow.redirect_uri = config.redirect_uri

    async def get_authorization_url(self, state: str, **kwargs) -> str:
        auth_url, _ = self.flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Força prompt para obter refresh_token
        )
        return auth_url

    async def exchange_code_for_tokens(self, code: str, **kwargs) -> TokenResponse:
        self.flow.fetch_token(code=code)
        credentials = self.flow.credentials

        return TokenResponse(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_in=3600,  # Google padrão
            token_type="Bearer",
            scope=" ".join(credentials.scopes or [])
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis. com/token",
            client_id=self.config.client_id,
            client_secret=self.config.client_secret
        )
        credentials.refresh(Request())

        return TokenResponse(
            access_token=credentials.token,
            refresh_token=refresh_token,
            expires_in=3600,
            token_type="Bearer",
            scope=""
        )

    async def revoke_token(self, token: str) -> bool:
        revoke_url = "https://oauth2.googleapis.com/revoke"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                revoke_url,
                params={"token": token},
                headers={"content-type": "application/x-www-form-urlencoded"}
            )
            return response. status_code == 200
Checkpoint:

Python
poetry run python -c "
from vizu_auth.oauth2.google_provider import GoogleOAuth2Provider
from vizu_auth.oauth2.models import OAuthConfig

config = OAuthConfig(
    client_id='test',
    client_secret='test',
    redirect_uri='http://localhost/callback',
    scopes=['email']
)
provider = GoogleOAuth2Provider(config)
print('Google OAuth2 Provider created successfully')
"
Task 2.2: Integrar OAuth Manager com vizu_context_service
Objetivo: Persistir tokens no contexto seguro

Instruções:

Expandir vizu_context_service com métodos:
Python
class ContextService:
    async def save_integration_config(
        self,
        cliente_vizu_id: UUID,
        provider: str,
        config: OAuthConfig
    ) -> IntegrationConfig:
        """Salva configuração OAuth criptografada"""
        pass

    async def get_integration_config(
        self,
        cliente_vizu_id: UUID,
        provider: str
    ) -> Optional[IntegrationConfig]:
        """Recupera configuração OAuth"""
        pass

    async def save_integration_tokens(
        self,
        cliente_vizu_id: UUID,
        provider: str,
        tokens: TokenResponse
    ) -> IntegrationTokens:
        """Salva tokens OAuth criptografados"""
        pass

    async def get_integration_tokens(
        self,
        cliente_vizu_id: UUID,
        provider: str,
        auto_refresh: bool = True
    ) -> Optional[IntegrationTokens]:
        """
        Recupera tokens OAuth
        Se auto_refresh=True e token expirado, renova automaticamente
        """
        pass

    async def revoke_integration(
        self,
        cliente_vizu_id: UUID,
        provider: str
    ) -> bool:
        """Remove integração"""
        pass
Implementar criptografia usando CREDENTIALS_ENCRYPTION_KEY (Fernet):
Python
from cryptography.fernet import Fernet

class TokenEncryption:
    def __init__(self, key: str):
        self.cipher = Fernet(key. encode())

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher. decrypt(ciphertext.encode()). decode()
Checkpoint:

bash
# Teste de criptografia
poetry run pytest libs/vizu_context_service/tests/test_integration_tokens.py -v

# Deve passar testes de:
# - Salvar config criptografado
# - Recuperar e descriptografar
# - Renovar token expirado automaticamente
FASE 3: Endpoints OAuth no MCP Server (Checkpoint: Auth Flow Completo)
Task 3. 1: Criar Router de Integrações
Objetivo: Adicionar endpoints OAuth ao tool_pool_api

Instruções:

Criar services/tool_pool_api/src/tool_pool_api/api/integrations_router.py:
Python
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
import secrets
from datetime import timedelta

from vizu_auth import AuthResult
from vizu_auth.fastapi import create_auth_dependency
from vizu_auth.oauth2 import GoogleOAuth2Provider, OAuthConfig
from vizu_context_service import ContextService
from tool_pool_api.core.config import get_settings

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# Dependency para autenticação
get_auth = create_auth_dependency(...)

# Dependency para context service
def get_context_service() -> ContextService:
    # Implementar usando SessionLocal do db_connector
    pass

@router.post("/google/config")
async def configure_google_integration(
    client_id: str,
    client_secret: str,
    auth: AuthResult = Depends(get_auth),
    context: ContextService = Depends(get_context_service)
):
    """
    Configura credenciais OAuth Google para o cliente autenticado
    """
    settings = get_settings()

    config = OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=f"{settings.BASE_URL}/integrations/google/callback",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
            "openid", "email", "profile"
        ]
    )

    await context.save_integration_config(
        cliente_vizu_id=auth.cliente_vizu_id,
        provider="google",
        config=config
    )

    return {"status": "configured", "provider": "google"}


@router.post("/google/auth/initiate")
async def initiate_google_auth(
    auth: AuthResult = Depends(get_auth),
    context: ContextService = Depends(get_context_service),
    redis_client = Depends(get_redis)
):
    """
    Inicia fluxo OAuth Google
    Retorna URL de consentimento
    """
    # Recuperar config do cliente
    config = await context.get_integration_config(
        auth.cliente_vizu_id,
        "google"
    )
    if not config:
        raise HTTPException(400, "Google integration not configured")

    # Gerar state aleatório
    state = secrets. token_urlsafe(32)

    # Salvar state no Redis (5min TTL)
    await redis_client.setex(
        f"oauth_state:{state}",
        300,  # 5 minutos
        str(auth.cliente_vizu_id)
    )

    # Gerar URL de autorização
    provider = GoogleOAuth2Provider(config. get_decrypted_config())
    auth_url = await provider.get_authorization_url(state=state)

    return {
        "auth_url": auth_url,
        "state": state,
        "expires_in": 300
    }


@router.get("/google/callback")
async def google_auth_callback(
    code: str = Query(...),
    state: str = Query(... ),
    context: ContextService = Depends(get_context_service),
    redis_client = Depends(get_redis)
):
    """
    Callback OAuth Google
    Troca code por tokens e salva no contexto
    """
    # Validar state
    cliente_vizu_id_str = await redis_client.get(f"oauth_state:{state}")
    if not cliente_vizu_id_str:
        raise HTTPException(400, "Invalid or expired state")

    cliente_vizu_id = UUID(cliente_vizu_id_str. decode())

    # Remover state do Redis
    await redis_client.delete(f"oauth_state:{state}")

    # Recuperar config
    config = await context.get_integration_config(cliente_vizu_id, "google")
    if not config:
        raise HTTPException(400, "Google integration not configured")

    # Trocar code por tokens
    provider = GoogleOAuth2Provider(config.get_decrypted_config())
    tokens = await provider. exchange_code_for_tokens(code)

    # Salvar tokens no contexto
    await context.save_integration_tokens(
        cliente_vizu_id=cliente_vizu_id,
        provider="google",
        tokens=tokens
    )

    # Redirecionar para frontend com sucesso
    frontend_url = get_settings(). FRONTEND_URL
    return RedirectResponse(
        url=f"{frontend_url}/integrations/success? provider=google"
    )


@router.delete("/google/auth/revoke")
async def revoke_google_auth(
    auth: AuthResult = Depends(get_auth),
    context: ContextService = Depends(get_context_service)
):
    """
    Revoga integração Google
    """
    # Recuperar tokens
    tokens = await context.get_integration_tokens(
        auth. cliente_vizu_id,
        "google",
        auto_refresh=False
    )

    if tokens:
        # Revogar no Google
        config = await context.get_integration_config(auth.cliente_vizu_id, "google")
        provider = GoogleOAuth2Provider(config.get_decrypted_config())
        await provider.revoke_token(tokens.access_token)

    # Remover do contexto
    await context.revoke_integration(auth.cliente_vizu_id, "google")

    return {"status": "revoked", "provider": "google"}


@router.get("/google/status")
async def get_google_status(
    auth: AuthResult = Depends(get_auth),
    context: ContextService = Depends(get_context_service)
):
    """
    Verifica status da integração Google
    """
    config = await context.get_integration_config(auth.cliente_vizu_id, "google")
    tokens = await context.get_integration_tokens(
        auth.cliente_vizu_id,
        "google",
        auto_refresh=False
    )

    return {
        "configured": config is not None,
        "connected": tokens is not None and not tokens.is_expired(),
        "scopes": config.scopes if config else [],
        "expires_at": tokens.expires_at if tokens else None
    }
Registrar router no main.py:
Python
from tool_pool_api.api.integrations_router import router as integrations_router

app.include_router(integrations_router)
Adicionar variáveis ao . env. example:
bash
# Google OAuth (por cliente, vai para DB)
# GOOGLE_CLIENT_ID e SECRET vêm do DB via integration_configs

# URLs
BASE_URL=http://localhost:8006
FRONTEND_URL=http://localhost:3000

# Criptografia (compartilhada com clients_api)
CREDENTIALS_ENCRYPTION_KEY=<gerar com Fernet. generate_key()>
Checkpoint:

bash
# Testar fluxo completo

# 1. Configurar integração
curl -X POST http://localhost:8006/integrations/google/config \
  -H "X-API-KEY: sua-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "*. apps.googleusercontent.com",
    "client_secret": "seu-secret"
  }'

# 2. Iniciar OAuth
curl -X POST http://localhost:8006/integrations/google/auth/initiate \
  -H "X-API-KEY: sua-api-key"
# Deve retornar: {"auth_url": "https://accounts.google.com/.. .", "state": "..."}

# 3. Abrir auth_url no navegador, autorizar, verificar callback

# 4. Verificar status
curl http://localhost:8006/integrations/google/status \
  -H "X-API-KEY: sua-api-key"
# Deve retornar: {"configured": true, "connected": true, ... }
FASE 4: Tool MCP para Google Suite (Checkpoint: Tools Funcionais)
Task 4. 1: Criar Google Suite Tool Handler
Objetivo: Implementar MCP tool que usa os clientes Google

Instruções: Criar services/tool_pool_api/src/tool_pool_api/tools/google_suite_tool.py (código já fornecido na análise item 4).

Checkpoint:

Python
# Teste unitário
poetry run pytest services/tool_pool_api/tests/test_google_suite_tool.py -v

# Teste de integração (requer OAuth configurado)
# Via MCP protocol ou endpoint REST do tool_pool_api
Task 4.2: Registrar Tool no MCP Server
Objetivo: Expor funções Google via MCP

Instruções:

Atualizar services/tool_pool_api/src/tool_pool_api/main.py:
Python
from tool_pool_api.tools.google_suite_tool import GoogleSuiteTool

# ...  código existente ...

# Registrar Google Suite Tool
google_tool = GoogleSuiteTool(context_service=get_context_service())
mcp_server.register_tool(google_tool)
Adicionar middleware de injeção de cliente_vizu_id:
Python
# Baseado no padrão existente do tool_pool_api
# O cliente_vizu_id deve ser extraído do AccessToken e injetado nos parâmetros da tool
Checkpoint:

bash
# Listar tools disponíveis via MCP
curl http://localhost:8006/mcp/tools

# Deve incluir:
# - write_to_sheet
# - read_emails
# - query_calendar

# Testar tool via MCP client ou Copilot Agent
FASE 5: Testes, Documentação e Refinamento (Checkpoint: Produção-Ready)
Task 5. 1: Testes End-to-End
Objetivo: Validar fluxo completo OAuth + Tools

Instruções:

Criar services/tool_pool_api/tests/integration/test_google_suite_e2e.py:
Python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
async def test_full_google_sheets_flow():
    """
    Teste E2E:
    1. Configura OAuth
    2. Inicia auth (mock callback)
    3. Usa tool para escrever em Sheet
    4. Verifica resultado
    """
    async with AsyncClient(base_url="http://localhost:8006") as client:
        # Setup OAuth config
        response = await client.post(
            "/integrations/google/config",
            headers={"X-API-KEY": "test-key"},
            json={"client_id": "test", "client_secret": "test"}
        )
        assert response. status_code == 200

        # Mock tokens (para testes, bypassar OAuth real)
        # ...  código de mock ...

        # Chamar tool
        response = await client.post(
            "/mcp/tools/write_to_sheet",
            headers={"X-API-KEY": "test-key"},
            json={
                "spreadsheet_id": "test-sheet-id",
                "range_name": "Sheet1",
                "values": [["Teste", "123"]]
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
Rodar testes:
bash
# Testes unitários
poetry run pytest libs/vizu_google_suite_client/tests -v

# Testes de integração (requer mocks ou tokens reais)
poetry run pytest services/tool_pool_api/tests -v -m integration
Checkpoint: Todos os testes passando.

Task 5.2: Documentação Completa
Objetivo: Documentar para desenvolvedores e usuários finais

Instruções:

Criar docs/google_suite_integration. md:
Markdown
# Google Suite Integration - Guia Completo

## Visão Geral
Integração multiusuário com Google Sheets, Gmail e Calendar via OAuth2.

## Setup para Desenvolvedores

### 1.  Configurar Google Cloud Project
[Passos detalhados da Task 0. 1]

### 2.  Configurar Variáveis de Ambiente
[Lista completa de env vars]

### 3.  Rodar Migrações
[Comandos de migration]

## Setup para Clientes Vizu

### 1. Configurar Credenciais OAuth
POST /integrations/google/config
[Exemplo de request/response]

### 2.  Autorizar Acesso
POST /integrations/google/auth/initiate
[Fluxo completo com screenshots]

### 3. Usar Tools
[Exemplos de chamadas para cada tool]

## Arquitetura

### Diagrama de Fluxo OAuth
[Mermaid diagram]

### Armazenamento de Tokens
[Explicação do modelo de dados]

### Refresh Automático
[Como funciona o auto-refresh]

## Troubleshooting

### Erro: "Invalid grant"
[Soluções]

### Erro: "Quota exceeded"
[Soluções e rate limiting]

## API Reference

### Endpoints
[Documentação completa de todos os endpoints]

### Tools MCP
[Documentação completa de todas as tools]
Atualizar README principal do monorepo
Adicionar exemplos em examples/google_suite/:
oauth_setup.py - Script de setup
sheets_example.py - Exemplo de uso Sheets
gmail_example.py - Exemplo de uso Gmail
calendar_example.py - Exemplo de uso Calendar
Checkpoint: Documentação revisada por peer review.

Task 5.3: Observabilidade e Logs
Objetivo: Instrumentar com traces e métricas

Instruções:

Adicionar logging estruturado em todas as operações:
Python
import structlog

logger = structlog.get_logger()

async def write_to_sheet(... ):
    logger.info(
        "google_sheets_write_start",
        cliente_vizu_id=cliente_vizu_id,
        spreadsheet_id=spreadsheet_id[:8] + ".. .",  # Parcial por segurança
        range_name=range_name
    )

    try:
        result = ...
        logger.info(
            "google_sheets_write_success",
            updated_cells=result.updated_cells
        )
        return result
    except Exception as e:
        logger.error(
            "google_sheets_write_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
Adicionar traces OpenTelemetry:
Python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def write_to_sheet(...):
    with tracer.start_as_current_span("google. sheets.write") as span:
        span.set_attribute("spreadsheet_id", spreadsheet_id)
        span.set_attribute("range_name", range_name)
        # ...  operação ...
Configurar alertas para:
Taxa de erros OAuth (> 5%)
Tokens expirados não renovados
Quota exceeded do Google
Latência > 5s em operações
Checkpoint: Dashboard no Langfuse/OTEL mostrando métricas.

Task 5.4: Rate Limiting e Quotas
Objetivo: Respeitar limites do Google e evitar abusos

Instruções:

Implementar rate limiter por cliente:
Python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=lambda: str(auth_result.cliente_vizu_id))

@router.post("/google/sheets/write")
@limiter. limit("10/minute")  # 10 writes por minuto por cliente
async def write_sheet(... ):
    pass
Implementar retry com backoff exponencial:
Python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError)
)
async def _make_google_api_call():
    # Chamada Google API
    pass
Monitorar quotas:
Python
# Capturar quota exceeded errors
try:
    result = sheets_api.call()
except HttpError as e:
    if e.resp.status == 429:  # Quota exceeded
        logger. warning("google_quota_exceeded", cliente_vizu_id=...)
        # Enfileirar para retry posterior
        await enqueue_retry(...)
        raise QuotaExceededError()
Checkpoint: Testes de carga mostrando rate limiting funcionando.

📊 CRITÉRIOS DE SUCESSO FINAIS
Funcionalidade
 OAuth flow completo funcionando (initiate → callback → tokens salvos)
 Refresh automático de tokens expirando
 Todas as 3 tools (Sheets/Gmail/Calendar) funcionais
 Multiusuário: cada cliente tem seus próprios tokens isolados
 Revogação de acesso funcionando
Segurança
 Tokens criptografados em repouso (Fernet)
 Client secrets criptografados
 Logs não expõem tokens completos
 State validation no callback OAuth
 HTTPS obrigatório em produção (documentado)
Performance
 Rate limiting por cliente implementado
 Retry com backoff para erros transientes
 Timeout de 30s em chamadas Google API
 Cache de metadata (quando aplicável)
Observabilidade
 Traces OpenTelemetry em todas as operações
 Logs estruturados (structlog)
 Métricas de erro/latência
 Alertas configurados
Documentação
 README atualizado
 Guia de setup Google Cloud Project
 Exemplos funcionais para cada tool
 Troubleshooting guide
 API reference completa
Testes
 Cobertura > 80% em libs
 Testes E2E para fluxo OAuth
 Testes de integração com mocks Google API
 Testes de erro (token expirado, quota exceeded, etc.)
🔧 FONTES DE PESQUISA DETALHADAS
Documentação Oficial Google
OAuth2 Google: https://developers.google.com/identity/protocols/oauth2/web-server
Google Sheets API v4: https://developers.google. com/sheets/api/reference/rest
Gmail API: https://developers.google. com/gmail/api/reference/rest
Google Calendar API: https://developers.google.com/calendar/api/v3/reference
Python Quickstarts: https://developers.google.com/workspace/guides/get-started
Bibliotecas Python
google-api-python-client: https://github.com/googleapis/google-api-python-client
google-auth: https://google-auth.readthedocs. io/
google-auth-oauthlib: https://google-auth-oauthlib. readthedocs.io/
Padrões do Projeto vizu-mono
VIZU_AUTH_PLAN. md (anexo) - Arquitetura de autenticação
MIGRATIONS.md (no repo) - Como rodar migrations
docker-compose.yml - Configuração de serviços
.github/copilot-instructions.md - Padrões de código
Segurança e Criptografia
Cryptography (Fernet): https://cryptography.io/en/latest/fernet/
OWASP OAuth2: https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html
🚨 NOTAS DE SEGURANÇA CRÍTICAS
NUNCA commitar secrets: Use . gitignore para arquivos de credenciais
Criptografar tokens: Sempre usar Fernet antes de salvar no DB
HTTPS obrigatório: Redirect URI deve ser HTTPS em produção
State validation: Sempre validar state no callback OAuth
Scope mínimo: Pedir apenas scopes necessários
Rotation de secrets: Implementar rotação de CREDENTIALS_ENCRYPTION_KEY
Audit logging: Registrar todas as operações sensíveis
Token expiration: Validar expires_at antes de usar tokens
📞 SUPORTE E PRÓXIMOS PASSOS
Após implementação completa, considerar:

Expansão para outras APIs Google: Drive, Docs, Forms
Webhooks: Receber notificações do Google (push notifications)
Batch operations: Otimizar múltiplas operações em uma chamada
Offline access: Melhorar estratégia de refresh tokens
Admin SDK: Gerenciamento de workspace para clientes enterprise
Este prompt foi elaborado com análise profunda do repositório vizubr/vizu-mono, considerando:

Arquitetura existente de microserviços
Padrões de autenticação (vizu_auth em desenvolvimento)
Sistema de contexto multiusuário (vizu_context_service)
Integração com MCP server (tool_pool_api)
Padrões de deployment Docker
Observabilidade e segurança
