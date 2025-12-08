"""
Prompt version management and comparison.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class PromptVersion:
    """Represents a specific version of a prompt."""

    name: str
    version: int
    content: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    cliente_vizu_id: Optional[UUID] = None

    @property
    def full_name(self) -> str:
        """Get full versioned name."""
        return f"{self.name}/v{self.version}"


class PromptManager:
    """
    Manage prompt versions and deployments.

    Provides:
    - Version listing and comparison
    - Active version tracking
    - Rollback support
    - A/B testing hooks
    """

    def __init__(self, db_session: Optional[Any] = None):
        """
        Initialize PromptManager.

        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db_session = db_session

    async def list_versions(
        self,
        name: str,
        cliente_id: Optional[UUID] = None,
        include_inactive: bool = False,
    ) -> List[PromptVersion]:
        """
        List all versions of a prompt.

        Args:
            name: Prompt name
            cliente_id: Filter by client
            include_inactive: Include inactive versions

        Returns:
            List of PromptVersion sorted by version descending
        """
        if not self.db_session:
            return []

        try:
            from sqlmodel import select
            from vizu_models import PromptTemplate

            query = select(PromptTemplate).where(PromptTemplate.name == name)

            if cliente_id:
                query = query.where(PromptTemplate.cliente_vizu_id == cliente_id)

            if not include_inactive:
                query = query.where(PromptTemplate.is_active == True)

            query = query.order_by(PromptTemplate.version.desc())

            results = self.db_session.exec(query).all()

            return [
                PromptVersion(
                    name=r.name,
                    version=r.version,
                    content=r.content,
                    is_active=r.is_active,
                    created_at=r.created_at if hasattr(r, "created_at") else None,
                    cliente_vizu_id=r.cliente_vizu_id,
                )
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error listing prompt versions: {e}")
            return []

    async def get_active_version(
        self,
        name: str,
        cliente_id: Optional[UUID] = None,
    ) -> Optional[PromptVersion]:
        """
        Get the active version of a prompt.

        Args:
            name: Prompt name
            cliente_id: Optional client ID

        Returns:
            Active PromptVersion or None
        """
        versions = await self.list_versions(name, cliente_id, include_inactive=False)
        return versions[0] if versions else None

    async def create_version(
        self,
        name: str,
        content: str,
        cliente_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None,
        activate: bool = True,
    ) -> PromptVersion:
        """
        Create a new version of a prompt.

        Args:
            name: Prompt name
            content: Prompt content
            cliente_id: Optional client ID for client-specific prompt
            metadata: Optional metadata
            activate: Whether to activate this version

        Returns:
            Created PromptVersion
        """
        if not self.db_session:
            raise RuntimeError("Database session required for version creation")

        try:
            from vizu_models import PromptTemplate

            # Get next version number
            versions = await self.list_versions(name, cliente_id, include_inactive=True)
            next_version = max([v.version for v in versions], default=0) + 1

            # Deactivate previous versions if activating
            if activate and versions:
                for v in versions:
                    await self._set_active(name, v.version, cliente_id, False)

            # Create new version
            prompt = PromptTemplate(
                name=name,
                content=content,
                version=next_version,
                is_active=activate,
                cliente_vizu_id=cliente_id,
            )

            self.db_session.add(prompt)
            self.db_session.commit()
            self.db_session.refresh(prompt)

            return PromptVersion(
                name=prompt.name,
                version=prompt.version,
                content=prompt.content,
                is_active=prompt.is_active,
                cliente_vizu_id=prompt.cliente_vizu_id,
                metadata=metadata or {},
            )

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error creating prompt version: {e}")
            raise

    async def activate_version(
        self,
        name: str,
        version: int,
        cliente_id: Optional[UUID] = None,
    ) -> bool:
        """
        Activate a specific version (deactivates others).

        Args:
            name: Prompt name
            version: Version to activate
            cliente_id: Optional client ID

        Returns:
            True if successful
        """
        if not self.db_session:
            return False

        try:
            # Deactivate all versions
            versions = await self.list_versions(name, cliente_id, include_inactive=True)
            for v in versions:
                await self._set_active(name, v.version, cliente_id, False)

            # Activate specified version
            return await self._set_active(name, version, cliente_id, True)

        except Exception as e:
            logger.error(f"Error activating version: {e}")
            return False

    async def rollback(
        self,
        name: str,
        cliente_id: Optional[UUID] = None,
    ) -> Optional[PromptVersion]:
        """
        Rollback to the previous version.

        Args:
            name: Prompt name
            cliente_id: Optional client ID

        Returns:
            Activated PromptVersion or None
        """
        versions = await self.list_versions(name, cliente_id, include_inactive=True)

        if len(versions) < 2:
            logger.warning(f"Cannot rollback {name}: not enough versions")
            return None

        # Current active is versions[0], rollback to versions[1]
        previous = versions[1]

        success = await self.activate_version(name, previous.version, cliente_id)
        if success:
            previous.is_active = True
            return previous

        return None

    async def _set_active(
        self,
        name: str,
        version: int,
        cliente_id: Optional[UUID],
        active: bool,
    ) -> bool:
        """Set active status for a version."""
        if not self.db_session:
            return False

        try:
            from sqlmodel import select
            from vizu_models import PromptTemplate

            query = select(PromptTemplate).where(
                PromptTemplate.name == name,
                PromptTemplate.version == version,
            )
            if cliente_id:
                query = query.where(PromptTemplate.cliente_vizu_id == cliente_id)
            else:
                query = query.where(PromptTemplate.cliente_vizu_id == None)

            prompt = self.db_session.exec(query).first()
            if prompt:
                prompt.is_active = active
                self.db_session.add(prompt)
                self.db_session.commit()
                return True

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error setting active status: {e}")

        return False

    async def compare_versions(
        self,
        name: str,
        version_a: int,
        version_b: int,
        cliente_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Compare two versions of a prompt.

        Args:
            name: Prompt name
            version_a: First version
            version_b: Second version
            cliente_id: Optional client ID

        Returns:
            Comparison dict with differences
        """
        versions = await self.list_versions(name, cliente_id, include_inactive=True)

        prompt_a = next((v for v in versions if v.version == version_a), None)
        prompt_b = next((v for v in versions if v.version == version_b), None)

        if not prompt_a or not prompt_b:
            return {"error": "One or both versions not found"}

        # Simple diff
        lines_a = prompt_a.content.split("\n")
        lines_b = prompt_b.content.split("\n")

        return {
            "version_a": version_a,
            "version_b": version_b,
            "lines_a": len(lines_a),
            "lines_b": len(lines_b),
            "chars_a": len(prompt_a.content),
            "chars_b": len(prompt_b.content),
            "chars_diff": len(prompt_b.content) - len(prompt_a.content),
            "content_a": prompt_a.content,
            "content_b": prompt_b.content,
        }
