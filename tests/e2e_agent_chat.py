"""
E2E manual test: envia mensagem para um agente via agent_api e imprime a resposta.
Usage:
  python3 tests/e2e_agent_chat.py --slug data-analyst --msg "Gere um gráfico de barras com dados de exemplo de vendas por produto"
"""
import argparse
import json
import sys
import os
import subprocess
import uuid

BASE_URL = "http://localhost:8003/v1"

def get_token() -> str:
    result = subprocess.run(
        ["python3", "tests/agent_routing/get_test_token.py"],
        capture_output=True, text=True
    )
    token_path = "/tmp/blu_test_jwt.txt"
    with open(token_path) as f:
        return f.read().strip()

KNOWN_AGENTS = {
    "data-analyst": ("a0a6fe63-9033-421f-8fec-ca5a16f307a6", "Data Analyst"),
    "documentos": ("59bda36d-adab-4fe6-a38b-b6b16b1c337c", "Agente de Documentos"),
    "synthesis":  ("09829bcc-feea-4936-9db4-9c87082327c4", "Synthesis Agent"),
}

def get_agent_id(slug: str, token: str) -> str:
    if slug in KNOWN_AGENTS:
        agent_id, name = KNOWN_AGENTS[slug]
        print(f"[agent] {name} (id={agent_id})")
        return agent_id
    raise ValueError(f"Agent '{slug}' not in KNOWN_AGENTS. Known: {list(KNOWN_AGENTS)}")

def create_session(agent_id: str, token: str) -> str:
    import urllib.request, urllib.error
    data = json.dumps({"agent_catalog_id": agent_id}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/sessions",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
    session_id = body["id"]
    print(f"[session] created: {session_id}")
    return session_id

def chat(session_id: str, message: str, token: str):
    import urllib.request
    data = json.dumps({"message": message, "session_id": session_id}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/sessions/{session_id}/chat/agent",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    print(f"\n[chat] enviando: {message}\n{'─'*60}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        buffer = b""
        while True:
            chunk = resp.read(1024)
            if not chunk:
                break
            buffer += chunk
            while b"\n\n" in buffer:
                event_raw, buffer = buffer.split(b"\n\n", 1)
                for line in event_raw.decode("utf-8", errors="replace").split("\n"):
                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        try:
                            evt = json.loads(payload)
                        except json.JSONDecodeError:
                            print(f"  [raw] {payload}")
                            continue
                        event_type = evt.get("event") or evt.get("type", "")
                        if event_type == "token":
                            print(evt.get("data", evt.get("content", "")), end="", flush=True)
                        elif event_type == "tool_call":
                            print(f"\n  [🔧 tool] {evt.get('tool_name','?')}({json.dumps(evt.get('args',{}))[:120]})")
                        elif event_type == "tool_result":
                            result_preview = str(evt.get("result", ""))[:200]
                            print(f"  [✓ result] {result_preview}")
                        elif event_type in ("final", "done", "end"):
                            print(f"\n{'─'*60}\n[done]")
                        elif event_type == "error":
                            print(f"\n[❌ ERROR] {evt.get('message', evt)}")
                        else:
                            # outros eventos: mostrar resumo
                            print(f"\n  [{event_type}] {str(evt)[:200]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", default="data-analyst")
    parser.add_argument("--msg", default="Gere um gráfico de barras com dados de exemplo de vendas por produto (A, B, C) e me mostre o HTML gerado.")
    args = parser.parse_args()

    token = get_token()
    agent_id = get_agent_id(args.slug, token)
    session_id = create_session(agent_id, token)
    chat(session_id, args.msg, token)
