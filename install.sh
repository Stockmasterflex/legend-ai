#!/usr/bin/env bash
set -euo pipefail

# ================================
# LEGEND AI ORCHESTRATOR - ONE-SHOT INSTALL
# ================================

# Color output for clarity
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}✨ Installing Legend AI Orchestrator...${NC}"

# Set up directories
PROJECT_DIR="${HOME}/Projects/LegendAI"
cd "$PROJECT_DIR" || { echo -e "${RED}Error: Project directory not found${NC}"; exit 1; }

echo "Creating orchestrator structure..."
mkdir -p orchestrator logs ai_prompts orchestrator/prompts .orchestrator

# ===== CONFIGURATION FILE =====
cat > orchestrator/config.json <<'CONFIG'
{
  "project_name": "Legend AI",
  "services": {
    "api": {
      "name": "Scanner API",
      "url_env": "LEGEND_API",
      "health_path": "/healthz",
      "render_id_env": "API_SERVICE_ID"
    },
    "shots": {
      "name": "Screenshot Engine",
      "url_env": "LEGEND_SHOTS",
      "health_path": "/healthz",
      "render_id_env": "SHOTS_SERVICE_ID"
    },
    "frontend": {
      "name": "Next.js Frontend",
      "url_env": "LEGEND_FRONTEND",
      "health_path": "/",
      "deploy_hook_env": "VERCEL_DEPLOY_HOOK_URL"
    }
  },
  "ai_tools": {
    "cursor": { "enabled": true, "prompt_prefix": ".cursor-prompt-" },
    "codex": { "enabled": true, "prompt_prefix": "codex-" }
  },
  "notifications": {
    "slack_webhook_env": "SLACK_WEBHOOK_URL",
    "enabled": false
  }
}
CONFIG

# ===== MONITORING RULES =====
cat > orchestrator/rules.yml <<'RULES'
# Orchestrator Rules - What to watch and how to respond
poll_interval_seconds: 30

cooldowns:
  deploy: 300      # 5 minutes between deploys
  notify: 60       # 1 minute between notifications
  ai_prompt: 120   # 2 minutes between AI prompts

checks:
  # Service Health Checks
  - id: api_health
    type: http
    service: api
    critical: true
    on_fail:
      - notify: "API is down"
      - ai_prompt: debug_api.md
      - auto_deploy: api

  - id: shots_health
    type: http
    service: shots
    critical: false
    on_fail:
      - notify: "Screenshot service unhealthy"
      - ai_prompt: fix_screenshots.md

  - id: frontend_health
    type: http
    service: frontend
    critical: true
    on_fail:
      - notify: "Frontend unreachable"
      - ai_prompt: debug_frontend.md

  # Code Quality Checks
  - id: test_coverage
    type: command
    cmd: "python -m pytest --co -q 2>/dev/null | wc -l"
    expect_min: 10
    on_fail:
      - ai_prompt: write_tests.md

  - id: git_activity
    type: git
    min_commits_today: 1
    on_low:
      - ai_prompt: daily_priorities.md

  # Analytics Quality
  - id: analytics_check
    type: api_quality
    endpoint: "/api/v1/analytics/overview?run_id=1"
    required_keys: ["kpis", "pattern_distribution"]
    on_fail:
      - ai_prompt: fix_analytics.md
RULES

# ===== AI PROMPT TEMPLATES =====

# Debug API Template
cat > orchestrator/prompts/debug_api.md <<'PROMPT'
# 🚨 API Service Down

**Time:** {{timestamp}}
**Service:** {{service_url}}
**Last Known Good:** {{last_healthy}}

## Quick Diagnosis Steps

1. Check recent commits that might have broken it:
   ```bash
   git log --oneline -5
   ```

2. View live logs:
   ```bash
   curl -H "Authorization: Bearer $RENDER_TOKEN" \
     "https://api.render.com/v1/services/{{service_id}}/logs?limit=100"
   ```

3. Test locally:
   ```bash
   python legend_ai/api.py
   curl -fsS localhost:8000/healthz
   ```

## Common Fixes

- Import Error: Check requirements.txt matches imports
- DB Connection: Verify DATABASE_URL is set
- Port Binding: Ensure PORT env var is used
- Timeout: Increase gunicorn timeout if needed

## Deploy Fix
Once fixed locally:
```bash
git add -A && git commit -m "fix: api health check"
git push origin main
```
PROMPT

# Screenshots Fix Template
cat > orchestrator/prompts/fix_screenshots.md <<'PROMPT'
# 🖨️ Screenshot Service Issue

**Service:** {{service_url}}/healthz
**Status:** {{error_detail}}

## Likely Causes

1. Chromium not found - Check Puppeteer setup:
   ```javascript
   // Needs @sparticuz/chromium for serverless
   const chromium = require('@sparticuz/chromium');
   ```

2. Memory limits - Render free tier = 512MB
   - Reduce concurrent renders
   - Clear page after each chart

3. DRY_RUN stuck - Check env:
   ```bash
   echo $DRY_RUN  # Should be 0 or false
   ```

## Quick Test
```bash
cd legend-room-screenshot-engine
npm start
curl localhost:3001/render?symbol=NVDA
```
PROMPT

# Daily Priorities Template
cat > orchestrator/prompts/daily_priorities.md <<'PROMPT'
# 🗓️ Daily Development Priorities

**Date:** {{date}}
**Last Commit:** {{last_commit_time}} ago
**Current Sprint:** Production Hardening

## Today's Focus (2-hour blocks)

### Block 1: Core Functionality (9-11am)
{{#if api_unhealthy}}
- 🚑 Fix API health issues first
{{else}}
- ✅ API healthy - focus on features
{{/if}}

Priority tasks:
1. [ ] Ensure scanner returns consistent data shape
2. [ ] Add error boundaries to frontend
3. [ ] Test chart generation with 5 random symbols

### Block 2: User Experience (11am-1pm)
- [ ] Polish /demo page load time
- [ ] Add loading skeletons for charts
- [ ] Verify mobile responsiveness

### Block 3: Growth & Content (2-4pm)
- [ ] Write one technical blog post
- [ ] Update landing page copy
- [ ] Add Google Analytics events

## Quick Wins (15-min tasks)
- Add pytest for one untested endpoint
- Update README with latest setup
- Check and merge Dependabot PRs
- Tweet about a pattern you found

## Evening Review Checklist
- [ ] All services green in orchestrator
- [ ] At least 3 meaningful commits
- [ ] Tomorrow's priorities noted

---
💡 Pro tip: Use `legend-status` command for quick health check
PROMPT

# Write Tests Template
cat > orchestrator/prompts/write_tests.md <<'PROMPT'
# 🧪 Test Coverage Low

Current test count: {{test_count}}
Target: 15+ tests minimum

## Priority Tests to Add

### 1. API Endpoints
```python
def test_scan_endpoint_with_filters():
    """Test /api/v1/scan with various filter combinations"""
    response = client.get("/api/v1/scan?pattern=VCP&universe=sp500")
    assert response.status_code == 200
    assert "stocks" in response.json()

def test_analytics_empty_state():
    """Ensure analytics handles no data gracefully"""
    response = client.get("/api/v1/analytics/overview?run_id=999")
    assert response.status_code == 200
    assert response.json()["data_status"] in ["empty", "no_data"]
```

### 2. Chart Service
```python
def test_chart_metadata():
    """Verify chart endpoint returns proper metadata"""
    response = client.get("/api/v1/chart?symbol=AAPL")
    assert "chart_url" in response.json()
    assert "meta" in response.json()
```

### 3. Frontend Components
```javascript
// In __tests__/
test('PatternCard renders without crashing', () => {
  render(<PatternCard pattern="VCP" count={5} />);
});
```

Run tests:
```bash
python -m pytest -xvs
npm test
```
PROMPT

# ===== MAIN ORCHESTRATOR SCRIPT =====
cat > orchestrator/orchestrator.py <<'PYTHON'
#!/usr/bin/env python3
"""
Legend AI Orchestrator - Your AI Project Manager
Monitors services, generates AI prompts, keeps you productive
"""

import os
import sys
import time
import json
import yaml
import subprocess
import logging
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/orchestrator.log')
    ]
)
logger = logging.getLogger(__name__)

class LegendOrchestrator:
    def __init__(self):
        self.project_dir = Path.cwd()
        self.config = self.load_config()
        self.rules = self.load_rules()
        self.state_file = Path('.orchestrator/state.json')
        self.state = self.load_state()

    def load_config(self):
        with open('orchestrator/config.json', 'r') as f:
            return json.load(f)

    def load_rules(self):
        with open('orchestrator/rules.yml', 'r') as f:
            return yaml.safe_load(f)

    def load_state(self):
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {'cooldowns': {}, 'last_healthy': {}}

    def save_state(self):
        self.state_file.parent.mkdir(exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def check_cooldown(self, action_key, seconds):
        last_time = self.state['cooldowns'].get(action_key, 0)
        return (time.time() - last_time) > seconds

    def update_cooldown(self, action_key):
        self.state['cooldowns'][action_key] = time.time()

    def check_http_service(self, service_name):
        service = self.config['services'].get(service_name)
        if not service:
            return False, "Service not configured"

        base_url = os.environ.get(service['url_env'], '')
        if not base_url:
            return False, f"Environment variable {service['url_env']} not set"

        url = base_url.rstrip('/') + service['health_path']

        try:
            req = Request(url, headers={'User-Agent': 'Legend-Orchestrator'})
            response = urlopen(req, timeout=10)
            data = response.read().decode('utf-8')

            try:
                json_data = json.loads(data)
                return True, json_data
            except Exception:
                return True, data

        except HTTPError as e:
            return False, f"HTTP {e.code}: {e.reason}"
        except URLError as e:
            return False, f"Connection error: {e.reason}"
        except Exception as e:
            return False, str(e)

    def check_command(self, cmd, expect_min=None):
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=30, cwd=self.project_dir
            )

            if result.returncode != 0:
                return False, result.stderr.strip()

            output = result.stdout.strip()

            if expect_min is not None:
                try:
                    value = int(output)
                    if value < expect_min:
                        return False, f"Value {value} below minimum {expect_min}"
                    return True, value
                except Exception:
                    return False, f"Could not parse output as number: {output}"

            return True, output

        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def check_git_activity(self):
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            result = subprocess.run(
                ['git', 'log', '--oneline', '--since', today],
                capture_output=True, text=True, cwd=self.project_dir
            )

            commits = [l for l in result.stdout.splitlines() if l.strip()]

            last_commit_result = subprocess.run(
                ['git', 'log', '-1', '--format=%cr'],
                capture_output=True, text=True, cwd=self.project_dir
            )
            last_commit = last_commit_result.stdout.strip() or "unknown"

            return len(commits), last_commit

        except Exception as e:
            logger.error(f"Git check failed: {e}")
            return 0, "unknown"

    def generate_ai_prompt(self, template_file, context=None):
        if context is None:
            context = {}

        template_path = Path(f'orchestrator/prompts/{template_file}')
        if not template_path.exists():
            logger.warning(f"Template {template_file} not found")
            return None

        with open(template_path, 'r') as f:
            template = f.read()

        context.update({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date': datetime.now().strftime('%Y-%m-%d'),
        })

        for key, value in context.items():
            template = template.replace(f'{{{{{key}}}}}', str(value))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f'ai_prompts/{timestamp}_{template_file}')

        with open(output_file, 'w') as f:
            f.write(template)

        if self.config['ai_tools']['cursor']['enabled']:
            cursor_file = Path(f".cursor-prompt-{timestamp}.md")
            with open(cursor_file, 'w') as f:
                f.write(template)
            logger.info(f"📝  Cursor prompt created: {cursor_file}")

        logger.info(f"🧠 AI prompt generated: {output_file}")
        return output_file

    def notify(self, message):
        logger.info(f"🔔 {message}")

        webhook_url = os.environ.get(
            self.config['notifications']['slack_webhook_env'], ''
        )

        if webhook_url and self.config['notifications']['enabled']:
            try:
                import urllib.request
                data = json.dumps({'text': message}).encode('utf-8')
                req = urllib.request.Request(
                    webhook_url,
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                urllib.request.urlopen(req)
            except Exception as e:
                logger.error(f"Slack notification failed: {e}")

    def deploy_service(self, service_name):
        service = self.config['services'].get(service_name)
        if not service:
            logger.error(f"Service {service_name} not configured")
            return

        if service_name == 'frontend':
            hook_url = os.environ.get(service.get('deploy_hook_env', ''))
            if hook_url:
                try:
                    import urllib.request
                    urllib.request.urlopen(
                        urllib.request.Request(hook_url, method='POST')
                    )
                    logger.info(f"🚀 Triggered Vercel deployment for {service_name}")
                except Exception as e:
                    logger.error(f"Vercel deploy failed: {e}")
        else:
            token = os.environ.get('RENDER_TOKEN', '')
            service_id = os.environ.get(service.get('render_id_env', ''))

            if token and service_id:
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        f'https://api.render.com/v1/services/{service_id}/deploys',
                        headers={'Authorization': f'Bearer {token}'},
                        method='POST'
                    )
                    urllib.request.urlopen(req)
                    logger.info(f"🚀 Triggered Render deployment for {service_name}")
                except Exception as e:
                    logger.error(f"Render deploy failed: {e}")

    def run_check(self, check):
        check_type = check.get('type')

        if check_type == 'http':
            service = check.get('service')
            success, detail = self.check_http_service(service)
            if success:
                self.state['last_healthy'][service] = time.time()
            return success, detail

        elif check_type == 'command':
            cmd = check.get('cmd')
            expect_min = check.get('expect_min')
            return self.check_command(cmd, expect_min)

        elif check_type == 'git':
            commits, last_commit = self.check_git_activity()
            min_commits = check.get('min_commits_today', 1)
            if commits < min_commits:
                return False, {'commits_today': commits, 'last_commit': last_commit}
            return True, {'commits_today': commits, 'last_commit': last_commit}

        elif check_type == 'api_quality':
            api_service = self.config['services']['api']
            base_url = os.environ.get(api_service['url_env'], '')
            if not base_url:
                return False, "API URL not configured"

            endpoint = check.get('endpoint')
            url = base_url.rstrip('/') + endpoint

            try:
                req = Request(url, headers={'User-Agent': 'Legend-Orchestrator'})
                response = urlopen(req, timeout=10)
                data = json.loads(response.read().decode('utf-8'))

                required_keys = check.get('required_keys', [])
                missing = [k for k in required_keys if k not in data]

                if missing:
                    return False, f"Missing keys: {missing}"
                return True, data

            except Exception as e:
                return False, str(e)

        return False, f"Unknown check type: {check_type}"

    def handle_failure(self, check, detail):
        check_id = check.get('id')
        actions = check.get('on_fail', []) if not check.get('on_low') else check.get('on_low', [])

        for action in actions:
            if isinstance(action, dict):
                action_type = list(action.keys())[0]
                action_value = action[action_type]
            else:
                continue

            cooldown_key = f"{check_id}_{action_type}"
            cooldown_time = self.rules['cooldowns'].get(action_type, 60)

            if not self.check_cooldown(cooldown_key, cooldown_time):
                continue

            if action_type == 'notify':
                self.notify(action_value)
                self.update_cooldown(cooldown_key)

            elif action_type == 'ai_prompt':
                service_key = check.get('service', '')
                service_cfg = self.config['services'].get(service_key, {})
                context = {
                    'service_url': os.environ.get(service_cfg.get('url_env', ''), 'unknown'),
                    'error_detail': str(detail),
                    'last_healthy': datetime.fromtimestamp(
                        self.state['last_healthy'].get(service_key, 0)
                    ).strftime('%H:%M:%S') if service_key in self.state['last_healthy'] else 'never',
                }
                if isinstance(detail, dict):
                    context.update(detail)

                self.generate_ai_prompt(action_value, context)
                self.update_cooldown(cooldown_key)

            elif action_type == 'auto_deploy':
                self.deploy_service(action_value)
                self.update_cooldown(cooldown_key)

    def run(self):
        logger.info("🤖 Legend AI Orchestrator started")
        logger.info(f"📈 Monitoring {len(self.rules['checks'])} checks")
        logger.info(f"⏱️  Poll interval: {self.rules['poll_interval_seconds']}s")

        while True:
            try:
                for check in self.rules['checks']:
                    check_id = check.get('id', 'unknown')
                    success, detail = self.run_check(check)

                    if not success:
                        logger.warning(f"❌ {check_id}: {detail}")
                        self.handle_failure(check, detail)
                    else:
                        if check.get('critical'):
                            logger.debug(f"✅ {check_id}: OK")

                self.save_state()

            except KeyboardInterrupt:
                logger.info("🛑 Orchestrator stopped by user")
                break
            except Exception as e:
                logger.error(f"Orchestrator error: {e}", exc_info=True)

            time.sleep(self.rules['poll_interval_seconds'])

def main():
    required_env = ['LEGEND_API', 'LEGEND_SHOTS']
    missing = [e for e in required_env if not os.environ.get(e)]

    if missing:
        print(f"⚠️  Missing environment variables: {missing}")
        print("Please set them in your shell or .env file")
        sys.exit(1)

    orchestrator = LegendOrchestrator()
    orchestrator.run()

if __name__ == '__main__':
    main()
PYTHON

chmod +x orchestrator/orchestrator.py

# ===== HELPER SCRIPTS =====

# Quick status check
envsubst_func() { envsubst "$@" 2>/dev/null || cat; }

cat > orchestrator/status.sh <<'BASH'
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
BASH
chmod +x orchestrator/status.sh

# Deploy helper
cat > orchestrator/deploy.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Deploying Legend AI Services"
echo "==============================="
echo

# Check for required env vars
if [ -z "${RENDER_TOKEN:-}" ]; then
    echo "⚠️  RENDER_TOKEN not set - skipping Render deployments"
else
    if [ -n "${API_SERVICE_ID:-}" ]; then
        echo "Deploying API..."
        curl -X POST -H "Authorization: Bearer $RENDER_TOKEN" \
            "https://api.render.com/v1/services/$API_SERVICE_ID/deploys" \
            > /dev/null 2>&1 && echo "  ✅ API deployment triggered"
    fi

    if [ -n "${SHOTS_SERVICE_ID:-}" ]; then
        echo "Deploying Screenshots..."
        curl -X POST -H "Authorization: Bearer $RENDER_TOKEN" \
            "https://api.render.com/v1/services/$SHOTS_SERVICE_ID/deploys" \
            > /dev/null 2>&1 && echo "  ✅ Screenshots deployment triggered"
    fi
fi

if [ -n "${VERCEL_DEPLOY_HOOK_URL:-}" ]; then
    echo "Deploying Frontend..."
    curl -X POST "$VERCEL_DEPLOY_HOOK_URL" > /dev/null 2>&1 && \
        echo "  ✅ Frontend deployment triggered"
else
    echo "⚠️  VERCEL_DEPLOY_HOOK_URL not set - skipping frontend"
fi

echo
echo "✨ Deployments triggered - check service dashboards for status"
BASH
chmod +x orchestrator/deploy.sh

# Run orchestrator script
cat > orchestrator/run.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

# Install dependencies if needed
echo "Checking dependencies..."
python3 -c "import yaml" 2>/dev/null || pip3 install -q pyyaml

# Check for tmux
if ! command -v tmux > /dev/null 2>&1; then
    echo "Installing tmux..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install tmux
    else
        sudo apt-get update -y && sudo apt-get install -y tmux
    fi
fi

# Create or attach to tmux session
SESSION="legend-orch"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Orchestrator already running in tmux"
    echo "Attaching to session..."
    tmux attach -t "$SESSION"
else
    echo "Starting orchestrator in tmux..."
    tmux new-session -d -s "$SESSION" -n orchestrator
    tmux send-keys -t "$SESSION" "cd $PWD" C-m
    tmux send-keys -t "$SESSION" "python3 orchestrator/orchestrator.py" C-m
    echo "✅ Orchestrator started in tmux session: $SESSION"
    echo "   Use 'tmux attach -t legend-orch' to view"
fi
BASH
chmod +x orchestrator/run.sh

# ===== INSTALL DEPENDENCIES =====
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install -q pyyaml

# ===== CREATE ENV TEMPLATE =====
if [ ! -f .env ]; then
    cat > .env.template <<'ENV'
# Legend AI Environment Variables
# Copy to .env and fill in your values

# Service URLs (required)
export LEGEND_API=https://your-api.onrender.com
export LEGEND_SHOTS=https://your-shots.onrender.com
export LEGEND_FRONTEND=https://your-site.vercel.app

# Render Deployment (optional)
export RENDER_TOKEN=your-render-api-token
export API_SERVICE_ID=srv-xxxxxxxxxxxxx
export SHOTS_SERVICE_ID=srv-xxxxxxxxxxxxx

# Vercel Deployment (optional)
export VERCEL_DEPLOY_HOOK_URL=https://api.vercel.com/v1/integrations/deploy/xxxxx

# Notifications (optional)
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxxx
ENV
    echo -e "${YELLOW}🧠  Created .env.template - copy to .env and add your values${NC}"
fi

# ===== FINAL SETUP =====
echo
echo -e "${GREEN}✅ Legend AI Orchestrator installed successfully!${NC}"
echo
echo "🚦 Quick Start Guide:"
echo "==================="
echo
if [ ! -f .env ]; then
  echo "1. Set up environment variables:"
  echo "   cp .env.template .env"
  echo "   nano .env  # Add your service URLs and tokens"
  echo "   source .env"
  echo
fi
echo "2. Start the orchestrator:"
echo "   ./orchestrator/run.sh"
echo

echo "3. Check status anytime:"
echo "   ./orchestrator/status.sh"
echo

echo "4. View live logs:"
echo "   tmux attach -t legend-orch"
echo

echo "5. Deploy services:"
echo "   ./orchestrator/deploy.sh"
echo

echo "🧠  AI prompts will appear in: ai_prompts/"
echo "🧭  Cursor prompts will appear as: .cursor-prompt-*.md"
echo

echo -e "${YELLOW}💡 Pro tip: Add these aliases to your shell:${NC}"
echo "alias legend-status='cd ~/Projects/LegendAI && ./orchestrator/status.sh'"
echo "alias legend-orch='cd ~/Projects/LegendAI && tmux attach -t legend-orch'"
echo "alias legend-deploy='cd ~/Projects/LegendAI && ./orchestrator/deploy.sh'"
