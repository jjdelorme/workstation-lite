# Workstation Lite: Project Plan

## 1. Executive Summary
**Workstation Lite** is a "zero-infrastructure" developer platform designed to replace managed Cloud Workstations with a highly customizable, cost-effective, and portable alternative. It leverages **Cloud Run** as a serverless control plane and **GKE Autopilot** for on-demand, persistent development environments.

The core philosophy is "Deployment as Code": a single `git clone` and `gcloud run deploy` should result in a fully functional orchestration portal that provisions and manages its own infrastructure using the logged-in user's GCP permissions.

---

## 2. System Architecture

### 2.1 Control Plane (Cloud Run)
- **Backend:** Python (FastAPI) for high-performance orchestration and mature GCP SDK support.
- **Frontend:** React + TypeScript + Material UI (MUI) following **Material Design 3 (M3)** standards.
- **Authentication:** OAuth 2.0 with `https://www.googleapis.com/auth/cloud-platform` scope. The app executes actions (GKE creation, Pod management) using the user's delegated identity.

### 2.2 Workstation Layer (GKE Autopilot)
- **Compute:** GKE Autopilot (billing only for active Pods).
- **Persistence:** Kubernetes `StatefulSet` paired with `PersistentVolumeClaim` (PVC) using GCE Balanced Persistent Disks.
- **Isolation:** Each developer environment is isolated in a unique Kubernetes Namespace.
- **Image Management:** Custom Dockerfiles are built via **Cloud Build** and stored in **Artifact Registry**.
- **Opinionated Default Image:** A "batteries-included" environment based on `codercom/code-server` (Ubuntu) featuring:
    - **Runtimes:** Python 3, Node.js (via NVM), Go, TypeScript.
    - **Cloud Tools:** `gcloud` SDK, `kubectl`, `git`, Gemini CLI.
    - **CLI Experience:** `zsh` + `oh-my-zsh`, `powerlevel10k` theme, `tmux`, `jq`, `vim`.
    - **Persistence:** User configuration (`.zshrc`, `.tmux.conf`) and code live in the persistent `/home/coder`.

### 2.3 Connectivity Model
- **Primary Access:** Web-based IDE (Code OSS/code-server) via port-forwarding.
- **CLI Access:** Persistent SSH-like sessions via a dynamically generated `curl | bash` command.
- **Tunneling:** Local port-forwarding of project ports (e.g., 3000, 8000, 8080) to the local host.

---

## 3. Tech Stack Details

| Component | Technology |
| :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn |
| **Frontend Framework** | React 18, TypeScript, Vite |
| **UI Library** | MUI (Material UI) with Material 3 Theme |
| **GCP Integration** | `google-cloud-container`, `google-cloud-build`, `kubernetes-python` |
| **Container Base** | `gitpod/openvscode-server:latest` (Ubuntu-based) |
| **Infrastructure** | GKE Autopilot, Artifact Registry, Cloud Run, Cloud Build |

---

## 4. Key Features & Workflows

### 4.1 Zero-Infra Bootstrapping
1. User deploys Cloud Run app.
2. User logs in; app detects no GKE cluster.
3. User clicks "Initialize Project"; app creates GKE Autopilot cluster and Artifact Registry repository.

### 4.2 Workstation Lifecycle
- **Create:** User selects a template or edits a Dockerfile; app triggers Cloud Build and deploys a StatefulSet.
- **Start/Stop:** App scales StatefulSet replicas (1 or 0). 
- **Persistence:** Home directory (`/home/workspace`) survives scale-to-zero.

### 4.3 The "Magic Command"
The portal generates a one-liner for the user's terminal:
```bash
curl -s https://[OUR-APP].a.run.app/connect | bash
```
The endpoint dynamically generates the necessary `gcloud` and `kubectl` commands (credentials, port-forwarding, and exec) based on the user's active session.

---

## 5. UI/UX Style Guidance (Material Design 3)
- **Aesthetic:** Clean, professional, minimal elevation, high-signal-to-noise ratio.
- **Color:** Dynamic color mapping (Primary/Secondary/Tertiary) with a soft `surface` background.
- **Feedback:** Visual skeleton loaders for provisioning states; real-time K8s status indicators (e.g., `ContainerCreating`, `Running`, `Terminated`).

---

## 6. Implementation Roadmap

### Phase 1: Foundational Scaffold
- [ ] Initialize FastAPI project with `google-cloud` libraries.
- [ ] Initialize React + MUI project with Material 3 theme.
- [ ] Create `deploy.sh` for one-command Cloud Run deployment.

### Phase 2: Orchestration Logic
- [ ] Implement GKE Autopilot "Discovery & Creation" logic.
- [ ] Implement Kubernetes `StatefulSet` + `PVC` manifest generator.
- [ ] Build the "Start/Stop" API endpoints.

### Phase 3: Customization & Persistence
- [ ] Implement the Cloud Build integration for custom Dockerfiles.
- [ ] Add the Monaco-based Dockerfile editor to the UI.
- [ ] Ensure volume mounting correctly persists `/home/coder`.

### Phase 4: Automation & DX
- [ ] Generate the connection bash commands in the UI.
- [ ] Implement the "Scale-to-Zero" scheduler (Cloud Run Job).
- [ ] Add "Project Snapshot" feature to clone disks or export code.

---

## 7. Security & Safety
- **Delegated Identity:** No long-lived Service Account keys; uses OAuth tokens.
- **Namespace Security:** Network Policies to isolate user namespaces.
- **IAP Alternative:** In-app Google Auth checks domain-specific whitelists (e.g., only `@example.com` emails).
