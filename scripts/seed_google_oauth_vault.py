#!/usr/bin/env python3
"""
Seed platform-level Google OAuth credentials into Supabase Vault.

Stores GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET as encrypted secrets
in Supabase Vault, accessible via the get_platform_google_oauth_config() RPC.

Prerequisites:
    - Supabase Vault extension enabled (supabase/migrations/20260203_vault_credential_storage.sql)
    - RPC function created (supabase/migrations/20260316_google_oauth_vault_rpc.sql)
    - Environment: SUPABASE_URL, SUPABASE_SERVICE_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

Usage:
    # From repo root, with .env loaded:
    python scripts/seed_google_oauth_vault.py

    # Or pass credentials directly:
    python scripts/seed_google_oauth_vault.py \\
        --client-id YOUR_CLIENT_ID \\
        --client-secret YOUR_CLIENT_SECRET

    # Dry-run (show what would be stored, without writing):
    python scripts/seed_google_oauth_vault.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "libs" / "vizu_supabase_client" / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

from vizu_supabase_client import get_supabase_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

VAULT_SECRETS = [
    {
        "name": "google_oauth_client_id",
        "description": "Platform-level Google OAuth client ID",
        "env_var": "GOOGLE_CLIENT_ID",
    },
    {
        "name": "google_oauth_client_secret",
        "description": "Platform-level Google OAuth client secret",
        "env_var": "GOOGLE_CLIENT_SECRET",
    },
]


def _upsert_vault_secret(client, name: str, secret: str, description: str) -> str:
    """Insert or update a Vault secret via store_credential_in_vault-style SQL.

    Uses the RPC pattern: check for existing secret by name, update or create.
    """
    result = client.rpc(
        "store_vault_secret",
        {"p_name": name, "p_secret": secret, "p_description": description},
    ).execute()
    return result.data


def main():
    parser = argparse.ArgumentParser(description="Seed Google OAuth credentials into Supabase Vault")
    parser.add_argument("--client-id", help="Google OAuth client ID (overrides GOOGLE_CLIENT_ID env)")
    parser.add_argument(
        "--client-secret", help="Google OAuth client secret (overrides GOOGLE_CLIENT_SECRET env)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be stored without writing")
    args = parser.parse_args()

    values = {}
    for secret_def in VAULT_SECRETS:
        cli_key = secret_def["env_var"].lower().replace("google_", "")  # client_id or client_secret
        cli_val = getattr(args, cli_key.replace("-", "_"), None)
        env_val = os.getenv(secret_def["env_var"])
        value = cli_val or env_val

        if not value:
            logger.error(
                f"Missing {secret_def['env_var']}. "
                f"Set it in .env or pass --{cli_key.replace('_', '-')}"
            )
            sys.exit(1)

        values[secret_def["name"]] = value

    if args.dry_run:
        logger.info("DRY RUN — would store the following Vault secrets:")
        for secret_def in VAULT_SECRETS:
            val = values[secret_def["name"]]
            masked = val[:8] + "..." + val[-4:] if len(val) > 16 else "***"
            logger.info(f"  {secret_def['name']}: {masked} ({secret_def['description']})")
        return

    client = get_supabase_client()

    # Create the upsert helper function if it doesn't exist yet.
    # This is a one-time bootstrap; the migration should have created it.
    # We use raw RPC to call vault functions through a helper.
    for secret_def in VAULT_SECRETS:
        name = secret_def["name"]
        secret_value = values[name]
        description = secret_def["description"]

        try:
            # Use the store_vault_secret RPC (created below in bootstrap)
            result = client.rpc(
                "store_vault_secret",
                {"p_name": name, "p_secret": secret_value, "p_description": description},
            ).execute()
            logger.info(f"✓ Stored '{name}' in Vault (id: {result.data})")
        except Exception as e:
            logger.error(f"✗ Failed to store '{name}': {e}")
            sys.exit(1)

    logger.info("Done. Platform Google OAuth credentials are now in Supabase Vault.")
    logger.info("The app will use them as fallback when no per-client config exists.")


if __name__ == "__main__":
    main()
