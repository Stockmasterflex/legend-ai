#!/bin/bash
# Fix Vercel Dashboard - Force Redeploy Script
# This forces Vercel to pick up the latest app.js with correct API calls

set -e  # Exit on error

echo "🔧 Legend AI - Vercel Dashboard Fix Script"
echo "==========================================="
echo ""

# Navigate to repo root
cd "$(dirname "$0")/.."

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository!"
    exit 1
fi

echo "📍 Current directory: $(pwd)"
echo ""

# Show current app.js API endpoint
echo "🔍 Checking current app.js API endpoint..."
if grep -q "/v1/patterns/all" app.js; then
    echo "✅ app.js correctly calls /v1/patterns/all"
else
    echo "⚠️  Warning: app.js might not be calling /v1/patterns/all"
fi
echo ""

# Check Vercel configuration
if [ -f "vercel.json" ]; then
    echo "📄 Found vercel.json"
    cat vercel.json
    echo ""
else
    echo "⚠️  No vercel.json found - Vercel might use default config"
    echo ""
fi

# Add a cache-busting comment to app.js
echo "🔨 Adding cache-busting comment to force rebuild..."
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "/* Updated: $TIMESTAMP - Force Vercel rebuild */" >> app.js

# Show git status
echo ""
echo "📊 Git status:"
git status --short

# Stage changes
echo ""
echo "📦 Staging changes..."
git add app.js

# Commit
COMMIT_MSG="fix: force Vercel redeploy - fix dashboard data display ($TIMESTAMP)"
echo ""
echo "💾 Committing: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# Get current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo ""
echo "🌿 Current branch: $BRANCH"

# Push
echo ""
echo "🚀 Pushing to remote..."
git push origin "$BRANCH"

echo ""
echo "✅ Done! Changes pushed to GitHub."
echo ""
echo "📋 Next Steps:"
echo "1. Go to https://vercel.com/dashboard"
echo "2. Find your 'legend-ai-dashboard' project"
echo "3. Go to Deployments tab"
echo "4. Wait for auto-deploy to complete (2-3 minutes)"
echo "5. Click the deployment when it's done"
echo "6. Test: https://legend-ai-dashboard.vercel.app/"
echo ""
echo "🧪 Test Command (paste in browser console):"
echo "fetch('https://legend-api.onrender.com/v1/patterns/all').then(r=>r.json()).then(d=>console.table(d.items))"
echo ""
echo "Expected: Table showing CRWD, PLTR, NVDA with prices and confidence"
echo ""

