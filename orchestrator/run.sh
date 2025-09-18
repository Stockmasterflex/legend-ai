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
