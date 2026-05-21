#!/usr/bin/env python3
"""
Generate a short-lived Supabase access token for a test user.
Writes the token to /tmp/blu_test_jwt.txt

Usage:
    python get_test_token.py
    python get_test_token.py --email other@test.com
"""
import argparse
import os
import sys
from pathlib import Path

# Load repo .env
repo_root = Path(__file__).parents[2]
env_file = repo_root / ".env"
with open(env_file) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import requests
from supabase import create_client

def get_token(email: str) -> str:
    url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(url, service_key)

    # Generate magic link
    result = client.auth.admin.generate_link({
        "type": "magiclink",
        "email": email,
    })
    hashed_token = result.properties.hashed_token

    # Exchange for access_token
    resp = requests.post(
        f"{url}/auth/v1/verify",
        json={"type": "magiclink", "token_hash": hashed_token},
        headers={"apikey": service_key, "Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--email", default="lucascid@poli.ufrj.br")
    args = p.parse_args()

    token = get_token(args.email)
    out = Path("/tmp/blu_test_jwt.txt")
    out.write_text(token)
    print(f"Token saved to {out}")
    print(f"Preview: {token[:40]}...")
    print(f"\nexport BLU_JWT={token}")
