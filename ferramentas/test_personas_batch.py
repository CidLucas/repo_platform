#!/usr/bin/env python3
"""
Test Personas batch runner.
Sends test messages from CSV to each persona's API to validate RAG responses.
"""
import requests
import csv
import time
import os
from datetime import datetime

# Configuration - detect if running in container or host
IS_CONTAINER = os.path.exists("/.dockerenv") or os.environ.get("PYTHONPATH", "").startswith("/app")

if IS_CONTAINER:
    API_URL = "http://localhost:8000/chat"
else:
    API_URL = "http://localhost:8003/chat"

# CSV file with test messages
CSV_FILE = os.environ.get("CSV_FILE", "/app/ferramentas/test_personas.csv")


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
    print("🚀 Test Personas Batch Run")
    print("=" * 70)
    print(f"📍 API URL: {API_URL}")
    print(f"📄 CSV File: {CSV_FILE}")
    print("=" * 70)

    # Read CSV
    messages = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages.append(row)

    print(f"📝 Messages to send: {len(messages)}")
    print("=" * 70)

    successful = 0
    failed = 0
    results = []
    current_api_key = None

    for i, row in enumerate(messages, 1):
        api_key = row['api_key']
        message = row['mensagem']

        # Print separator when switching personas
        if api_key != current_api_key:
            current_api_key = api_key
            print(f"\n{'='*70}")
            print(f"🔑 Switching to API Key: {api_key[:8]}...")
            print("=" * 70)

        session_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{i}"
        print(f"\n[{i}/{len(messages)}] Session: {session_id}")
        print(f"📤 Message: {message[:80]}...")

        start_time = time.time()
        result = send_message(api_key, message, session_id)
        elapsed = time.time() - start_time

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            failed += 1
            results.append({
                "api_key": api_key[:8],
                "message": message[:50],
                "status": "FAILED",
                "error": result["error"],
                "time": elapsed
            })
        else:
            response_preview = result.get("response", "")[:150]
            print(f"✅ Response ({elapsed:.1f}s):")
            print(f"   {response_preview}...")
            successful += 1
            results.append({
                "api_key": api_key[:8],
                "message": message[:50],
                "status": "OK",
                "response": response_preview,
                "time": elapsed
            })

        # Small delay between requests
        if i < len(messages):
            time.sleep(1)

    print("\n" + "=" * 70)
    print(f"📊 RESULTS SUMMARY")
    print("=" * 70)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {successful/(successful+failed)*100:.1f}%")
    print(f"🔍 Check traces at Langfuse")
    print("=" * 70)


if __name__ == "__main__":
    main()
