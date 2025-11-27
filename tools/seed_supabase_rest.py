"""Seed Supabase directly using the PostgREST REST API (/rest/v1).

This script uses the `SUPABASE_URL` and `SUPABASE_API_KEY` (service role key)
to insert rows into `cliente_vizu` and `configuracao_negocio` tables.

Usage (zsh):
  export SUPABASE_URL="https://<project>.supabase.co"
  export SUPABASE_API_KEY="<service-role-key>"
  python tools/seed_supabase_rest.py

Notes:
- The script will check for existing clients by `nome_empresa` and skip
  creation if found (idempotent). It will still try to create/update the
  `configuracao_negocio` for that client.
- Uses `Prefer: return=representation` to obtain inserted rows when supported.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, Any, Optional

import requests
import uuid

# Basic personas copied from the repo's evaluation suite to keep seeds consistent
PERSONAS = [
    {"nome_empresa": "Oficina Mendes", "tipo_cliente": "EXTERNO", "tier": "SME"},
    {"nome_empresa": "Studio J", "tipo_cliente": "EXTERNO", "tier": "SME"},
    {"nome_empresa": "Casa com Alma", "tipo_cliente": "EXTERNO", "tier": "SME"},
    {"nome_empresa": "Consultório Odontológico Dra. Beatriz Almeida", "tipo_cliente": "EXTERNO", "tier": "SME"},
    {"nome_empresa": "Marcos Eletricista", "tipo_cliente": "EXTERNO", "tier": "SME"},
]

PERSONA_CONFIGS = {
    "Oficina Mendes": {
        "prompt_base": "Você é um atendente virtual da 'Oficina Mendes'. Seja direto, profissional e confiável.",
        "horario_funcionamento": {"seg-sex": "08:00-18:00", "sab": "08:00-12:00"},
        "ferramenta_rag_habilitada": False,
        "ferramenta_sql_habilitada": False,
    },
    "Studio J": {
        "prompt_base": "Você é o assistente virtual do 'Studio J'...",
        "horario_funcionamento": {"ter-sex": "10:00-20:00", "sab": "09:00-18:00"},
        "ferramenta_rag_habilitada": False,
        "ferramenta_sql_habilitada": False,
    },
    "Casa com Alma": {
        "prompt_base": "Você é um consultor virtual da 'Casa com Alma'...",
        "horario_funcionamento": {"seg-sex": "09:00-17:00"},
        "ferramenta_rag_habilitada": True,
        "ferramenta_sql_habilitada": False,
    },
    "Consultório Odontológico Dra. Beatriz Almeida": {
        "prompt_base": "Você é a secretária virtual do Consultório...",
        "horario_funcionamento": {"seg-sex": "08:30-18:30"},
        "ferramenta_rag_habilitada": False,
        "ferramenta_sql_habilitada": True,
    },
    "Marcos Eletricista": {
        "prompt_base": "Você é o assistente técnico de Marcos Eletricista...",
        "horario_funcionamento": {"seg-dom": "08:00-22:00"},
        "ferramenta_rag_habilitada": True,
        "ferramenta_sql_habilitada": True,
    },
}


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        print(f"Error: environment variable {name} not set", file=sys.stderr)
        sys.exit(1)
    return v


def build_headers(api_key: str) -> Dict[str, str]:
    # Use both Authorization and apikey headers as recommended by Supabase for admin calls
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Ask PostgREST to return the created row
        "Prefer": "return=representation",
    }


def find_client(base: str, headers: Dict[str, str], nome_empresa: str) -> Optional[Dict[str, Any]]:
    url = f"{base}/rest/v1/cliente_vizu"
    params = {"select": "id,api_key,nome_empresa", "nome_empresa": f"eq.{nome_empresa}"}
    # Note: requests will URL-encode params automatically
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code != 200:
        print(f"Warning: search client returned {resp.status_code}: {resp.text}")
        return None
    data = resp.json()
    return data[0] if data else None


def create_client(base: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = f"{base}/rest/v1/cliente_vizu"
    # If the DB lacks server-side defaults for `id` or `api_key`, provide them
    body = payload.copy()
    if "id" not in body:
        body["id"] = str(uuid.uuid4())
    if "api_key" not in body:
        body["api_key"] = str(uuid.uuid4())

    resp = requests.post(url, headers=headers, json=body, timeout=10)
    if resp.status_code not in (200, 201):
        print(f"Failed creating client ({payload.get('nome_empresa')}): {resp.status_code} {resp.text}")
        return None
    # PostgREST returns a list of created rows
    try:
        return resp.json()[0]
    except Exception:
        return None


def upsert_config(base: str, headers: Dict[str, str], cfg: Dict[str, Any]) -> bool:
    url = f"{base}/rest/v1/configuracao_negocio"
    # Try to insert; if conflict on cliente_vizu_id occurs, perform a PATCH
    resp = requests.post(url, headers=headers, json=cfg, timeout=10)
    if resp.status_code in (200, 201):
        return True
    # If conflict, try patch by cliente_vizu_id
    if resp.status_code == 409:
        cliente_id = cfg.get("cliente_vizu_id")
        patch_url = f"{url}?cliente_vizu_id=eq.{cliente_id}"
        resp2 = requests.patch(patch_url, headers=headers, json=cfg, timeout=10)
        return resp2.status_code in (200, 204)
    print(f"Failed creating/updating config for {cfg.get('cliente_vizu_id')}: {resp.status_code} {resp.text}")
    return False


def main() -> None:
    supabase_url = "https://haruewffnubdgyofftut.supabase.co"

    if supabase_url and not supabase_url.startswith("http"):
        supabase_url = f"https://{supabase_url}"
    if not supabase_url:
        print("Error: set SUPABASE_URL (e.g. https://<project>.supabase.co)", file=sys.stderr)
        sys.exit(1)

    api_key = "sb_secret_WDttwpfT6_SAAm7xYYwpjA_Wf6_oSxo"
    headers = build_headers(api_key)

    print("Seeding Supabase at:", supabase_url)

    results = {}
    for persona in PERSONAS:
        name = persona["nome_empresa"]
        print(f"\nProcessing: {name}")

        existing = find_client(supabase_url, headers, name)
        if existing:
            print(f" - Found existing client: {existing.get('id')} (skipping create)")
            client_id = existing.get("id")
            api_key_val = existing.get("api_key")
        else:
            created = create_client(supabase_url, headers, persona)
            if not created:
                print(f" - ERROR: could not create client {name}")
                continue
            client_id = created.get("id")
            api_key_val = created.get("api_key")
            print(f" - Created client id={client_id}")

        # Create/update configuration if available
        cfg = PERSONA_CONFIGS.get(name)
        if cfg:
            cfg_body = cfg.copy()
            cfg_body["cliente_vizu_id"] = client_id
            ok = upsert_config(supabase_url, headers, cfg_body)
            print(f" - Config {'upserted' if ok else 'failed'} for client {client_id}")

        results[name] = {"id": client_id, "api_key": api_key_val}

    print("\nSeed complete. Summary:")
    for k, v in results.items():
        print(f" - {k}: id={v.get('id')} api_key={v.get('api_key')}")


if __name__ == "__main__":
    main()
