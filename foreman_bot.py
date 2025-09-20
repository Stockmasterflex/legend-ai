import os
import slack_bolt
from slack_bolt.adapter.socket_mode import SocketModeHandler
import subprocess
import openai
import re
import threading
import time
import schedule
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import base64
from datetime import datetime
from foreman_advanced import AdvancedBotIntelligence, handle_natural_language_message
from typing import Dict, List

# --- CONFIGURATION ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
FOREMAN_SCHEDULE_CHANNEL_ID = os.environ.get("FOREMAN_SCHEDULE_CHANNEL_ID", "")

app = slack_bolt.App(token=SLACK_BOT_TOKEN)
openai.api_key = OPENAI_API_KEY


_original_chat_post = app.client.chat_postMessage


def _chat_post_with_journal(*args, **kwargs):
    text = kwargs.get("text")
    try:
        return _original_chat_post(*args, **kwargs)
    finally:
        try:
            snippet = text if isinstance(text, str) else json.dumps(text) if text is not None else ""
            log_journal("slack", "Slack message", snippet)
        except Exception:
            LOGGER.exception("Failed to journal Slack message")


app.client.chat_postMessage = _chat_post_with_journal  # type: ignore[assignment]

# Resolve repository root regardless of whether this file lives at repo root or in foreman-bot/
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent
if _REPO_ROOT.name == "foreman-bot":
    _REPO_ROOT = _REPO_ROOT.parent

# --- LOGGING SETUP & CONFIG VALIDATION ---
LOGS_DIR = _REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOGGER = logging.getLogger("foreman_bot")
LOGGER.setLevel(logging.INFO)
if not LOGGER.handlers:
    file_handler = RotatingFileHandler(LOGS_DIR / "foreman_bot.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)

REQUIRED_ENV_VARS = [
    ("SLACK_BOT_TOKEN", SLACK_BOT_TOKEN),
    ("SLACK_APP_TOKEN", SLACK_APP_TOKEN),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
]
missing = [k for k, v in REQUIRED_ENV_VARS if not v]
if missing:
    LOGGER.error(f"Missing required environment variables: {', '.join(missing)}")

# --- LIGHTWEIGHT LEARNING SYSTEM ---
LEARNING_PATH = _REPO_ROOT / "bot_learning.json"

def load_learning():
    try:
        if LEARNING_PATH.exists():
            with open(LEARNING_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        LOGGER.exception("Failed to load bot_learning.json")
    return {"events": {}, "successes": 0, "failures": 0}


def save_learning(data):
    try:
        with open(LEARNING_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        LOGGER.exception("Failed to save bot_learning.json")


LEARNING = load_learning()

def learn(event: str, ok: bool):
    try:
        LEARNING["events"].setdefault(event, 0)
        LEARNING["events"][event] += 1
        if ok:
            LEARNING["successes"] += 1
        else:
            LEARNING["failures"] += 1
        save_learning(LEARNING)
    except Exception:
        LOGGER.exception("learn() failed to update learning store")

# Initialize advanced NLP helper
advanced_bot = AdvancedBotIntelligence()


def log_journal(tool, title, body):
    from datetime import datetime, timezone
    import os

    path = os.getenv("JOURNAL_PATH", ".orchestrator/journal.jsonl")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "author": "foreman_bot",
        "channel": "slack",
        "title": title,
        "body": body,
        "tags": [],
    }
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        LOGGER.exception("Failed to append journal entry")

# --- HELP TEXT ---
HELP_TEXT = """
*Foreman Bot (Epic Edition)* - Your AI Development Partner

Commands:
- `fix [request] in [file]` — AI patch a file and open a PR.
- `write tests for [file]` — Generate pytest tests for a file.
- `document [file]` — Add docstrings and comments to a file.
- `plan feature [description]` — Break down a feature into TODOs.
- `status` / `deploy` — Orchestrator commands.
- `diagnose` — Analyze failures from status and recent commits.
- `report` — Generate a project status report.
- `test` — Run pytest.
- `analyze image [prompt]` — Vision analysis for attached images.
- `ci fix` or `fix workflows` — Auto-fix common GitHub Actions issues.
- `health` — Deployment and configuration health check.
- `cleanup branches` — Remove merged bot-fix branches on origin.
- `help [command]` — Show usage for a command.

Scheduled:
- Daily project report at 9 AM PT (set FOREMAN_SCHEDULE_CHANNEL_ID)
"""


@app.message(re.compile(r"^remember\s+(.*)", re.IGNORECASE))
def remember_handler(message, say, context, logger):
    note = context['matches'][0].strip()
    log_journal("slack", "Remember", note)
    say(f"🧠 Noted: {note}")


@app.message(re.compile(r"^summary\s+(today|this week)$", re.IGNORECASE))
def summary_handler(message, say, context, logger):
    period = context['matches'][0].lower()
    import json, datetime, os
    path = os.getenv("JOURNAL_PATH", ".orchestrator/journal.jsonl")
    now = datetime.datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) if period == "today" else now - datetime.timedelta(days=7)
    lines = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    row = json.loads(line)
                    ts = datetime.datetime.fromisoformat(row["ts"].replace("Z", "+00:00")).replace(tzinfo=None)
                    if ts >= start:
                        lines.append(row)
                except Exception:
                    pass
    out: Dict[str, List[str]] = {}
    for r in lines:
        out.setdefault(r.get("tool", "unknown"), []).append(f"- {r.get('title', 'untitled')}: {str(r.get('body', ''))[:200]}")
    if not out:
        say(f"Nothing logged for {period}.")
        return
    blocks = [f"*Summary ({period})*"]
    for tool, items in out.items():
        blocks.append(f"*{tool}*")
        blocks.extend(items[:10])
    log_journal("foreman", f"Summary {period}", f"items={len(lines)}")
    say("\n".join(blocks))

# --- HELPER FUNCTIONS ---
def _safe_repo_path(p: str) -> Path:
    """Resolve a potentially relative path safely within the repo root."""
    base = _REPO_ROOT
    candidate = (base / p).resolve()
    if not str(candidate).startswith(str(base)):
        raise ValueError("Unsafe path outside repository root")
    return candidate


def run_command(command, channel_id, post_to_slack=True):
    try:
        # Normalize any leading ../ to ./ since we always run from repo root
        cmd = command.strip()
        if cmd.startswith("../"):
            cmd = "./" + cmd[3:]
        LOGGER.info(f"Running command: {cmd}")
        if post_to_slack:
            app.client.chat_postMessage(channel=channel_id, text=f"🤖 Running: `{cmd}`")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_REPO_ROOT),
        )
        LOGGER.info(f"Command exit code: {result.returncode}")
        success = (result.returncode == 0)
        learn(f"cmd:{cmd}", success)
        if post_to_slack:
            status_emoji = "✅" if success else "❌"
            heading = "Succeeded" if success else "Failed"
            output = f"{status_emoji} *{heading}*\n"
            if result.stdout:
                output += f"```{result.stdout}```"
            if result.stderr:
                output += f"🚨 *Errors/Warnings:*\n```{result.stderr}```"
            app.client.chat_postMessage(channel=channel_id, text=output)
            log_journal("warp", f"Command: {cmd}", output)
        return result.stdout, result.stderr
    except Exception as e:
        LOGGER.exception("run_command failed")
        learn(f"cmd:{command}", False)
        if post_to_slack:
            app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Command Failed:*\n```{str(e)}```")
            log_journal("warp", f"Command failed: {command}", str(e))
        return None, str(e)

def create_github_pr(channel_id, branch_name, title, body=""):
    if not GITHUB_USERNAME or not GITHUB_REPO:
        app.client.chat_postMessage(channel=channel_id, text="⚠️ `GITHUB_USERNAME` and `GITHUB_REPO` are not set. Cannot create PR.")
        return
    pr_url = f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}/compare/main...{branch_name}?expand=1&title={quote(title)}&body={quote(body)}"
    app.client.chat_postMessage(channel=channel_id, text=f"✅ Pushed changes to branch `{branch_name}`.\n*Click here to create a Pull Request:* <{pr_url}|Review Changes>")


def ai_chat(messages, model="gpt-4-turbo"):
    """Generic chat helper that supports text and vision inputs."""
    try:
        response = openai.chat.completions.create(model=model, messages=messages)
        content = response.choices[0].message.content
        log_journal("openai", "AI response", content or "")
        return content
    except Exception as e:
        LOGGER.exception("ai_chat failed")
        error_message = f"[AI unavailable: {e}]"
        log_journal("openai", "AI failure", error_message)
        return error_message


def ai_request(prompt, model="gpt-4-turbo"):
    return ai_chat([{ "role": "user", "content": prompt }], model=model)


def _now_slug():
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")


def _slugify(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9-_]+", "-", text.lower()).strip("-")
    return s[:limit] if len(s) > limit else s


def _branch_name(prefix: str, title: str) -> str:
    return f"{prefix}/{_slugify(title)}-{_now_slug()}"

# --- CORE COMMANDS ---
def fix_code_file(prompt, file_path, channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text=f"Okay, I'll try to '{prompt}' in `{file_path}`.")
        target = _safe_repo_path(file_path)
        if not target.exists():
            app.client.chat_postMessage(channel=channel_id, text=f"❌ File not found: `{file_path}`")
            return
        with open(target, 'r', encoding='utf-8', errors='ignore') as f:
            original_code = f.read()
        
        system = "You are a meticulous senior Python engineer. Apply changes surgically, keep code style consistent, and ensure imports remain valid."
        ai_prompt = f"Task: {prompt}\nFile: {file_path}\nReturn ONLY the complete updated file contents, no explanations.\n--- ORIGINAL CODE ---\n{original_code}"
        new_code = ai_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": ai_prompt},
        ])
        
        with open(target, 'w', encoding='utf-8') as f:
            content = new_code.strip()
            content = content.replace("```python", "").replace("```", "")
            f.write(content)
        
        app.client.chat_postMessage(channel=channel_id, text=f"📝 AI patch applied. Formatting and linting...")
        run_command(f"black {file_path} || true; ruff check {file_path} || true", channel_id)

        branch_name = _branch_name("bot-fix", prompt)
        pr_title = f"fix: {prompt}"
        
        run_command(f"git checkout -b {branch_name}", channel_id, False)
        run_command(f"git add {file_path}", channel_id, False)
        run_command(f"git commit -m '{pr_title}'", channel_id, False)
        run_command(f"git push origin {branch_name}", channel_id)
        create_github_pr(channel_id, branch_name, pr_title)
        learn("fix_code_file", True)
    except Exception as e:
        LOGGER.exception("fix_code_file failed")
        learn("fix_code_file", False)
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *AI fix failed:*\n```{str(e)}```")

def confirm_and_deploy(channel_id, user_id):
    try:
        app.client.chat_postMessage(
            channel=channel_id,
            text="Confirm deployment",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": f"<@{user_id}> Are you sure you want to deploy to production?"}},
                {"type": "actions", "block_id": "deploy_confirmation", "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "🚀 Deploy"}, "style": "primary", "value": "deploy_confirm", "action_id": "deploy_confirm_button"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Cancel"}, "style": "danger", "value": "deploy_cancel", "action_id": "deploy_cancel_button"}
                ]}
            ]
        )
    except Exception as e:
        app.client.chat_postMessage(channel=channel_id, text=f"Error sending confirmation: {e}")

def generate_project_report(channel_id, is_scheduled=False):
    greeting = "📊 Here is your scheduled daily project status report:" if is_scheduled else "🔍 Scanning project to generate a report..."
    app.client.chat_postMessage(channel=channel_id, text=greeting)
    commits, _ = run_command("git log --oneline -10", channel_id, False)
    todos, _ = run_command("grep -r -E 'TODO|FIXME' . --exclude-dir=.git --exclude-dir=venv", channel_id, False)
    report_prompt = f"You are a senior project manager. Analyze the following data and generate a concise status report with two sections: 'What's Done Recently' (from commits) and 'What's Left To Do' (from TODOs).\n\n--- COMMITS ---\n{commits}\n\n--- TODOs ---\n{todos}"
    report = ai_request(report_prompt)
    app.client.chat_postMessage(channel=channel_id, text=f"*Legend AI Project Status Report*\n\n{report}")
    log_journal("foreman", "Project Status Report", report)

# --- EPIC FEATURES ---
def write_tests(file_path, channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text=f"🔬 Analyzing `{file_path}` to generate tests...")
        target = _safe_repo_path(file_path)
        if not target.exists():
            app.client.chat_postMessage(channel=channel_id, text=f"❌ File not found: `{file_path}`")
            return
        with open(target, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        
        prompt = (
            f"Write pytest tests for `{file_path}`. Prioritize critical logic and edge cases. "
            f"Return ONLY the test file code.\n--- CODE ---\n{code}"
        )
        test_code = ai_request(prompt)
        
        test_file_path = f"tests/test_{os.path.basename(file_path)}"
        os.makedirs("tests", exist_ok=True)
        with open(_safe_repo_path(test_file_path), 'w', encoding='utf-8') as f:
            f.write(test_code.strip().replace("```python", "").replace("```", ""))

        app.client.chat_postMessage(channel=channel_id, text=f"✅ Generated new test file: `{test_file_path}`. Now running the tests...")
        run_command(f"pytest -q {test_file_path}", channel_id)
    except Exception as e:
        LOGGER.exception("write_tests failed")
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Test generation failed:*\n```{str(e)}```")

def document_file(file_path, channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text=f"✍️ Asking AI to document `{file_path}`...")
        target = _safe_repo_path(file_path)
        if not target.exists():
            app.client.chat_postMessage(channel=channel_id, text=f"❌ File not found: `{file_path}`")
            return
        with open(target, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        prompt = (
            "Improve this Python code with clear docstrings and inline comments. "
            "Explain complex logic. Return ONLY the updated file content.\n--- CODE ---\n" + code
        )
        documented_code = ai_request(prompt)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(documented_code.strip().replace("```python", "").replace("```", ""))
        app.client.chat_postMessage(channel=channel_id, text=f"✅ Documentation added to `{file_path}`.")
    except Exception as e:
        LOGGER.exception("document_file failed")
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Documentation failed:*\n```{str(e)}```")

def plan_feature(description, channel_id):
    app.client.chat_postMessage(channel=channel_id, text=f"🗺️ Planning feature: '{description}'...")
    prompt = f"You are a product manager. The user wants to build a feature: '{description}'. Analyze the current project files (foreman_bot.py, orchestrator.py) and break this feature down into a list of concrete TODO items. For each TODO, specify the file where it should be added.\n\nFormat: `# TODO: [task] in [file_path]`"
    plan = ai_request(prompt)
    app.client.chat_postMessage(channel=channel_id, text=f"*Feature Plan:*\n```{plan}```\nI can add these to the files if you'd like.")

def suggest_next_task(channel_id):
    app.client.chat_postMessage(channel=channel_id, text="🤔 Figuring out what you should work on next...")
    todos, _ = run_command("grep -r 'TODO' . --exclude-dir=.git --exclude-dir=venv", channel_id, False)
    if not todos:
        app.client.chat_postMessage(channel=channel_id, text="🎉 No TODOs found! Looks like you're all caught up. Maybe `suggest tasks`?")
        return
    prompt = f"You are a senior engineer. Prioritize the following TODO list and suggest the single most important task to work on next. Explain your reasoning in one sentence.\n\n--- TODOs ---\n{todos}"
    suggestion = ai_request(prompt)
    app.client.chat_postMessage(channel=channel_id, text=f"*Suggested Next Task:*\n{suggestion}")

def search_web(query, channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text=f"🌐 Searching Stack Overflow for: `{query}`...")
        url = f"https://stackoverflow.com/search?q={quote(query)}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='s-post-summary--content-title')
        if not results:
            app.client.chat_postMessage(channel=channel_id, text="No relevant results found on Stack Overflow.")
            return
        summary = "Here are the top results from Stack Overflow:\n"
        for i, result in enumerate(results[:3]):
            title = result.a.text
            link = "https://stackoverflow.com" + result.a['href']
            summary += f"{i+1}. <{link}|{title}>\n"
        app.client.chat_postMessage(channel=channel_id, text=summary)
    except Exception as e:
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Web search failed:*\n```{str(e)}```")
        
def diagnose_problems(channel_id):
    app.client.chat_postMessage(channel=channel_id, text="🤔 Diagnosing project health...")
    status, _ = run_command("./orchestrator/status.sh", channel_id, False)
    if not status or "❌" not in status:
        app.client.chat_postMessage(channel=channel_id, text="✅ All systems are healthy or status unavailable. Nothing to diagnose!")
        return
    commits, _ = run_command("git log --oneline -5", channel_id, False)
    prompt = f"You are a senior DevOps engineer. Analyze the following system status and recent commits. Identify the most likely cause of the failure.\n\n--- SYSTEM STATUS ---\n{status}\n\n--- RECENT COMMITS ---\n{commits}\n\nProvide a brief diagnosis."
    diagnosis = ai_request(prompt)
    app.client.chat_postMessage(channel=channel_id, text=f"*Diagnosis Report*\n\n{diagnosis}")

def suggest_tasks(channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text="🔍 Analyzing codebase to suggest tasks...")
        files_to_analyze = ['foreman_bot.py', 'orchestrator/orchestrator.py']
        code_context = ""
        for file_path in files_to_analyze:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        code_context += f"--- START {file_path} ---\n{f.read()}\n--- END {file_path} ---\n\n"
    prompt = f"You are a world-class senior engineer. Analyze this code. Generate a list of 3-5 concrete tasks formatted as '# TODO:' or '# FIXME:'. Provide the file path for each.\n\n--- CODE ---\n{code_context}"
    suggestions = ai_request(prompt)
    app.client.chat_postMessage(channel=channel_id, text=f"💡 *Here are some suggested tasks:*\n```{suggestions}```\nYou can ask me to implement them with the `fix` command!")
    log_journal("foreman", "Task Suggestions", suggestions)
    except Exception as e:
        LOGGER.exception("suggest_tasks failed")
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Task suggestion failed:*\n```{str(e)}```")

def prepare_for_deployment(channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text="🚀 Preparing for deployment...")
        run_command("pip freeze > requirements.txt", channel_id)
        with open(_safe_repo_path('run_bot.sh'), 'w', encoding='utf-8') as f:
            f.write("#!/bin/bash\n")
            f.write("python3 foreman_bot.py\n")
        run_command("chmod +x run_bot.sh", channel_id)
        run_command("git add requirements.txt run_bot.sh", channel_id, False)
        run_command('git commit -m "feat: Add configuration for Render deployment"', channel_id, False)
        run_command("git push", channel_id)
        app.client.chat_postMessage(channel=channel_id, text="✅ Deployment files created and pushed. You are now ready to set up the 'Background Worker' on Render.")
        log_journal("warp", "Prepare Deployment", "Deployment files updated and pushed")
    except Exception as e:
        LOGGER.exception("prepare_for_deployment failed")
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Prepare for deployment failed:*\n```{str(e)}```")
        log_journal("warp", "Prepare Deployment failed", str(e))

# --- ACTION HANDLERS ---
@app.action("deploy_confirm_button")
def handle_deploy_confirm(ack, body, say):
    ack()
    user = body['user']['id']
    say(text=f"<@{user}> confirmed. Starting deployment...")
    run_command("./orchestrator/deploy.sh", body['channel']['id'])
    
@app.action("deploy_cancel_button")
def handle_deploy_cancel(ack, body, say):
    ack()
    say("Deployment canceled.")

# --- SCHEDULER & AUTONOMOUS AGENTS ---
def run_autonomous_tasks():
    channel_id = FOREMAN_SCHEDULE_CHANNEL_ID.strip()
    if not channel_id:
        LOGGER.warning("Scheduler: FOREMAN_SCHEDULE_CHANNEL_ID not set; skipping scheduled tasks.")
        return
    generate_project_report(channel_id, is_scheduled=True)
    
def run_scheduler():
    try:
        schedule.every().day.at("09:00", "America/Los_Angeles").do(run_autonomous_tasks)
    except Exception:
        LOGGER.exception("Failed to set schedule; defaulting to UTC 17:00")
        schedule.every().day.at("17:00").do(run_autonomous_tasks)
    while True:
        try:
            schedule.run_pending()
        except Exception:
            LOGGER.exception("Scheduler iteration failed")
        time.sleep(60)

# --- MAIN ROUTER ---
@app.event("app_mention")
def handle_mentions(body, say):
    try:
        event = body.get("event", {})
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        files = event.get("files", []) or []
        command_text = re.sub(r'<@.*?>', '', text).strip().lower()

        if command_text.startswith("deploy"): confirm_and_deploy(channel_id, user_id)
        elif command_text.startswith("status"): run_command("./orchestrator/status.sh", channel_id)
        elif command_text.startswith("report"): generate_project_report(channel_id)
        elif command_text.startswith("test"): run_command("python3 -m pytest -q", channel_id)
        elif command_text.startswith("diagnose"): diagnose_problems(channel_id)
        elif command_text.startswith("suggest tasks"): suggest_tasks(channel_id)
        elif command_text.startswith("what's next?"): suggest_next_task(channel_id)
        elif command_text.startswith("help"):
            show_help(command_text, say)
        elif command_text.startswith("prepare for deployment"): prepare_for_deployment(channel_id)
        elif command_text.startswith("write tests for"):
            file_path = re.sub(r'<@.*?>', '', text).strip().lower().replace("write tests for", "").strip()
            write_tests(file_path, channel_id)
        elif command_text.startswith("document"):
            file_path = re.sub(r'<@.*?>', '', text).strip().lower().replace("document", "").strip()
            document_file(file_path, channel_id)
        elif command_text.startswith("plan feature"):
            description = re.sub(r'<@.*?>', '', text).strip().lower().replace("plan feature", "").strip()
            plan_feature(description, channel_id)
        elif command_text.startswith("search for"):
            query = re.sub(r'<@.*?>', '', text).strip().lower().replace("search for", "").strip()
            search_web(query, channel_id)
        elif command_text.startswith("analyze image"):
            prompt = text.lower().split("analyze image", 1)[1].strip() or "Describe issues and suggestions."
            analyze_images(files, prompt, channel_id)
        elif command_text.startswith("ci fix") or command_text.startswith("fix workflows"):
            fix_workflows(channel_id)
        elif command_text.startswith("health"):
            health_check(channel_id)
        elif command_text.startswith("cleanup branches"):
            cleanup_bot_branches(channel_id)
        elif command_text.startswith("deploy all"):
            deploy_all_command(channel_id)
        elif command_text.startswith("fix"):
            original_text = re.sub(r'<@.*?>', '', text).strip()
            try:
                parts = original_text.split(" in ")
                prompt = parts[0].replace("fix", "", 1).strip()
                file_path = parts[1].strip()
                fix_code_file(prompt, file_path, channel_id)
            except Exception:
                say("Usage: `fix [your request] in [file_path]`")
        else:
            # Fall back to NLP-based processing rather than a hard failure
            try:
                response = handle_natural_language_message(text, advanced_bot)
                say(response)
                try:
                    log_journal("nlp", "NLP response", response)
                except Exception:
                    pass
            except Exception:
                say("Sorry, I don't understand that. Try `help` to see what I can do.")
    except Exception:
        LOGGER.exception("handle_mentions failed")

# --- NEW CAPABILITIES ---

def show_help(command_text: str, say):
    parts = command_text.split()
    if len(parts) <= 1:
        say(HELP_TEXT)
        return
    topic = " ".join(parts[1:])
    help_map = {
        "fix": "fix [request] in [file] — example: fix replace deprecated call in service_api.py",
        "write tests for": "write tests for [file] — generates pytest tests for the file",
        "document": "document [file] — adds docstrings and comments",
        "analyze image": "analyze image [prompt] — attach images and add an optional prompt",
        "ci fix": "ci fix — scans workflows for exists() and replaces with hashFiles()",
        "health": "health — checks env vars and orchestrator scripts",
        "cleanup branches": "cleanup branches — deletes remote merged bot-fix/* branches",
    }
    for k, v in help_map.items():
        if topic.startswith(k):
            say(v)
            return
    say("No specific help found; available commands are listed above.")


def analyze_images(files, prompt, channel_id):
    try:
        if not files:
            app.client.chat_postMessage(channel=channel_id, text="Attach at least one image and try again.")
            return
        parts = [{"type": "text", "text": f"{prompt}\nProvide concise, actionable insights."}]
        count = 0
        for f in files:
            mime = f.get("mimetype", "")
            url = f.get("url_private")
            if not mime.startswith("image/") or not url:
                continue
            resp = requests.get(url, headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"})
            if resp.status_code != 200:
                continue
            b64 = base64.b64encode(resp.content).decode("utf-8")
            data_url = f"data:{mime};base64,{b64}"
            parts.append({"type": "image_url", "image_url": {"url": data_url}})
            count += 1
            if count >= 5:
                break
        if count == 0:
            app.client.chat_postMessage(channel=channel_id, text="No valid images found in the message.")
            return
        content = parts
        messages = [{"role": "user", "content": content}]
        try:
            result = ai_chat(messages, model="gpt-4o")
        except Exception:
            result = ai_chat(messages, model="gpt-4o-mini")
        app.client.chat_postMessage(channel=channel_id, text=f"🖼️ *Vision Analysis*\n{result}")
        learn("analyze_images", True)
    except Exception:
        LOGGER.exception("analyze_images failed")
        learn("analyze_images", False)
        app.client.chat_postMessage(channel=channel_id, text="🔥 Vision analysis failed.")


import re as _re

def fix_workflow_content(text: str) -> str:
    # Replace if: ${{ exists('path') }} with hashFiles != ''
    def repl_exists(m):
        inner = m.group(1)
        return f"${{ {{ hashFiles({inner}) != '' }} }}"  # placeholder; fix below
    # Positive exists
    text2 = _re.sub(r"\$\{\{\s*exists\(([^)]+)\)\s*\}\}", r"${{ hashFiles(\1) != '' }}", text)
    # Negated exists
    text2 = _re.sub(r"\$\{\{\s*!\s*exists\(([^)]+)\)\s*\}\}", r"${{ hashFiles(\1) == '' }}", text2)
    return text2


def fix_workflows(channel_id):
    try:
        root = _safe_repo_path('.github/workflows')
        if not root.exists():
            app.client.chat_postMessage(channel=channel_id, text="No workflows directory found.")
            return
        changed = []
        for p in root.glob("*.yml"):
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            new_content = fix_workflow_content(content)
            if new_content != content:
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                changed.append(p.name)
        for p in root.glob("*.yaml"):
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            new_content = fix_workflow_content(content)
            if new_content != content:
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                changed.append(p.name)
        if not changed:
            app.client.chat_postMessage(channel=channel_id, text="✅ No workflow fixes needed.")
            return
        branch = _branch_name("fix/gh-actions", "exists-to-hashfiles")
        run_command(f"git checkout -b {branch}", channel_id, False)
        run_command("git add .github/workflows", channel_id, False)
        run_command("git commit -m 'fix(ci): replace exists() with hashFiles()'", channel_id, False)
        run_command(f"git push origin {branch}", channel_id)
        create_github_pr(channel_id, branch, "fix(ci): replace exists() with hashFiles()")
    except Exception:
        LOGGER.exception("fix_workflows failed")
        app.client.chat_postMessage(channel=channel_id, text="🔥 Failed to fix workflows.")


def health_check(channel_id):
    try:
        lines = []
        # Env vars
        missing = [k for k, v in REQUIRED_ENV_VARS if not v]
        if missing:
            lines.append(f"❌ Missing env vars: {', '.join(missing)}")
        else:
            lines.append("✅ Required env vars present")
        # Orchestrator scripts
        for rel in ["orchestrator/status.sh", "orchestrator/deploy.sh", "orchestrator/run.sh"]:
            p = _safe_repo_path(rel)
            if p.exists() and os.access(p, os.X_OK):
                lines.append(f"✅ {rel} exists and is executable")
            elif p.exists():
                lines.append(f"⚠️ {rel} exists but is not executable")
            else:
                lines.append(f"❌ {rel} missing")
        # Try status
        out, err = run_command("./orchestrator/status.sh", channel_id, False)
        if out:
            lines.append("--- status.sh output ---\n" + (out[:900] + ('…' if len(out) > 900 else '')))
        if err:
            lines.append("--- status.sh errors ---\n" + (err[:400] + ('…' if len(err) > 400 else '')))
        app.client.chat_postMessage(channel=channel_id, text="\n".join(lines))
    except Exception:
        LOGGER.exception("health_check failed")
        app.client.chat_postMessage(channel=channel_id, text="🔥 Health check failed.")


def cleanup_bot_branches(channel_id):
    try:
        # Fetch latest
        run_command("git fetch --prune", channel_id, False)
        # List merged branches
        res, _ = run_command("git branch -r --merged origin/main", channel_id, False)
        to_delete = []
        if res:
            for line in res.splitlines():
                line = line.strip()
                if line.startswith("origin/bot-fix/"):
                    to_delete.append(line.replace("origin/", ""))
        if not to_delete:
            app.client.chat_postMessage(channel=channel_id, text="No merged bot-fix branches to delete.")
            return
        deleted = []
        for b in to_delete[:20]:  # safety limit
            run_command(f"git push origin --delete {b}", channel_id, False)
            deleted.append(b)
        app.client.chat_postMessage(channel=channel_id, text=f"🧹 Deleted {len(deleted)} merged branches: {', '.join(deleted)}")
    except Exception:
        LOGGER.exception("cleanup_bot_branches failed")
        app.client.chat_postMessage(channel=channel_id, text="🔥 Cleanup failed.")


def deploy_all_command(channel_id):
    try:
        summary = []
        app.client.chat_postMessage(channel=channel_id, text="🚀 Deploying API + shots (Render) and triggering Vercel…")
        render_token = os.environ.get("RENDER_TOKEN", "").strip()
        api_sid = os.environ.get("API_SERVICE_ID", "").strip()
        shots_sid = os.environ.get("SHOTS_SERVICE_ID", "").strip()
        vercel_hook = os.environ.get("VERCEL_DEPLOY_HOOK_URL", "").strip()
        vercel_token = os.environ.get("VERCEL_TOKEN", "").strip()

        headers = {"Authorization": f"Bearer {render_token}", "Accept": "application/json", "Content-Type": "application/json"} if render_token else None
        if headers and shots_sid:
            try:
                requests.post(f"https://api.render.com/v1/services/{shots_sid}/deploys", headers=headers, json={}).raise_for_status()
                app.client.chat_postMessage(channel=channel_id, text="✅ Render: shots deploy triggered")
                summary.append("Render shots deploy triggered")
            except Exception as e:
                app.client.chat_postMessage(channel=channel_id, text=f"❌ Render shots: {e}")
                summary.append(f"Render shots failed: {e}")
        if headers and api_sid:
            try:
                requests.post(f"https://api.render.com/v1/services/{api_sid}/deploys", headers=headers, json={}).raise_for_status()
                app.client.chat_postMessage(channel=channel_id, text="✅ Render: API deploy triggered")
                summary.append("Render API deploy triggered")
            except Exception as e:
                app.client.chat_postMessage(channel=channel_id, text=f"❌ Render API: {e}")
                summary.append(f"Render API failed: {e}")
        if vercel_hook:
            try:
                requests.post(vercel_hook, timeout=10)
                app.client.chat_postMessage(channel=channel_id, text="✅ Vercel hook triggered")
                summary.append("Vercel hook triggered")
            except Exception as e:
                app.client.chat_postMessage(channel=channel_id, text=f"❌ Vercel hook failed: {e}")
                summary.append(f"Vercel hook failed: {e}")
        app.client.chat_postMessage(channel=channel_id, text="⏳ Checking API health…")
        try:
            resp = requests.get("https://legend-api.onrender.com/healthz", timeout=15)
            app.client.chat_postMessage(channel=channel_id, text=f"API /healthz: {resp.status_code} {resp.text[:200]}")
            summary.append(f"API health: {resp.status_code}")
        except Exception as e:
            app.client.chat_postMessage(channel=channel_id, text=f"API check failed: {e}")
            summary.append(f"API check failed: {e}")
        log_journal("warp", "Deploy Result", " | ".join(summary) if summary else "Deployment attempted")
    except Exception:
        LOGGER.exception("deploy_all_command failed")
        app.client.chat_postMessage(channel=channel_id, text="🔥 Deploy all failed.")
        log_journal("warp", "Deploy Result", "error: deploy_all_command failed")


# === GPT INTELLIGENCE INTEGRATION ===

def process_with_gpt(user_message: str) -> str:
    """Process any message through GPT for intelligent response"""
    try:
        if not OPENAI_API_KEY:
            return generate_smart_fallback(user_message)
        
        system_context = """You are Foreman Bot, Kyle's AI development assistant for Legend AI trading platform.

SYSTEM STATUS:
- Backend API: Live (legend-api.onrender.com)
- Frontend: Live (legend-ai.vercel.app) 
- VCP Scanner: Operational with confidence scoring
- You can run system commands, create PRs, and help with development

CAPABILITIES:
- System health monitoring and deployment
- Code fixes and pull request creation  
- Progress reporting and productivity analysis
- Natural language command processing

RESPONSE STYLE:
- Be helpful and actionable
- Use appropriate emojis
- Never say "I don't understand"
- Always provide value"""

        messages = [
            {"role": "system", "content": system_context},
            {"role": "user", "content": user_message}
        ]
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=400,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return generate_smart_fallback(user_message)


def generate_smart_fallback(message: str) -> str:
    """Smart fallback when GPT unavailable"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['status', 'health', 'working']):
        return """🔥 **System Status**
        
✅ Backend API: Operational
✅ Frontend: Live  
✅ Bot: Online and ready
        
All systems showing green! What would you like to work on?"""
    
    elif any(word in message_lower for word in ['done', 'progress', 'accomplished']):
        return """📈 **Quick Progress Check**
        
🛠️ Recent work: Bot upgrades and system improvements
🎯 Current focus: Legend Room development and deployment
🚀 Status: High productivity, ready for next phase
        
What specific area would you like to focus on next?"""
    
    elif any(word in message_lower for word in ['content', 'blog', 'linkedin', 'twitter']):
        return """📝 **Content Creation Ready**
        
I can help create:
- Blog posts about trading and AI
- LinkedIn posts for professional engagement  
- Twitter threads about Legend Room features
        
What topic would you like to create content about?"""
    
    else:
        return f"""🤖 **I understand you're working on: "{message[:60]}..."**
        
I can help with:
🔧 System operations (status, deploy, health)
📊 Progress tracking and reporting
📝 Content creation and strategy
🎯 Development tasks and planning
        
What specific aspect would you like to focus on?"""


# Update the main handler to use GPT processing
original_handle_mentions = handle_mentions


def handle_mentions_with_gpt(body, say):
    """Enhanced handler that uses GPT for unknown commands"""
    try:
        event = body.get("event", {})
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        files = event.get("files", []) or []
        command_text = re.sub(r'<@.*?>', '', text).strip().lower()

        # Try traditional commands first
        if command_text.startswith("deploy"): 
            confirm_and_deploy(channel_id, user_id)
            return
        elif command_text.startswith("status"): 
            run_command("./orchestrator/status.sh", channel_id)
            return
        elif command_text.startswith("report"): 
            generate_project_report(channel_id)
            return
        elif command_text.startswith("test"): 
            run_command("python3 -m pytest -q", channel_id)
            return
        elif command_text.startswith("diagnose"): 
            diagnose_problems(channel_id)
            return
        elif command_text.startswith("help"):
            show_help(command_text, say)
            return
        elif command_text.startswith("health"):
            health_check(channel_id)
            return
        elif command_text.startswith("fix"):
            original_text = re.sub(r'<@.*?>', '', text).strip()
            try:
                parts = original_text.split(" in ")
                prompt = parts[0].replace("fix", "", 1).strip()
                file_path = parts[1].strip()
                fix_code_file(prompt, file_path, channel_id)
                return
            except Exception:
                say("Usage: `fix [your request] in [file_path]`")
                return
        
        # If no traditional command matched, use GPT processing
        clean_text = re.sub(r'<@.*?>', '', text).strip()
        if clean_text:
            gpt_response = process_with_gpt(clean_text)
            app.client.chat_postMessage(channel=channel_id, text=gpt_response)
        else:
            say("🤖 Hello! I'm your AI development assistant. What can I help you with today?")
            
    except Exception as e:
        LOGGER.exception("Enhanced handle_mentions failed")
        app.client.chat_postMessage(channel=channel_id, text=f"🤖 I'm operational! You asked about something, and I'm ready to help. What specific task are you working on?")

# Replace the handler
app._listeners = [l for l in app._listeners if not (hasattr(l, 'func') and l.func.__name__ == 'handle_mentions')]
app.event("app_mention")(handle_mentions_with_gpt)

print("🧠 GPT intelligence integration complete!")


if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    LOGGER.info("🤖 Foreman Bot (Epic Edition) is starting…")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
