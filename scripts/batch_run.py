#!/usr/bin/env python3
"""
Batch run script to generate multiple traces in Langfuse.
Sends various messages to the chat endpoint to create diverse traces.
"""
import os
import time
from datetime import datetime

import psycopg2
import requests

# Configuration - detect if running in container or host
IS_CONTAINER = os.path.exists("/.dockerenv") or os.environ.get("PYTHONPATH", "").startswith("/app")

if IS_CONTAINER:
    API_URL = "http://localhost:8000/chat"  # Inside container, service listens on 8000
    DB_HOST = "postgres"
else:
    API_URL = "http://localhost:8003/chat"  # From host, mapped to 8003
    DB_HOST = "localhost"

DB_CONFIG = {
    "host": DB_HOST,
    "port": 5432,
    "database": "vizu_db",
    "user": "user",
    "password": "password"
}

# Diverse test messages to generate varied traces
TEST_MESSAGES = [
    "Olá, quais serviços você oferece?",
    "Qual o horário de funcionamento?",
    "Como faço para agendar um horário?",
    "Quanto custa uma hidratação capilar?",
    "Vocês trabalham aos sábados?",
    "Quero marcar um corte de cabelo para amanhã",
    "Vocês aceitam cartão de crédito?",
    "Qual a especialidade do salão?",
    "Tem estacionamento no local?",
    "Quais produtos vocês usam nos tratamentos?",
]


def get_api_key():
    """Get the first client API key from the database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT api_key, nome_empresa FROM cliente_vizu LIMIT 1;")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return result[0], result[1]
        return None, None
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None, None


def send_message(api_key: str, message: str, session_id: str) -> dict:
    """Send a message to the chat endpoint."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    payload = {
        "message": message,
        "session_id": session_id
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout (120s)"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def main():
    print("🚀 Langfuse Batch Run - Generating Traces")
    print("=" * 50)

    # Get API key
    api_key, client_name = get_api_key()
    if not api_key:
        print("❌ Could not get API key from database")
        return

    print(f"✅ Using client: {client_name}")
    print(f"📍 API URL: {API_URL}")
    print(f"📝 Messages to send: {len(TEST_MESSAGES)}")
    print("=" * 50)

    successful = 0
    failed = 0

    for i, message in enumerate(TEST_MESSAGES, 1):
        session_id = f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{i}"
        print(f"\n[{i}/{len(TEST_MESSAGES)}] Session: {session_id}")
        print(f"📤 Message: {message}")

        start_time = time.time()
        result = send_message(api_key, message, session_id)
        elapsed = time.time() - start_time

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            failed += 1
        else:
            response_preview = result.get("response", "")[:100]
            print(f"✅ Response ({elapsed:.1f}s): {response_preview}...")
            successful += 1

        # Small delay between requests
        if i < len(TEST_MESSAGES):
            time.sleep(1)

    print("\n" + "=" * 50)
    print(f"📊 Results: {successful} successful, {failed} failed")
    print("🔍 Check traces at: http://localhost:3000")
    print("=" * 50)


if __name__ == "__main__":
    main()
