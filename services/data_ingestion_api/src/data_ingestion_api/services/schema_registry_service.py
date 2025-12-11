"""
Schema Registry Service - CRUD para mapeamentos de schema no Supabase.

Este serviço gerencia a persistência de mapeamentos de colunas entre
fontes de dados externas e o schema canônico Vizu.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from data_ingestion_api.services.supabase_client import supabase_client

logger = logging.getLogger(__name__)


class MappingStatus(str, Enum):
    """Status possíveis de um mapeamento."""
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    ERROR = "error"


@dataclass
class SchemaMapping:
    """Representa um mapeamento de schema salvo."""
    id: str | None = None
    credential_id: str = ""
    resource_type: str = ""
    source_columns: list[str] = field(default_factory=list)
    mapping: dict[str, str] = field(default_factory=dict)  # {source: canonical}
    unmapped_columns: list[str] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)
    status: MappingStatus = MappingStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário para salvar no banco."""
        return {
            "credential_id": self.credential_id,
            "resource_type": self.resource_type,
            "source_columns": self.source_columns,
            "mapping": self.mapping,
            "unmapped_columns": self.unmapped_columns,
            "confidence_scores": self.confidence_scores,
            "status": self.status.value if isinstance(self.status, MappingStatus) else self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SchemaMapping":
        """Cria instância a partir de dicionário do banco."""
        return cls(
            id=data.get("id"),
            credential_id=data.get("credential_id", ""),
            resource_type=data.get("resource_type", ""),
            source_columns=data.get("source_columns", []),
            mapping=data.get("mapping", {}),
            unmapped_columns=data.get("unmapped_columns", []),
            confidence_scores=data.get("confidence_scores", {}),
            status=MappingStatus(data.get("status", "pending")),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class SchemaRegistryService:
    """
    Serviço para gerenciamento de mapeamentos de schema no Supabase.
    
    Operações:
    - Salvar mapeamento (create/update)
    - Buscar mapeamento por credential_id
    - Listar mapeamentos por status
    - Atualizar status
    - Deletar mapeamento
    """

    TABLE_NAME = "data_source_mappings"

    def __init__(self):
        self.client = supabase_client

    async def save_mapping(
        self,
        credential_id: str,
        resource_type: str,
        source_columns: list[str],
        mapping: dict[str, str],
        unmapped_columns: list[str] = None,
        confidence_scores: dict[str, float] = None,
        status: MappingStatus = None,
        metadata: dict[str, Any] = None
    ) -> SchemaMapping:
        """
        Salva ou atualiza um mapeamento de schema.
        
        Usa upsert baseado em (credential_id, resource_type) para
        evitar duplicatas.
        
        Args:
            credential_id: ID da credencial/fonte de dados
            resource_type: Tipo do recurso (products, orders, etc.)
            source_columns: Lista de colunas da fonte original
            mapping: Mapeamento {coluna_origem: coluna_vizu}
            unmapped_columns: Colunas não mapeadas
            confidence_scores: Scores de confiança do match
            status: Status do mapeamento
            metadata: Metadados adicionais
            
        Returns:
            SchemaMapping salvo/atualizado
        """
        # Determina status automaticamente se não fornecido
        if status is None:
            if unmapped_columns:
                status = MappingStatus.NEEDS_REVIEW
            elif confidence_scores and any(s < 0.75 for s in confidence_scores.values()):
                status = MappingStatus.NEEDS_REVIEW
            else:
                status = MappingStatus.READY

        data = {
            "credential_id": credential_id,
            "resource_type": resource_type,
            "source_columns": source_columns,
            "mapping": mapping,
            "unmapped_columns": unmapped_columns or [],
            "confidence_scores": confidence_scores or {},
            "status": status.value if isinstance(status, MappingStatus) else status,
            "metadata": metadata or {},
        }

        try:
            result = await self.client.upsert(
                self.TABLE_NAME,
                data,
                on_conflict="credential_id,resource_type"
            )

            logger.info(f"Mapeamento salvo: credential={credential_id}, resource={resource_type}, status={status}")

            return SchemaMapping.from_dict(result)

        except Exception as e:
            logger.error(f"Erro ao salvar mapeamento: {e}")
            raise

    async def get_mapping(
        self,
        credential_id: str,
        resource_type: str
    ) -> SchemaMapping | None:
        """
        Busca um mapeamento específico.
        
        Args:
            credential_id: ID da credencial
            resource_type: Tipo do recurso
            
        Returns:
            SchemaMapping encontrado ou None
        """
        try:
            result = await self.client.select_one(
                self.TABLE_NAME,
                filters={
                    "credential_id": credential_id,
                    "resource_type": resource_type
                }
            )

            if result:
                return SchemaMapping.from_dict(result)
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar mapeamento: {e}")
            return None

    async def get_mappings_by_credential(
        self,
        credential_id: str
    ) -> list[SchemaMapping]:
        """
        Busca todos os mapeamentos de uma credencial.
        
        Args:
            credential_id: ID da credencial
            
        Returns:
            Lista de mapeamentos
        """
        try:
            results = await self.client.select(
                self.TABLE_NAME,
                filters={"credential_id": credential_id}
            )

            return [SchemaMapping.from_dict(r) for r in results]

        except Exception as e:
            logger.error(f"Erro ao buscar mapeamentos: {e}")
            return []

    async def get_mappings_by_status(
        self,
        status: MappingStatus
    ) -> list[SchemaMapping]:
        """
        Busca mapeamentos por status.
        
        Args:
            status: Status a filtrar
            
        Returns:
            Lista de mapeamentos com o status especificado
        """
        try:
            status_value = status.value if isinstance(status, MappingStatus) else status
            results = await self.client.select(
                self.TABLE_NAME,
                filters={"status": status_value}
            )

            return [SchemaMapping.from_dict(r) for r in results]

        except Exception as e:
            logger.error(f"Erro ao buscar mapeamentos por status: {e}")
            return []

    async def update_status(
        self,
        credential_id: str,
        resource_type: str,
        status: MappingStatus
    ) -> bool:
        """
        Atualiza apenas o status de um mapeamento.
        
        Args:
            credential_id: ID da credencial
            resource_type: Tipo do recurso
            status: Novo status
            
        Returns:
            True se atualizado com sucesso
        """
        try:
            status_value = status.value if isinstance(status, MappingStatus) else status
            results = await self.client.update(
                self.TABLE_NAME,
                data={"status": status_value},
                filters={
                    "credential_id": credential_id,
                    "resource_type": resource_type
                }
            )

            if results:
                logger.info(f"Status atualizado: {credential_id}/{resource_type} -> {status}")
                return True
            return False

        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
            return False

    async def update_mapping(
        self,
        credential_id: str,
        resource_type: str,
        mapping: dict[str, str],
        unmapped_columns: list[str] = None
    ) -> SchemaMapping | None:
        """
        Atualiza o mapeamento de colunas (após revisão manual).
        
        Args:
            credential_id: ID da credencial
            resource_type: Tipo do recurso
            mapping: Novo mapeamento confirmado
            unmapped_columns: Colunas não mapeadas atualizadas
            
        Returns:
            SchemaMapping atualizado ou None
        """
        try:
            data = {
                "mapping": mapping,
                "status": MappingStatus.READY.value,
            }

            if unmapped_columns is not None:
                data["unmapped_columns"] = unmapped_columns

            results = await self.client.update(
                self.TABLE_NAME,
                data=data,
                filters={
                    "credential_id": credential_id,
                    "resource_type": resource_type
                }
            )

            if results:
                logger.info(f"Mapeamento atualizado: {credential_id}/{resource_type}")
                return SchemaMapping.from_dict(results[0])
            return None

        except Exception as e:
            logger.error(f"Erro ao atualizar mapeamento: {e}")
            return None

    async def delete_mapping(
        self,
        credential_id: str,
        resource_type: str
    ) -> bool:
        """
        Deleta um mapeamento.
        
        Args:
            credential_id: ID da credencial
            resource_type: Tipo do recurso
            
        Returns:
            True se deletado com sucesso
        """
        try:
            results = await self.client.delete(
                self.TABLE_NAME,
                filters={
                    "credential_id": credential_id,
                    "resource_type": resource_type
                }
            )

            if results:
                logger.info(f"Mapeamento deletado: {credential_id}/{resource_type}")
                return True
            return False

        except Exception as e:
            logger.error(f"Erro ao deletar mapeamento: {e}")
            return False

    async def delete_all_by_credential(self, credential_id: str) -> int:
        """
        Deleta todos os mapeamentos de uma credencial.
        
        Args:
            credential_id: ID da credencial
            
        Returns:
            Número de mapeamentos deletados
        """
        try:
            results = await self.client.delete(
                self.TABLE_NAME,
                filters={"credential_id": credential_id}
            )

            count = len(results) if results else 0
            logger.info(f"Mapeamentos deletados para {credential_id}: {count}")
            return count

        except Exception as e:
            logger.error(f"Erro ao deletar mapeamentos: {e}")
            return 0


# Instância global
schema_registry = SchemaRegistryService()
