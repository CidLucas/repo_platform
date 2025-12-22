"""
Google Secret Manager integration for secure credential storage.

This module provides a high-level interface for storing and managing
sensitive credentials using Google Cloud Secret Manager.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SecretManager:
    """
    Google Secret Manager client for storing and retrieving sensitive credentials.

    Provides async methods for:
    - Storing secrets with automatic versioning
    - Deleting secrets (for rollback scenarios)
    - Retrieving secret values
    """

    def __init__(self, project_id: str | None = None):
        """
        Initialize the Secret Manager client.

        Args:
            project_id: GCP project ID. If not provided, uses default from environment.
        """
        self.project_id = project_id
        self._client = None

    def _get_client(self):
        """Lazily initialize the Secret Manager client."""
        if self._client is None:
            try:
                from google.cloud import secretmanager
                self._client = secretmanager.SecretManagerServiceClient()
            except ImportError:
                raise ImportError(
                    "google-cloud-secretmanager is required but not installed. "
                    "Install it with: pip install google-cloud-secretmanager"
                )
        return self._client

    async def store_secret(self, client_id: str, credentials: dict[str, Any]) -> str:
        """
        Store credentials in Google Secret Manager.

        Creates a new secret or adds a new version if the secret already exists.
        The secret name is automatically generated from the client_id.

        Args:
            client_id: Unique identifier for the client (used in secret name)
            credentials: Dictionary of sensitive credential data to store

        Returns:
            The full secret version name (e.g., "projects/123/secrets/vizu-creds-abc/versions/1")

        Raises:
            Exception: If secret creation fails
        """
        client = self._get_client()

        # Generate a deterministic secret name from client_id
        secret_id = f"vizu-creds-{client_id}".replace("_", "-").lower()

        if not self.project_id:
            # Try to get project from default environment
            import google.auth
            _, project = google.auth.default()
            self.project_id = project

        parent = f"projects/{self.project_id}"
        secret_path = f"{parent}/secrets/{secret_id}"

        # Convert credentials dict to JSON string
        payload = json.dumps(credentials).encode("utf-8")

        try:
            # Try to create the secret first
            try:
                secret = client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {
                            "replication": {"automatic": {}},
                        },
                    }
                )
                logger.info(f"Created new secret: {secret.name}")
            except Exception as create_error:
                # Secret might already exist, which is fine
                if "already exists" not in str(create_error).lower():
                    raise
                logger.debug(f"Secret {secret_id} already exists, adding new version")

            # Add a new version with the credential data
            version = client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": payload},
                }
            )

            logger.info(f"Stored secret version: {version.name}")
            return version.name

        except Exception as e:
            logger.error(f"Failed to store secret for client {client_id}: {e}")
            raise Exception(f"Failed to store secret in Secret Manager: {e}")

    async def delete_secret(self, secret_id: str) -> bool:
        """
        Delete a secret from Google Secret Manager.

        This is typically used for rollback scenarios when credential
        storage fails after the secret was created.

        Args:
            secret_id: Full secret version name or secret name to delete

        Returns:
            True if deletion was successful, False otherwise

        Note:
            If secret_id is a version name, only that version is destroyed.
            If it's a secret name, the entire secret (all versions) is deleted.
        """
        client = self._get_client()

        try:
            # Check if this is a version name or secret name
            if "/versions/" in secret_id:
                # This is a version name - destroy just this version
                client.destroy_secret_version(request={"name": secret_id})
                logger.info(f"Destroyed secret version: {secret_id}")
            else:
                # This is a secret name - delete the entire secret
                client.delete_secret(request={"name": secret_id})
                logger.info(f"Deleted secret: {secret_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete secret {secret_id}: {e}")
            return False

    async def get_secret(self, secret_name: str) -> dict[str, Any]:
        """
        Retrieve and decode a secret from Google Secret Manager.

        Args:
            secret_name: Full secret version name or secret name (uses latest version)

        Returns:
            Dictionary containing the decoded secret data

        Raises:
            Exception: If secret retrieval or JSON decoding fails
        """
        client = self._get_client()

        try:
            # If no version specified, append /versions/latest
            if "/versions/" not in secret_name:
                secret_name = f"{secret_name}/versions/latest"

            response = client.access_secret_version(request={"name": secret_name})
            payload = response.payload.data.decode("utf-8")

            return json.loads(payload)

        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise Exception(f"Failed to retrieve secret from Secret Manager: {e}")
