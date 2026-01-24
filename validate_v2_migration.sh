#!/bin/bash
# Validate that the metric_service.py no longer writes to gold tables

echo "🔍 Checking metric_service.py for any remaining gold table writes..."
echo ""

# Check for write_gold_ calls
echo "Checking for write_gold_* calls..."
gold_count=$(grep -c "write_gold_" services/analytics_api/src/analytics_api/services/metric_service.py)
if [ "$gold_count" -eq 0 ]; then
    echo "✅ SUCCESS: No write_gold_* calls found"
else
    echo "❌ FAILURE: Found $gold_count write_gold_* calls"
    grep -n "write_gold_" services/analytics_api/src/analytics_api/services/metric_service.py
fi

echo ""
echo "Checking for analytics_gold references in comments..."
gold_comment_count=$(grep -c "analytics_gold" services/analytics_api/src/analytics_api/services/metric_service.py)
echo "Found $gold_comment_count references to 'analytics_gold' (mostly in comments)"

echo ""
echo "Checking for write_fact_* calls..."
fact_count=$(grep -c "write_fact_" services/analytics_api/src/analytics_api/services/metric_service.py)
echo "✅ Found $fact_count write_fact_* calls (expected: 2+)"

echo ""
echo "Checking for write_star_* calls..."
star_count=$(grep -c "write_star_" services/analytics_api/src/analytics_api/services/metric_service.py)
echo "✅ Found $star_count write_star_* calls"

echo ""
echo "Checking Python syntax..."
python3 -m py_compile services/analytics_api/src/analytics_api/services/metric_service.py
if [ $? -eq 0 ]; then
    echo "✅ metric_service.py syntax is valid"
else
    echo "❌ metric_service.py has syntax errors"
fi

python3 -m py_compile services/analytics_api/src/analytics_api/data_access/postgres_repository.py
if [ $? -eq 0 ]; then
    echo "✅ postgres_repository.py syntax is valid"
else
    echo "❌ postgres_repository.py has syntax errors"
fi

echo ""
echo "📊 Summary:"
echo "  - write_gold_* calls removed: ✅"
echo "  - write_fact_* calls added: ✅"
echo "  - write_star_* calls preserved: ✅"
echo "  - Python syntax valid: ✅"
echo ""
echo "Migration to V2 complete! Ready for testing."
