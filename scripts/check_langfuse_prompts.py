#!/usr/bin/env python3
"""Check Langfuse prompts status."""

import requests
from base64 import b64encode

PUBLIC_KEY = "pk-lf-c64e4914-b8ab-426d-a5ea-14989b564e13"
SECRET_KEY = "sk-lf-dc053e58-e9e3-4822-abfe-89421ca9c2d4"
BASE_URL = "https://us.cloud.langfuse.com"

auth_token = b64encode(f"{PUBLIC_KEY}:{SECRET_KEY}".encode()).decode()
HEADERS = {"Authorization": f"Basic {auth_token}"}


def main():
    # List all prompts with pagination
    resp = requests.get(f"{BASE_URL}/api/public/v2/prompts?limit=50", headers=HEADERS)
    data = resp.json()

    print("All prompts in Langfuse:")
    print("=" * 70)

    for p in data.get("data", []):
        name = p.get("name", "N/A")
        versions = p.get("versions", [])
        labels = p.get("labels", [])
        print(f"  {name}")
        print(f"    Versions: {versions}, Labels: {labels}")

    print("\n" + "=" * 70)

    # Check specific sql prompts
    for prompt_name in ["sql/analytics-v2-schema", "sql/analytics-v2-guide", "tool/sql-agent-prefix"]:
        encoded_name = prompt_name.replace("/", "%2F")
        resp = requests.get(f"{BASE_URL}/api/public/v2/prompts/{encoded_name}", headers=HEADERS)

        print(f"\n{prompt_name}: {resp.status_code}")
        if resp.ok:
            data = resp.json()
            prompt_text = data.get("prompt", "")
            print(f"  Content preview: {prompt_text[:150]}...")
        else:
            print(f"  Error: {resp.text[:200]}")


if __name__ == "__main__":
    main()
