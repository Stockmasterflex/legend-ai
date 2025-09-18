#!/usr/bin/env bash
set -euo pipefail

echo "📊 Legend AI Status Check"
echo "========================"
echo

# Check environment
echo "Environment Variables:"
echo "  API: ${LEGEND_API:-❌ NOT SET}"
echo "  SHOTS: ${LEGEND_SHOTS:-❌ NOT SET}"
echo "  FRONTEND: ${LEGEND_FRONTEND:-❌ NOT SET}"
echo

# Quick health checks
echo "Service Health:"

# API
if [ -n "${LEGEND_API:-}" ]; then
    if curl -fsS "${LEGEND_API}/healthz" > /dev/null 2>&1; then
        echo "  ✅ API: Healthy"
    else
        echo "  ❌ API: Unhealthy"
    fi
else
    echo "  ⚠️  API: Not configured"
fi

# Screenshots
if [ -n "${LEGEND_SHOTS:-}" ]; then
    if curl -fsS "${LEGEND_SHOTS}/healthz" > /dev/null 2>&1; then
        echo "  ✅ Screenshots: Healthy"
    else
        echo "  ❌ Screenshots: Unhealthy"
    fi
else
    echo "  ⚠️  Screenshots: Not configured"
fi

# Frontend
if [ -n "${LEGEND_FRONTEND:-}" ]; then
    CODE=$(curl -s -o /dev/null -w "%{http_code}" "${LEGEND_FRONTEND}")
    if [ "$CODE" = "200" ]; then
        echo "  ✅ Frontend: Healthy"
    else
        echo "  ❌ Frontend: HTTP $CODE"
    fi
else
    echo "  ⚠️  Frontend: Not configured"
fi

echo
echo "Git Activity:"
COMMITS_TODAY=$(git log --oneline --since="$(date +%Y-%m-%d)" 2>/dev/null | wc -l | tr -d ' ')
LAST_COMMIT=$(git log -1 --format=%cr 2>/dev/null || echo "never")
echo "  Commits today: $COMMITS_TODAY"
echo "  Last commit: $LAST_COMMIT"

echo
echo "Test Coverage:"
if command -v python3 > /dev/null 2>&1; then
    TEST_COUNT=$(python3 -m pytest --co -q 2>/dev/null | grep -c "::" || echo "0")
    echo "  Python tests: $TEST_COUNT"
else
    echo "  ⚠️  Python not found"
fi

echo
echo "🧭 Use 'tmux attach -t legend-orch' to view orchestrator"
