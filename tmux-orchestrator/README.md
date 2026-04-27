# Tmux Orchestrator

This directory contains the Python FastAPI daemon (`main.py`) and bash script (`get_tmux_context.sh`) used to summarize active tmux panes via the Gemini CLI.

**Note:** By default, this service is baked directly into the user's Workstation Pod during image build via a Dockerfile snippet (e.g., `templates/Dockerfile.template`).

This directory exists primarily for local testing and debugging of the orchestrator API.

## Local Testing
1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn
   ```
2. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001
   ```
3. Test the endpoint:
   ```bash
   curl http://localhost:8001/api/panes
   ```
