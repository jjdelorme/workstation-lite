# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Workstation Lite** is a cloud workstation orchestration platform for managing developer environments on GCP. It provides a web UI to provision, manage, and connect to remote dev environments running as Pods on GKE Autopilot. Deployed to Google Cloud Run.

## Build & Run Commands

### Backend (FastAPI)
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev          # Dev server with HMR (proxies /api to localhost:8080)
npm run build        # Production build (tsc -b && vite build)
npm run lint         # ESLint
```

### Tests
```bash
cd backend && pytest              # All backend tests
cd backend && pytest tests/test_foo.py       # Single test file
cd backend && pytest tests/test_foo.py::test_bar  # Single test
```

### Deployment
```bash
./deploy.sh   # Builds Docker image and deploys to Cloud Run
```

## Architecture

- **Monolith deployment**: FastAPI serves the React SPA from `backend/app/static/` (built frontend assets copied there via Dockerfile multi-stage build).
- **API prefix**: All backend routes are mounted under `/api`. The FastAPI SPA middleware catches non-API 404s and serves `index.html` for client-side routing.
- **Dev proxy**: Vite dev server proxies `/api` requests to the backend at `localhost:8080`.

### Backend (`backend/app/`)
- `main.py` — FastAPI app entry point, mounts routers and SPA middleware
- `api/` — Route handlers: `health.py`, `workstations.py`, `admin.py`
- `services/` — GCP integration: `gke.py`, `k8s.py`, `cloud_build.py`, `artifact_registry.py`, `compute.py`, `service_usage.py`
- `models/workstation.py` — Pydantic models for request/response validation
- `core/config.py` — App configuration via pydantic-settings

### Frontend (`frontend/src/`)
- React 19 + TypeScript + MUI (Material UI) + React Router
- `App.tsx` — Main app with routing
- `components/` — `WorkstationEditor.tsx`, `NewWorkstationDialog.tsx`, `ConnectionInstructions.tsx`
- `theme.ts` — Material Design 3 theme configuration
- Monaco Editor for in-browser Dockerfile editing

### Key Concepts
- **Images (Templates)**: Dockerfile source in ConfigMaps + built images in Artifact Registry. Lifecycle: Create → Build → List → Edit.
- **Workstations (Instances)**: K8s StatefulSet + PVC pairs. Lifecycle: Create → Start → Stop → Delete. Deleting destroys both compute and storage.

### GCP Services Used
- GKE Autopilot (workstation compute), Artifact Registry (images), Cloud Build (image builds), Cloud Run (control plane hosting)

## Important Notes

- `main.py` sets `CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false` and `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` at module load to prevent segfaults during mTLS cert provider execution.
- `start.sh` is a local utility for port-forwarding and connecting to a running workstation pod via kubectl.
- `nuke_everything.py` destroys all project resources — use with extreme caution.
- Root-level `test_*.py` files are ad-hoc integration/debugging scripts, not part of the test suite.
