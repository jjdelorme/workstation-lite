#!/bin/bash
# Retrieves all tmux panes and their recent history (last 100 lines)

panes=$(tmux list-panes -a -F "#{pane_id} | Session: #{session_name} | Window: #{window_name} | Command: #{pane_current_command}" 2>/dev/null || echo "No tmux panes found")

echo "=== TMUX PANES ==="
echo "$panes"
echo ""

if [ "$panes" != "No tmux panes found" ]; then
    for pane_id in $(tmux list-panes -a -F "#{pane_id}" 2>/dev/null); do
        echo "--- PANE $pane_id ---"
        tmux capture-pane -p -t "$pane_id" -S -100 2>/dev/null || echo "Could not capture pane $pane_id"
        echo ""
    done
fi
