#!/bin/bash
# Quick diagnostic script to check if analytics_v2 views exist

set -e

echo "🔍 Checking analytics_v2 schema views in Supabase..."
echo ""

# Extract DB connection from .env
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    exit 1
fi

source .env

if [ -z "$SUPABASE_DB_URL" ]; then
    echo "❌ SUPABASE_DB_URL not set in .env"
    exit 1
fi

# Check if views exist
echo "Checking for required views..."
echo ""

VIEWS=("v_resumo_dashboard" "v_series_temporal" "v_ultimos_pedidos" "v_produtos_por_cliente")

for view in "${VIEWS[@]}"; do
    EXISTS=$(psql "$SUPABASE_DB_URL" -t -c "
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.views
            WHERE table_schema = 'analytics_v2'
            AND table_name = '$view'
        );
    " 2>/dev/null | tr -d ' ')

    if [ "$EXISTS" = "t" ]; then
        echo "✅ $view exists"
    else
        echo "❌ $view MISSING"
    fi
done

echo ""
echo "Checking analytics_v2 schema..."
SCHEMA_EXISTS=$(psql "$SUPABASE_DB_URL" -t -c "
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.schemata
        WHERE schema_name = 'analytics_v2'
    );
" 2>/dev/null | tr -d ' ')

if [ "$SCHEMA_EXISTS" = "t" ]; then
    echo "✅ analytics_v2 schema exists"
else
    echo "❌ analytics_v2 schema MISSING"
fi

echo ""
echo "📊 To fix missing views, run:"
echo "   make migrate-prod"
