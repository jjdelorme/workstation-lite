# Workstation Lite - Agent Instructions

This file provides comprehensive guidance for AI agents (Claude, Gemini, etc.) working with code in this repository.

## Project Overview
**Workstation Lite** is a cloud workstation orchestration platform for managing developer environments on Google Cloud Platform (GCP). It provides a web UI to provision, manage, and connect to remote dev environments running as Pods on GKE (Autopilot). Deployed to Google Cloud Run.

## Core Concepts
1. **Infrastructure**: The "foundational slab" (GKE + Network). One-time setup.
2. **Images (Templates)**: These are the Blueprints.
    * **Stored as**: Dockerfile source in a ConfigMap + Binary in Artifact Registry.
    * **Lifecycle**: Create (Build) -> List -> View Source -> Edit (Rebuild).
3. **Workstations (Instances)**: These are the Living Environments.
    * **Stored as**: A K8s StatefulSet (Compute) + a PVC (Storage).
    * **Lifecycle**: Create from a Template -> Start -> Stop -> Delete.
    * **Storage Logic**: Since each workstation is a unique instance, **deleting** a workstation should destroy both the compute and the storage. This ensures no "dangling disks" are left behind accumulating costs and cluttering the workspace.
4. **Services**: Non-workstation pods (databases, caches, queues) running alongside workstations in the same namespace, accessible via Kubernetes DNS.
    * **Catalog Templates**: Stored in a `service-catalog-templates` ConfigMap in the `default` namespace. Seeded from Python defaults on first access, then the ConfigMap is the source of truth.
    * **Instance Configs**: Stored per-user in a `service-configs` ConfigMap in the user's namespace. All fields (image, ports, env vars, mount path, health check, resources) are user-editable.
    * **Stored as**: A K8s StatefulSet (`svc-` prefix) + PVC + ClusterIP Service.
    * **Lifecycle**: Create (save config) -> Start -> Stop -> Delete.
    * **Connectivity**: ClusterIP services provide in-cluster DNS (`svc-<name>:<port>`). Connect/exec scripts generate `kubectl port-forward` and `kubectl exec` commands for local access.

## Architecture
- **Monolith Deployment:** The FastAPI backend serves the React SPA from its `static` directory. Frontend assets are built and copied there via Dockerfile multi-stage build.
- **API Prefix:** All backend routes are mounted under `/api`. The FastAPI SPA middleware catches non-API 404s and serves `index.html` for client-side routing.
- **Dev Proxy:** Vite dev server proxies `/api` requests to the backend at `localhost:8080`.

### Project Structure
- `backend/app/main.py`: FastAPI app entry point, mounts routers and SPA middleware.
- `backend/app/api/`: REST API endpoints (`health.py`, `admin.py`, `workstations.py`, `services.py`).
- `backend/app/services/`: Integration logic for GCP services (GKE, Cloud Build, Artifact Registry, etc.).
- `backend/app/models/`: Pydantic models for request/response validation.
- `backend/app/core/config.py`: App configuration via pydantic-settings.
- `frontend/src/`: React 19 + TypeScript + MUI + React Router application. Monaco Editor is used for in-browser Dockerfile editing.
- `plans/`: Project roadmaps, phase plans, and audit reports.

## Building and Running

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
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

**Important:** The backend serves the frontend from `backend/app/static/`, not from `frontend/dist/`. After rebuilding the frontend, copy the output to the backend:
```bash
rm -rf backend/app/static && cp -r frontend/dist backend/app/static
```
This allows you to update the UI without restarting the backend server — just refresh the browser.

### Tests
```bash
cd backend && pytest                              # All backend tests
cd backend && pytest tests/test_foo.py            # Single test file
cd backend && pytest tests/test_foo.py::test_bar  # Single test
```

### Deployment
```bash
./deploy.sh   # Builds Docker image and deploys to Cloud Run (requires authentication)
```

### Access Control
The Cloud Run service requires authentication (no public access). To grant a user access:
```bash
gcloud run services add-iam-policy-binding workstation-lite \
  --region us-central1 \
  --member="user:someone@example.com" \
  --role="roles/run.invoker"
```

To access the app in a browser, use the Cloud Run proxy (injects auth tokens automatically):
```bash
gcloud run services proxy workstation-lite --region us-central1 --port 3333
# Then open http://localhost:3333
```

## Development Conventions
- **Python:** PEP 8 compliant, using `pydantic` for validation and `FastAPI` for routing.
- **TypeScript:** Strict type checking, functional React components with hooks.
- **Styling:** Material UI components with Emotion-based styling. Prefer native MUI paradigms.

## Important Notes & Gotchas
- **Segfault Fix:** `main.py` sets `CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false` and `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` at module load. This prevents fatal segmentation faults during mTLS cert provider execution. **Do not remove these lines or move them after GCP imports.**
- `nuke_everything.py` destroys all project resources. Use with extreme caution.
- Root-level `test_*.py` files are ad-hoc integration/debugging scripts and are **not** part of the formal test suite (which lives in `backend/tests/`).
