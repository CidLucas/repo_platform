import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
from vizu_models import ClienteVizu, ConfiguracaoNegocio
from sqlalchemy import text
import json
from datetime import datetime


def save_integration_config(
    db: Session,
    cliente_vizu_id: uuid.UUID,
    provider: str,
    config_type: str,
    client_id_encrypted: str,
    client_secret_encrypted: str,
    redirect_uri: str,
    scopes: list,
):
    """Upsert an integration config for a cliente_vizu."""
    stmt = text(
        """
        INSERT INTO integration_configs (
            cliente_vizu_id, provider, config_type,
            client_id_encrypted, client_secret_encrypted,
            redirect_uri, scopes, created_at, updated_at
        ) VALUES (
            :cliente_vizu_id, :provider, :config_type,
            :client_id_encrypted, :client_secret_encrypted,
            :redirect_uri, :scopes, now(), now()
        )
        ON CONFLICT (cliente_vizu_id, provider, config_type)
        DO UPDATE SET
            client_id_encrypted = EXCLUDED.client_id_encrypted,
            client_secret_encrypted = EXCLUDED.client_secret_encrypted,
            redirect_uri = EXCLUDED.redirect_uri,
            scopes = EXCLUDED.scopes,
            updated_at = now()
        RETURNING *;
        """
    )

    result = db.execute(
        stmt,
        {
            "cliente_vizu_id": str(cliente_vizu_id),
            "provider": provider,
            "config_type": config_type,
            "client_id_encrypted": client_id_encrypted,
            "client_secret_encrypted": client_secret_encrypted,
            "redirect_uri": redirect_uri,
            "scopes": json.dumps(scopes),
        },
    )
    db.commit()
    return result.fetchone()


def get_integration_config(db: Session, cliente_vizu_id: uuid.UUID, provider: str):
    stmt = text(
        "SELECT * FROM integration_configs WHERE cliente_vizu_id = :cliente_vizu_id AND provider = :provider LIMIT 1"
    )
    res = db.execute(
        stmt, {"cliente_vizu_id": str(cliente_vizu_id), "provider": provider}
    ).fetchone()
    return res


def save_integration_tokens(
    db: Session,
    cliente_vizu_id: uuid.UUID,
    provider: str,
    access_token_encrypted: str,
    refresh_token_encrypted: str | None,
    token_type: str | None,
    expires_at: datetime | None,
    scopes: list,
    metadata: dict | None = None,
    account_email: str | None = None,
    account_name: str | None = None,
    is_default: bool = False,
):
    """Save or update integration tokens for a specific account.

    If account_email is not provided, uses 'default@unknown.com' for backwards compatibility.
    If is_default is True and no other default exists, this becomes the default account.
    """
    # Use placeholder for legacy single-account usage
    if not account_email:
        account_email = "default@unknown.com"
        account_name = account_name or "Primary Account"
        is_default = True

    # If setting as default, clear other defaults first
    if is_default:
        clear_default_stmt = text("""
            UPDATE integration_tokens
            SET is_default = false
            WHERE cliente_vizu_id = :cliente_vizu_id AND provider = :provider AND is_default = true
        """)
        db.execute(
            clear_default_stmt,
            {"cliente_vizu_id": str(cliente_vizu_id), "provider": provider},
        )

    stmt = text(
        """
        INSERT INTO integration_tokens (
            cliente_vizu_id, provider,
            access_token_encrypted, refresh_token_encrypted,
            token_type, expires_at, scopes, metadata,
            account_email, account_name, is_default,
            created_at, updated_at
        ) VALUES (
            :cliente_vizu_id, :provider,
            :access_token_encrypted, :refresh_token_encrypted,
            :token_type, :expires_at, :scopes, :metadata,
            :account_email, :account_name, :is_default,
            now(), now()
        )
        ON CONFLICT (cliente_vizu_id, provider, account_email)
        DO UPDATE SET
            access_token_encrypted = EXCLUDED.access_token_encrypted,
            refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
            token_type = EXCLUDED.token_type,
            expires_at = EXCLUDED.expires_at,
            scopes = EXCLUDED.scopes,
            metadata = EXCLUDED.metadata,
            account_name = EXCLUDED.account_name,
            is_default = EXCLUDED.is_default,
            updated_at = now()
        RETURNING *;
        """
    )

    result = db.execute(
        stmt,
        {
            "cliente_vizu_id": str(cliente_vizu_id),
            "provider": provider,
            "access_token_encrypted": access_token_encrypted,
            "refresh_token_encrypted": refresh_token_encrypted,
            "token_type": token_type,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "scopes": json.dumps(scopes),
            "metadata": json.dumps(metadata) if metadata is not None else None,
            "account_email": account_email,
            "account_name": account_name,
            "is_default": is_default,
        },
    )
    db.commit()
    return result.fetchone()


def get_integration_tokens(
    db: Session,
    cliente_vizu_id: uuid.UUID,
    provider: str,
    account_email: str | None = None,
):
    """Get integration tokens for a specific account or the default account.

    If account_email is provided, fetches that specific account.
    Otherwise, fetches the default account (is_default=true) or falls back to any account.
    """
    if account_email:
        stmt = text(
            """SELECT * FROM integration_tokens
               WHERE cliente_vizu_id = :cliente_vizu_id
               AND provider = :provider
               AND account_email = :account_email
               LIMIT 1"""
        )
        res = db.execute(
            stmt,
            {
                "cliente_vizu_id": str(cliente_vizu_id),
                "provider": provider,
                "account_email": account_email,
            },
        ).fetchone()
    else:
        # Try default account first, then fall back to any account
        stmt = text(
            """SELECT * FROM integration_tokens
               WHERE cliente_vizu_id = :cliente_vizu_id
               AND provider = :provider
               ORDER BY is_default DESC, created_at ASC
               LIMIT 1"""
        )
        res = db.execute(
            stmt,
            {
                "cliente_vizu_id": str(cliente_vizu_id),
                "provider": provider,
            },
        ).fetchone()
    return res


def list_integration_accounts(
    db: Session,
    cliente_vizu_id: uuid.UUID,
    provider: str,
):
    """List all connected accounts for a cliente/provider."""
    stmt = text(
        """SELECT id, account_email, account_name, is_default, expires_at, scopes, created_at
           FROM integration_tokens
           WHERE cliente_vizu_id = :cliente_vizu_id
           AND provider = :provider
           ORDER BY is_default DESC, account_email ASC"""
    )
    res = db.execute(
        stmt,
        {
            "cliente_vizu_id": str(cliente_vizu_id),
            "provider": provider,
        },
    ).fetchall()
    return res


def set_default_account(
    db: Session,
    cliente_vizu_id: uuid.UUID,
    provider: str,
    account_email: str,
):
    """Set a specific account as the default for a cliente/provider."""
    # Clear existing default
    clear_stmt = text("""
        UPDATE integration_tokens
        SET is_default = false
        WHERE cliente_vizu_id = :cliente_vizu_id AND provider = :provider
    """)
    db.execute(
        clear_stmt, {"cliente_vizu_id": str(cliente_vizu_id), "provider": provider}
    )

    # Set new default
    set_stmt = text("""
        UPDATE integration_tokens
        SET is_default = true
        WHERE cliente_vizu_id = :cliente_vizu_id
        AND provider = :provider
        AND account_email = :account_email
        RETURNING *
    """)
    result = db.execute(
        set_stmt,
        {
            "cliente_vizu_id": str(cliente_vizu_id),
            "provider": provider,
            "account_email": account_email,
        },
    ).fetchone()
    db.commit()
    return result


def revoke_integration(
    db: Session,
    cliente_vizu_id: uuid.UUID,
    provider: str,
    account_email: str | None = None,
):
    """Revoke integration for a specific account or all accounts.

    If account_email is provided, only that account is revoked.
    Otherwise, all accounts and configs for the provider are revoked.
    """
    if account_email:
        stmt1 = text("""
            DELETE FROM integration_tokens
            WHERE cliente_vizu_id = :cliente_vizu_id
            AND provider = :provider
            AND account_email = :account_email
        """)
        db.execute(
            stmt1,
            {
                "cliente_vizu_id": str(cliente_vizu_id),
                "provider": provider,
                "account_email": account_email,
            },
        )
    else:
        # Revoke all accounts for this provider
        stmt1 = text(
            "DELETE FROM integration_tokens WHERE cliente_vizu_id = :cliente_vizu_id AND provider = :provider"
        )
        stmt2 = text(
            "DELETE FROM integration_configs WHERE cliente_vizu_id = :cliente_vizu_id AND provider = :provider"
        )
        db.execute(
            stmt1, {"cliente_vizu_id": str(cliente_vizu_id), "provider": provider}
        )
        db.execute(
            stmt2, {"cliente_vizu_id": str(cliente_vizu_id), "provider": provider}
        )
    db.commit()
    return True


def get_cliente_vizu_by_api_key(db: Session, api_key: str):
    """Busca cliente pela API Key (Usada na autenticação inicial)"""
    statement = select(ClienteVizu).where(ClienteVizu.api_key == api_key)
    return db.execute(statement).scalars().first()


def get_cliente_vizu_by_id(db: Session, cliente_id: uuid.UUID):
    """Busca cliente pelo ID trazendo a configuração junto (Eager Load)."""
    statement = select(ClienteVizu).where(ClienteVizu.id == cliente_id)
    return db.execute(statement).scalars().first()


def get_configuracao_negocio(db: Session, cliente_id: uuid.UUID):
    """Busca as configurações de negócio de um cliente"""
    # Transitional helper: query legacy configuracao_negocio by cliente_vizu_id
    statement = select(ConfiguracaoNegocio).where(
        ConfiguracaoNegocio.cliente_vizu_id == cliente_id
    )
    return db.execute(statement).scalars().first()
