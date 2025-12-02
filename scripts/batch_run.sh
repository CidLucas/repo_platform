#!/bin/bash
# Batch run script to test Ollama Cloud response times
# Generates traces in Langfuse for analysis

API_URL="http://localhost:8003/chat"

# Get API key from database via docker
API_KEY=$(docker exec vizu_atendente_core python /app/scripts/get_api_key.py 2>/dev/null)

if [ -z "$API_KEY" ]; then
    echo "❌ Could not get API key. Run 'make seed' first."
    exit 1
fi

echo "🚀 Ollama Cloud Batch Run - Testing Response Times"
echo "=================================================="
echo "📍 API URL: $API_URL"
echo "🔑 Using API Key: ${API_KEY:0:8}..."
echo "=================================================="

# Test messages
MESSAGES=(
    "Olá, quais serviços você oferece?"
    "Qual o horário de funcionamento?"
    "Como faço para agendar um horário?"
    "Quanto custa uma hidratação capilar?"
    "Vocês trabalham aos sábados?"
    "Quero marcar um corte de cabelo para amanhã"
    "Vocês aceitam cartão de crédito?"
    "Qual a especialidade do salão?"
    "Tem estacionamento no local?"
    "Quais produtos vocês usam nos tratamentos?"
)

successful=0
failed=0
total_time=0

for i in "${!MESSAGES[@]}"; do
    msg="${MESSAGES[$i]}"
    num=$((i + 1))
    session_id="batch-$(date +%Y%m%d-%H%M%S)-$num"

    echo ""
    echo "[$num/${#MESSAGES[@]}] Session: $session_id"
    echo "📤 Message: $msg"

    start_time=$(python3 -c "import time; print(time.time())")

    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "X-API-KEY: $API_KEY" \
        -d "{\"message\": \"$msg\", \"session_id\": \"$session_id\"}" \
        --max-time 120 2>&1)

    end_time=$(python3 -c "import time; print(time.time())")
    elapsed=$(python3 -c "print(f'{$end_time - $start_time:.1f}')")

    # Check for error
    if echo "$response" | grep -q '"error"'; then
        echo "❌ Error: $response"
        ((failed++))
    elif echo "$response" | grep -q '"detail"'; then
        echo "❌ Error: $response"
        ((failed++))
    else
        # Get model_used and response preview
        model_used=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('model_used','unknown'))" 2>/dev/null || echo "unknown")
        response_text=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','')[:80])" 2>/dev/null || echo "...")
        echo "✅ Response (${elapsed}s) [model: $model_used]: $response_text..."
        ((successful++))
        total_time=$(python3 -c "print($total_time + $elapsed)")
    fi

    # Small delay between requests
    sleep 1
done

echo ""
echo "=================================================="
echo "📊 Results: $successful successful, $failed failed"
if [ $successful -gt 0 ]; then
    avg_time=$(python3 -c "print(f'{$total_time / $successful:.1f}')")
    echo "⏱️  Average response time: ${avg_time}s"
fi
echo "🔍 Check traces at: http://localhost:3000"
echo "=================================================="
