# Advanced Foreman Bot Intelligence module
import json
import re
import datetime
import os
from pathlib import Path
from typing import Dict, List, Any


class AdvancedBotIntelligence:
    def __init__(self):
        self.tool_results_db = Path('.orchestrator/tool_results.jsonl')
        self.conversation_context: List[Dict[str, Any]] = []
        self.natural_language_patterns = {
            'log_result': [r'result', r'got back', r'tool returned', r"here's what", r'output'],
            'status_query': [r'what.*done', r'progress', r'status', r'summary'],
            'next_steps': [r'what.*next', r'todo', r'should.*do', r'priorities'],
            'upgrade_request': [r'upgrade.*yourself', r'improve.*bot', r'add.*feature', r'enhance'],
        }

    def parse_natural_language(self, message: str) -> Dict[str, Any]:
        message_lower = message.lower()
        intent = 'unknown'
        confidence = 0.0
        for intent_type, patterns in self.natural_language_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    intent = intent_type
                    confidence = 0.8
                    break
        extracted_data = {
            'intent': intent,
            'confidence': confidence,
            'original_message': message,
            'timestamp': datetime.datetime.now().isoformat(),
            'extracted_entities': self.extract_entities(message)
        }
        return extracted_data

    def extract_entities(self, message: str) -> Dict[str, List[str]]:
        entities = {
            'symbols': re.findall(r'\b[A-Z]{2,5}\b', message),
            'numbers': re.findall(r'\d+(?:\.\d+)?', message),
            'tools': re.findall(r'\b(?:warp|cursor|claude|vercel|render|slack)\b', message.lower()),
            'actions': re.findall(r'\b(?:deploy|fix|test|scan|analyze|build)\b', message.lower()),
        }
        return {k: v for k, v in entities.items() if v}

    def log_tool_result(self, tool_name: str, result_data: Any, user_message: str = "") -> str:
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'tool': tool_name,
            'result_type': type(result_data).__name__,
            'result_data': result_data,
            'user_context': user_message,
            'session_id': datetime.datetime.now().strftime('%Y%m%d'),
            'metadata': {
                'success': 'error' not in str(result_data).lower(),
                'data_size': len(str(result_data)),
                'entities': self.extract_entities(str(result_data))
            }
        }
        os.makedirs('.orchestrator', exist_ok=True)
        with open(self.tool_results_db, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
        return f"✅ Logged {tool_name} result (Session: {log_entry['session_id']})"

    def generate_progress_report(self, timeframe: str = 'today') -> str:
        if not self.tool_results_db.exists():
            return "📊 No tool results logged yet. Start logging your work!"
        entries: List[Dict[str, Any]] = []
        cutoff_date = datetime.datetime.now()
        if timeframe == 'today':
            cutoff_date = cutoff_date.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            with open(self.tool_results_db, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    entry_time = datetime.datetime.fromisoformat(entry['timestamp'])
                    if entry_time >= cutoff_date:
                        entries.append(entry)
        except Exception:
            entries = []
        if not entries:
            return f"📊 No activity logged {timeframe}."
        tools_used: Dict[str, int] = {}
        successes = 0
        failures = 0
        for entry in entries:
            tool = entry.get('tool', 'unknown')
            tools_used[tool] = tools_used.get(tool, 0) + 1
            if entry.get('metadata', {}).get('success'):
                successes += 1
            else:
                failures += 1
        report_lines = [
            f"📊 **Progress Report ({timeframe.title()})**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🔧 **Tools Used:** {', '.join(f'{k}({v})' for k, v in tools_used.items())}",
            f"✅ **Successes:** {successes}",
            f"❌ **Issues:** {failures}",
            f"📈 **Productivity:** {len(entries)} total actions",
            "",
            "🎯 **Key Activities:",
        ]
        for e in entries[-5:]:
            ctx = (e.get('user_context') or '')[:50]
            report_lines.append(f"• {e.get('tool','?')}: {ctx}...")
        report_lines.append("")
        report_lines.append("🚀 **System Status:** " + ("🟢 High Productivity" if len(entries) > 5 else "🟡 Building Momentum"))
        return '\n'.join(report_lines)

    def suggest_next_steps(self) -> str:
        if not self.tool_results_db.exists():
            return "🎯 **Suggested Next Steps:**\n• Start logging your tool results\n• Run system health checks\n• Begin demo data population"
        recent_tools: List[str] = []
        try:
            with open(self.tool_results_db, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    entry = json.loads(line)
                    recent_tools.append(entry.get('tool', 'unknown'))
        except Exception:
            pass
        suggestions: List[str] = []
        if 'vercel' in recent_tools:
            suggestions += ["• Monitor Vercel deployment status", "• Test frontend functionality end-to-end"]
        if 'warp' in recent_tools:
            suggestions += ["• Commit and push recent changes", "• Run comprehensive system tests"]
        if len(set(recent_tools)) > 3:
            suggestions += ["• Create progress documentation", "• Consider system optimization"]
        if not suggestions:
            suggestions = [
                "• Continue current development workflow",
                "• Add more comprehensive logging",
                "• Plan next major feature implementation",
            ]
        return "🎯 **AI-Suggested Next Steps:**\n" + "\n".join(suggestions)

    def self_upgrade_request(self, upgrade_description: str) -> str:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        branch_name = f"bot-self-upgrade-{timestamp}"
        upgrade_plan = f"""
🤖 **Bot Self-Upgrade Initiated**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **Requested Enhancement:** {upgrade_description}
🌿 **Upgrade Branch:** {branch_name}
⏰ **Started:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔄 **Safe Upgrade Process:**
1. Create isolated upgrade branch
2. Implement requested features
3. Test in isolation
4. Create PR for review
5. Auto-merge if tests pass
6. Restart with new capabilities

⚡ **Status:** Upgrade request logged and queued
        """
        self.log_tool_result('bot_upgrade', {
            'upgrade_description': upgrade_description,
            'branch_name': branch_name,
            'status': 'requested',
            'timestamp': timestamp
        })
        return upgrade_plan.strip()


def handle_natural_language_message(message: str, bot_intelligence: AdvancedBotIntelligence) -> str:
    parsed = bot_intelligence.parse_natural_language(message)
    if parsed['intent'] == 'log_result':
        tool_match = re.search(r'(warp|cursor|claude|vercel|render|slack)', message.lower())
        tool_name = tool_match.group(1) if tool_match else 'unknown_tool'
        return bot_intelligence.log_tool_result(tool_name, message, message)
    elif parsed['intent'] == 'status_query':
        return bot_intelligence.generate_progress_report()
    elif parsed['intent'] == 'next_steps':
        return bot_intelligence.suggest_next_steps()
    elif parsed['intent'] == 'upgrade_request':
        return bot_intelligence.self_upgrade_request(message)
    else:
        return f"🤖 I understand you said: '{message[:100]}...'\nLet me analyze this and respond appropriately."