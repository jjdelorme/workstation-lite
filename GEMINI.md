# GEMINI.md - Workstation Lite

## Project Overview
**Workstation Lite** is a cloud workstation orchestration platform designed to manage developer environments on Google Cloud Platform (GCP). It provides a user-friendly interface to provision, manage, and connect to remote development environments running on Google Kubernetes Engine (GKE).

## Core Concepts

1. **Infrastructure**: The "foundational slab" (GKE + Network). One-time setup.
2. **Images (Templates)**: These are the Blueprints.
    * **Stored as**: Dockerfile source in a ConfigMap + Binary in Artifact Registry.
    * **Lifecycle**: Create (Build) $\rightarrow$ List $\rightarrow$ View Source $\rightarrow$ Edit (Rebuild).
3. **Workstations (Instances)**: These are the Living Environments.
    * **Stored as**: A K8s StatefulSet (Compute) + a PVC (Storage).
    * **Lifecycle**: Create from a Template $\rightarrow$ Start $\rightarrow$ Stop $\rightarrow$ Delete.
    * **Storage Logic**: Since each workstation is a unique instance, **deleting** a workstation should destroy both the compute and the storage. This ensures no "dangling disks" are left behind accumulating costs and cluttering the workspace.

### Core Technologies
- **Backend:** Python 3.11 + [FastAPI](https://fastapi.tiangolo.com/)
- **Frontend:** React 19 + TypeScript + [Vite](https://vitejs.dev/) + [MUI (Material UI)](https://mui.com/)
- **Infrastructure:** Google Kubernetes Engine (GKE), Google Artifact Registry, Google Cloud Build, Google Cloud Run
- **Editor Integration:** Monaco Editor (via `@monaco-editor/react`)

### Architecture
- **Monolith Deployment:** The FastAPI backend serves the React SPA from its `static` directory.
- **Orchestration Layer:** The backend interacts with GCP APIs (GKE, Cloud Build, Artifact Registry) to manage the lifecycle of workstation pods and images.
- **Kubernetes Native:** Development environments are deployed as Pods in a GKE cluster.

---

## Building and Running

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Cloud SDK (gcloud) configured with a project and Application Default Credentials (ADC).
- `kubectl` installed.

### Development Workflow
To run the project locally with hot-reloading:

#### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

#### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

### Testing
Run backend tests using `pytest`:
```bash
cd backend
pytest
```

### Deployment
The project is designed for deployment to **Google Cloud Run**.
```bash
./deploy.sh
```
This script builds the Docker image (using the root `Dockerfile`) and deploys it directly to Cloud Run.

---

## Development Conventions

### Coding Styles
- **Python:** PEP 8 compliant, using `pydantic` for data validation and `FastAPI` for routing.
- **TypeScript:** Strict type checking, functional React components with hooks.
- **Styling:** Material UI components with Emotion-based styling.

### Project Structure
- `backend/app/api/`: REST API endpoints (health, admin, workstations).
- `backend/app/services/`: Integration logic for GCP services (GKE, Cloud Build, etc.).
- `backend/app/models/`: Pydantic models for request/response validation.
- `frontend/src/components/`: Modular React components.
- `plans/`: Project roadmaps, phase plans, and audit reports.

### Key Scripts
- `start.sh`: A utility to port-forward and connect to a running workstation Pod in GKE.
- `deploy.sh`: Orchestrates the Cloud Run deployment process.
- `nuke_everything.py`: A cleanup script for project resources (use with caution).
