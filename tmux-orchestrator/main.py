from fastapi import FastAPI, HTTPException
import subprocess
import json
import os
import sys

app = FastAPI(title="Tmux Summarizer API")

TMUX_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "get_tmux_context.sh")

@app.get("/api/panes")
async def get_tmux_summaries():
    try:
        if not os.path.exists(TMUX_SCRIPT_PATH):
            raise HTTPException(status_code=500, detail="Tmux summarizer script not found.")
            
        tmux_context = subprocess.run(["bash", TMUX_SCRIPT_PATH], capture_output=True, text=True, check=True)
        raw_output = tmux_context.stdout
        
        prompt = f"""
Using the provided Tmux terminal context, analyze the history of each pane.

For each pane, determine:
1. "initial_intent": The overall goal or reason this session was started.
2. "working_directory": The directory path.
3. "git_branch": The active git branch (or null).
4. "task_summary": What specific task or process is currently running.
5. "status": The state of the process (e.g. RUNNING, WAITING, ERROR).
6. "pane_index": The tmux pane index (e.g. 0, 1, 2).
7. "layout": An object containing the pane's exact coordinates and dimensions extracted from the header (e.g. {{"top": 0, "left": 84, "width": 158, "height": 42}}). Convert these string values to numbers.

Return a structured JSON array summarizing them. Keys: pane_id, window_name, pane_index, command, status, initial_intent, working_directory, git_branch, task_summary, layout.
Return ONLY valid JSON array without any markdown formatting.

<tmux_context>
{raw_output}
</tmux_context>
"""
        
        command = ["gemini", "-p", prompt, "--output-format", "json"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        cli_output = json.loads(result.stdout)
        response_text = cli_output.get("response", "[]")
        
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
            
        panes_data = json.loads(response_text)
        return {"panes": panes_data}

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute process: {e.stderr}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
