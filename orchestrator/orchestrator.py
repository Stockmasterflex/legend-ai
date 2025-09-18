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
