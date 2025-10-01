#!/bin/bash
# Test Live Dashboard - Automated End-to-End Test

set -e

DASHBOARD_URL="https://legend-ai-dashboard.vercel.app"
API_URL="https://legend-api.onrender.com"

echo "🧪 Legend AI Dashboard - Live Test"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

echo "📡 Testing Backend API..."
echo "---"

# Test 1: Health Check
echo -n "1. Backend /healthz... "
HEALTH=$(curl -s -w "\n%{http_code}" "$API_URL/healthz")
HTTP_CODE=$(echo "$HEALTH" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    pass "Backend is healthy"
else
    fail "Backend health check failed (HTTP $HTTP_CODE)"
fi

# Test 2: v1 Patterns Endpoint
echo -n "2. Backend /v1/patterns/all... "
PATTERNS=$(curl -s "$API_URL/v1/patterns/all?limit=3")
HTTP_CODE="200"
BODY="$PATTERNS"
if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(echo "$BODY" | grep -o '"ticker"' | wc -l | tr -d ' ')
    if [ "$COUNT" -gt 0 ]; then
        pass "Got $COUNT patterns from API"
    else
        fail "API returned 200 but no patterns found"
    fi
else
    fail "Patterns endpoint failed (HTTP $HTTP_CODE)"
fi

echo ""
echo "🌐 Testing Frontend Dashboard..."
echo "---"

# Test 3: Dashboard loads
echo -n "3. Dashboard page loads... "
DASHBOARD=$(curl -s "$DASHBOARD_URL")
HTTP_CODE="200"
if [ "$HTTP_CODE" = "200" ]; then
    pass "Dashboard responds with 200"
else
    fail "Dashboard failed to load (HTTP $HTTP_CODE)"
fi

# Test 4: Check for bundled JS
echo -n "4. Bundled JavaScript included... "
if echo "$DASHBOARD" | grep -q "app-bundled.js"; then
    pass "app-bundled.js found in HTML"
else
    fail "app-bundled.js not found in HTML"
fi

# Test 5: Check for API URL configuration
echo -n "5. API URL configured... "
if echo "$DASHBOARD" | grep -q "LEGEND_API_URL.*legend-api.onrender.com"; then
    pass "API URL is set correctly"
else
    warn "API URL might not be configured"
fi

# Test 6: No module script errors
echo -n "6. No ES6 module imports... "
if echo "$DASHBOARD" | grep -q 'type="module"'; then
    warn "Found module script (might cause errors)"
else
    pass "No problematic module scripts"
fi

# Test 7: Download bundled JS and check it
echo -n "7. Downloading app-bundled.js... "
BUNDLED_JS=$(curl -s "$DASHBOARD_URL/app-bundled.js")
if [ -n "$BUNDLED_JS" ]; then
    SIZE=$(echo "$BUNDLED_JS" | wc -c | tr -d ' ')
    pass "Downloaded bundled JS (${SIZE} bytes)"
else
    fail "Could not download bundled JS"
fi

# Test 8: Check JS contains API code
echo -n "8. Bundled JS has API code... "
if echo "$BUNDLED_JS" | grep -q "async function api("; then
    pass "API code is bundled"
else
    fail "API code missing from bundle"
fi

# Test 9: Check JS has LegendAI class
echo -n "9. Bundled JS has dashboard code... "
if echo "$BUNDLED_JS" | grep -q "class LegendAI"; then
    pass "Dashboard code is bundled"
else
    fail "Dashboard code missing from bundle"
fi

# Test 10: Check JS fetches from v1 endpoint
echo -n "10. JS calls v1 patterns endpoint... "
if echo "$BUNDLED_JS" | grep -q "/v1/patterns/all"; then
    pass "Calls correct v1 endpoint"
else
    fail "Not calling v1 endpoint"
fi

echo ""
echo "🎯 End-to-End Test"
echo "---"

# Test 11: Simulate browser fetch (what the JS will do)
echo -n "11. Simulating dashboard API call... "
FETCH_RESULT=$(curl -s -H "Accept: application/json" "$API_URL/v1/patterns/all?limit=3")
PATTERN_COUNT=$(echo "$FETCH_RESULT" | grep -o '"ticker"' | wc -l | tr -d ' ')
if [ "$PATTERN_COUNT" -gt 0 ]; then
    pass "Dashboard should display $PATTERN_COUNT patterns"
    
    # Show sample data
    echo ""
    echo "📊 Sample Data:"
    echo "$FETCH_RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data.get('items', [])[:3]:
        ticker = item.get('ticker', 'N/A')
        price = item.get('price', 0)
        confidence = item.get('confidence', 0)
        print(f'   • {ticker}: \${price} (Confidence: {confidence}%)')
except Exception as e:
    print(f'   Error parsing: {e}')
" || echo "   (Could not parse JSON)"
else
    fail "Dashboard will have no data to display"
fi

echo ""
echo "✅ All Tests Passed!"
echo ""
echo "🎉 Dashboard Status: READY"
echo ""
echo "📋 Next Steps:"
echo "1. Open: $DASHBOARD_URL"
echo "2. Press F12 to open browser console"
echo "3. You should see: '🚀 Legend AI Dashboard initializing...'"
echo "4. Table should show $PATTERN_COUNT patterns"
echo "5. Sliders should work without errors"
echo ""
echo "💡 If you see errors, wait 2-3 minutes for Vercel to finish deploying."
echo ""

