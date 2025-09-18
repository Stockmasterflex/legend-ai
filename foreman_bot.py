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

# --- CONFIGURATION ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

app = slack_bolt.App(token=SLACK_BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

# --- HELP TEXT ---
HELP_TEXT = """
*Foreman Bot (Epic Edition)* - Your AI Development Partner

*Code & Quality*
- `fix [request] in [file]`: Fixes code and opens a GitHub PR.
- `write tests for [file]`: Generates a new `test_[file]` with pytest tests.
- `document [file]`: Adds docstrings and comments to a file.
- `refactor [request]`: Performs a project-wide refactor (experimental).

*Strategy & Planning*
- `plan feature [description]`: Breaks down a feature into TODOs and adds them to the code.
- `what's next?`: Suggests the next logical task from existing TODOs.
- `brainstorm [idea]`: Generates a technical plan for a new idea.
- `prepare release [vX.X.X]`: Drafts release notes for a new version tag.

*Diagnostics & Knowledge*
- `status` / `deploy`: Basic orchestrator commands.
- `diagnose`: Finds the likely cause of a service failure.
- `teach me about [file]`: Explains a file's purpose and logic.
- `search for [error]`: Searches Stack Overflow for a solution to an error.

*Deployment*
- `prepare for deployment`: Creates the necessary files for deploying me to Render.

*Autonomous Actions*
- I post a project report every morning at 9 AM PST.
"""

# --- HELPER FUNCTIONS ---
def run_command(command, channel_id, post_to_slack=True):
    try:
        if post_to_slack: app.client.chat_postMessage(channel=channel_id, text=f"🤖 Running: `{command}`")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        if post_to_slack:
            output = f"✅ *Succeeded*\n"
            if result.stdout: output += f"```{result.stdout}```"
            if result.stderr: output += f"🚨 *Errors/Warnings:*\n```{result.stderr}```"
            app.client.chat_postMessage(channel=channel_id, text=output)
        return result.stdout, result.stderr
    except Exception as e:
        if post_to_slack: app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Command Failed:*\n```{str(e)}```")
        return None, str(e)

def create_github_pr(channel_id, branch_name, title, body=""):
    if not GITHUB_USERNAME or not GITHUB_REPO:
        app.client.chat_postMessage(channel=channel_id, text="⚠️ `GITHUB_USERNAME` and `GITHUB_REPO` are not set. Cannot create PR.")
        return
    pr_url = f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}/compare/main...{branch_name}?expand=1&title={quote(title)}&body={quote(body)}"
    app.client.chat_postMessage(channel=channel_id, text=f"✅ Pushed changes to branch `{branch_name}`.\n*Click here to create a Pull Request:* <{pr_url}|Review Changes>")

def ai_request(prompt, model="gpt-4-turbo"):
    response = openai.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content

# --- CORE COMMANDS ---
def fix_code_file(prompt, file_path, channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text=f"Okay, I'll try to '{prompt}' in `{file_path}`.")
        with open(file_path, 'r') as f:
            original_code = f.read()
        
        ai_prompt = f"Expert software engineer task: '{prompt}'.\nOriginal code from '{file_path}':\n```{original_code}```\nProvide only the complete, updated file content."
        new_code = ai_request(ai_prompt)
        
        with open(file_path, 'w') as f:
            f.write(new_code.strip().replace("```python", "").replace("```", ""))
        
        app.client.chat_postMessage(channel=channel_id, text=f"📝 AI patch applied. Formatting and linting (Pre-Commit Guardian)...")
        run_command(f"black {file_path}; flake8 {file_path}", channel_id)

        branch_name = f"bot-fix/{prompt.replace(' ', '-').lower()[:30]}"
        pr_title = f"fix: {prompt}"
        
        run_command(f"git checkout -b {branch_name}", channel_id, False)
        run_command(f"git add {file_path}", channel_id, False)
        run_command(f"git commit -m '{pr_title}'", channel_id, False)
        run_command(f"git push origin {branch_name}", channel_id)
        create_github_pr(channel_id, branch_name, pr_title)
    except Exception as e:
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

# --- EPIC FEATURES ---
def write_tests(file_path, channel_id):
    try:
        app.client.chat_postMessage(channel=channel_id, text=f"🔬 Analyzing `{file_path}` to generate tests...")
        with open(file_path, 'r') as f:
            code = f.read()
        
        prompt = f"You are a test engineer. Analyze the following code from `{file_path}` and write a new Python file with comprehensive pytest tests for it. The tests should be practical and cover key functionality and edge cases. Provide only the raw code for the new test file.\n\n--- CODE ---\n{code}"
        test_code = ai_request(prompt)
        
        test_file_path = f"tests/test_{os.path.basename(file_path)}"
        os.makedirs("tests", exist_ok=True)
        with open(test_file_path, 'w') as f:
            f.write(test_code.strip().replace("```python", "").replace("```", ""))

        app.client.chat_postMessage(channel=channel_id, text=f"✅ Generated new test file: `{test_file_path}`. Now running the tests...")
        run_command(f"pytest {test_file_path}", channel_id)
    except Exception as e:
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Test generation failed:*\n```{str(e)}```")

def document_file(file_path, channel_id):
    app.client.chat_postMessage(channel=channel_id, text=f"✍️ Asking AI to document `{file_path}`...")
    with open(file_path, 'r') as f:
        code = f.read()
    prompt = f"You are a technical writer. Add clear, concise comments and docstrings to the following Python code. Explain complex logic. Return the fully documented code file.\n\n--- CODE ---\n{code}"
    documented_code = ai_request(prompt)
    with open(file_path, 'w') as f:
        f.write(documented_code.strip().replace("```python", "").replace("```", ""))
    app.client.chat_postMessage(channel=channel_id, text=f"✅ Documentation added to `{file_path}`.")

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
    if "❌" not in status:
        app.client.chat_postMessage(channel=channel_id, text="✅ All systems are healthy. Nothing to diagnose!")
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
                with open(file_path, 'r') as f:
                    code_context += f"--- START {file_path} ---\n{f.read()}\n--- END {file_path} ---\n\n"
        prompt = f"You are a world-class senior engineer. Analyze this code. Generate a list of 3-5 concrete tasks formatted as '# TODO:' or '# FIXME:'. Provide the file path for each.\n\n--- CODE ---\n{code_context}"
        suggestions = ai_request(prompt)
        app.client.chat_postMessage(channel=channel_id, text=f"💡 *Here are some suggested tasks:*\n```{suggestions}```\nYou can ask me to implement them with the `fix` command!")
    except Exception as e:
        app.client.chat_postMessage(channel=channel_id, text=f"🔥 *Task suggestion failed:*\n```{str(e)}```")

def prepare_for_deployment(channel_id):
    app.client.chat_postMessage(channel=channel_id, text="🚀 Preparing for deployment...")
    run_command("pip freeze > requirements.txt", channel_id)
    with open('run_bot.sh', 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("python3 foreman_bot.py\n")
    run_command("chmod +x run_bot.sh", channel_id)
    run_command("git add requirements.txt run_bot.sh", channel_id, False)
    run_command('git commit -m "feat: Add configuration for Render deployment"', channel_id, False)
    run_command("git push", channel_id)
    app.client.chat_postMessage(channel=channel_id, text="✅ Deployment files created and pushed. You are now ready to set up the 'Background Worker' on Render.")

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
    # IMPORTANT: Replace this placeholder with your actual channel ID!
    # How to find it: Right-click the channel name in Slack -> "Copy" -> "Copy Link".
    # The ID starts with 'C' and is at the end of the URL.
    channel_id = "C097P0L5A2Q" # Replace with your #all-legend-ai channel ID
    
    if channel_id == "YOUR_CHANNEL_ID_HERE":
        print("Scheduler Warning: Please set a channel_id in foreman_bot.py for scheduled tasks.")
        return

    generate_project_report(channel_id, is_scheduled=True)
    
def run_scheduler():
    schedule.every().day.at("09:00", "America/Los_Angeles").do(run_autonomous_tasks)
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- MAIN ROUTER ---
@app.event("app_mention")
def handle_mentions(body, say):
    text = body["event"]["text"]
    user_id = body["event"]["user"]
    channel_id = body["event"]["channel"]
    command_text = re.sub(r'<@.*?>', '', text).strip().lower()

    if command_text.startswith("deploy"): confirm_and_deploy(channel_id, user_id)
    elif command_text.startswith("status"): run_command("./orchestrator/status.sh", channel_id)
    elif command_text.startswith("report"): generate_project_report(channel_id)
    elif command_text.startswith("test"): run_command("python3 -m pytest", channel_id)
    elif command_text.startswith("diagnose"): diagnose_problems(channel_id)
    elif command_text.startswith("suggest tasks"): suggest_tasks(channel_id)
    elif command_text.startswith("what's next?"): suggest_next_task(channel_id)
    elif command_text.startswith("help"): say(HELP_TEXT)
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
        say(f"Sorry, I don't understand that. Try `help` to see what I can do.")

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("🤖 Foreman Bot (Epic Edition) is starting...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
