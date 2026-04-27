#!/bin/bash
# Retrieves all tmux panes and their recent history (last 100 lines)

panes=$(tmux list-panes -a -F "#{pane_id} | Session: #{session_name} | Window: #{window_name} | Pane Index: #{pane_index} | Top: #{pane_top} | Left: #{pane_left} | Width: #{pane_width} | Height: #{pane_height} | Command: #{pane_current_command} | Path: #{pane_current_path}" 2>/dev/null || echo "No tmux panes found")

echo "=== TMUX PANES ==="
echo "$panes"
echo ""

if [ "$panes" != "No tmux panes found" ]; then
    for pane_id in $(tmux list-panes -a -F "#{pane_id}" 2>/dev/null); do
        echo "--- PANE $pane_id ---"
        pane_path=$(tmux display-message -p -t "$pane_id" -F "#{pane_current_path}")
        echo "Path: $pane_path"
        
        git_branch=$(git -C "$pane_path" branch --show-current 2>/dev/null)
        if [ -n "$git_branch" ]; then
            echo "Git Branch: $git_branch"
        fi
        
        echo "History (last 100 lines):"
        tmux capture-pane -p -t "$pane_id" -S -100 2>/dev/null || echo "Could not capture pane $pane_id"
        echo ""
    done
fi
