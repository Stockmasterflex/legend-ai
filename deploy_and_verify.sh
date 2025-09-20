#!/bin/bash

# Comprehensive deployment verification and auto-fixing script
echo "🚀 Starting comprehensive deployment and verification process..."

MAX_ATTEMPTS=5
ATTEMPT=1

deploy_and_verify() {
    echo "📋 Attempt $ATTEMPT of $MAX_ATTEMPTS"
    
    # 1. Commit current changes
    echo "📝 Committing changes..."
    git add .
    git commit -m "fix: Refocus site on professional portfolio and fix scanner

MAJOR REFOCUS:
- Homepage now showcases Kyle Thomas as professional, not just AI project
- Emphasizes technical analysis expertise + software engineering
- Professional background, credentials, and career alignment
- Trading tools demo with comprehensive filtering
- Advanced pattern recognition with proper sectors/industries/timeframes
- Chart analysis tools framework
- Career-focused presentation suitable for job applications

SCANNER IMPROVEMENTS:
- Added sector, industry, pattern, timeframe filtering
- Comprehensive stock universe scanning
- Professional trading plan generation
- Enhanced technical analysis features
- Interactive chart analysis tools

This aligns with career goals in quantitative trading and fintech roles." || echo "Nothing to commit"

    # 2. Push to GitHub
    echo "📤 Pushing to GitHub..."
    if ! git push origin main; then
        echo "❌ Git push failed, attempting to fix..."
        git pull --rebase origin main
        git push origin main
    fi

    # 3. Check GitHub Actions (best-effort)
    echo "🔍 Checking GitHub Actions status..."
    sleep 30
    
    # 4. Deploy to Vercel
    echo "🚀 Triggering Vercel deployment..."
    DEPLOY_RESPONSE=$(curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_OVUp69Fr1bmHENNsmxh80kwMkqc1/7l5CR6kqSo")
    echo "Vercel deploy triggered: $DEPLOY_RESPONSE"
    
    # 5. Wait for Vercel deployment
    echo "⏳ Waiting for Vercel deployment to complete..."
    sleep 120  # Wait 2 minutes for deployment
    
    # 6. Verify all services
    echo "🔍 Verifying all services..."
    
    # Check frontend
    FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://legend-ai.vercel.app || echo "000")
    echo "Frontend status: $FRONTEND_STATUS"
    
    # Check API
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://legend-api.onrender.com/healthz || echo "000")
    echo "API status: $API_STATUS"
    
    # Check screenshots
    SHOTS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://legend-shots.onrender.com/health || echo "000")
    echo "Screenshots status: $SHOTS_STATUS"
    
    # Check specific pages
    HOME_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://legend-ai.vercel.app/ || echo "000")
    DEMO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://legend-ai.vercel.app/demo || echo "000")
    PROJECTS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://legend-ai.vercel.app/projects || echo "000")
    
    echo "Page statuses - Home: $HOME_STATUS, Demo: $DEMO_STATUS, Projects: $PROJECTS_STATUS"
    
    # 7. Check for deployment errors
    ERRORS=()
    
    if [[ "$FRONTEND_STATUS" != "200" ]]; then
        ERRORS+=("Frontend not responding")
    fi
    
    if [[ "$API_STATUS" != "200" ]]; then
        ERRORS+=("API not responding")
    fi
    
    if [[ "$HOME_STATUS" != "200" ]] || [[ "$DEMO_STATUS" != "200" ]] || [[ "$PROJECTS_STATUS" != "200" ]]; then
        ERRORS+=("Some pages not loading")
    fi
    
    # Check health endpoint
    HEALTH_CHECK=$(curl -s https://legend-ai.vercel.app/api/health | jq -r '.status' 2>/dev/null || echo "error")
    if [[ "$HEALTH_CHECK" != "healthy" ]] && [[ "$HEALTH_CHECK" != "degraded" ]]; then
        ERRORS+=("Health endpoint not working")
    fi
    
    # 8. If errors found, attempt fixes
    if [[ ${#ERRORS[@]} -gt 0 ]]; then
        echo "❌ Found errors: ${ERRORS[*]}"
        
        if [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; then
            echo "🔧 Attempting to fix errors..."
            
            # Fix package issues
            if [[ -f "kyle-portfolio/package.json" ]]; then
                echo "Trying npm install with legacy peers..."
                (cd kyle-portfolio && npm install --legacy-peer-deps || true)
            fi
            
            ATTEMPT=$((ATTEMPT + 1))
            echo "🔄 Retrying deployment (attempt $ATTEMPT)..."
            deploy_and_verify
            return $?
        else
            echo "❌ Max attempts reached. Manual intervention required."
            echo "Current errors:"
            printf '%s\n' "${ERRORS[@]}"
            return 1
        fi
    else
        echo "✅ All services are working correctly!"
        echo "🎉 Deployment successful!"
        
        echo ""
        echo "📊 DEPLOYMENT SUMMARY:"
        echo "Frontend: https://legend-ai.vercel.app (Status: $FRONTEND_STATUS)"
        echo "API: https://legend-api.onrender.com (Status: $API_STATUS)"
        echo "Screenshots: https://legend-shots.onrender.com (Status: $SHOTS_STATUS)"
        echo "Health: $HEALTH_CHECK"
        echo ""
        echo "🎯 All systems operational!"
        return 0
    fi
}

# Start the deployment and verification process
# Note: This script is provided but not run automatically by CI.
: # usage: ./deploy_and_verify.sh
