# Feature Implementation Plan: Phase 2 - Orchestration Logic

## 🔍 Analysis & Context
*   **Objective:** Implement GKE Autopilot "Discovery & Creation" logic, Kubernetes StatefulSet + PVC manifest generation, and the "Start/Stop" API endpoints for Workstation Lite.
*   **Affected Files:**
    *   `backend/app/main.py`
    *   `backend/app/core/config.py` (New)
    *   `backend/app/models/workstation.py` (New)
    *   `backend/app/services/gke.py` (New)
    *   `backend/app/services/k8s.py` (New)
    *   `backend/app/api/workstations.py` (New)
    *   `backend/tests/test_config.py` (New)
    *   `backend/tests/test_gke.py` (New)
    *   `backend/tests/test_k8s.py` (New)
    *   `backend/tests/test_workstations_api.py` (New)
*   **Key Dependencies:** `google-cloud-container`, `kubernetes`, `pydantic-settings`, `pytest`.
*   **Risks/Edge Cases:**
    *   GKE cluster creation operations are long-running and require asynchronous polling or returning an "in-progress" status.
    *   Application Default Credentials (ADC) must be used. Tests must heavily mock `google-cloud-container` and `kubernetes` clients to avoid relying on active cloud connections.
    *   Kubernetes resources (PVC, StatefulSet) require the corresponding per-user namespace to exist prior to creation.

## 📋 Micro-Step Checklist
- [ ] Phase 1: Configuration & Models
  - [ ] Step 1.A: Define Config & Model Unit Tests
  - [ ] Step 1.B: Implement App Configuration
  - [ ] Step 1.C: Implement Workstation Models
- [ ] Phase 2: GKE Cluster Orchestration
  - [ ] Step 2.A: Define GKE Service Unit Tests
  - [ ] Step 2.B: Implement GKE Manager Service
- [ ] Phase 3: Kubernetes Workstation Management
  - [ ] Step 3.A: Define Kubernetes Service Unit Tests
  - [ ] Step 3.B: Implement Kubernetes Manifest Generators
- [ ] Phase 4: Workstation API Endpoints
  - [ ] Step 4.A: Define Workstations API Unit Tests
  - [ ] Step 4.B: Implement Workstations Router
  - [ ] Step 4.C: Mount Router in FastAPI App

## 📝 Step-by-Step Implementation Details

### Prerequisites
Ensure backend environment is active: `cd backend && source venv/bin/activate`

#### Phase 1: Configuration & Models
1.  **Step 1.A (The Unit Test Harness):** Verify configuration defaults.
    *   *Target File:* `backend/tests/test_config.py`
    *   *Test Cases to Write:*
        *   Assert `Settings().gcp_project_id` loads from env.
        *   Assert `Settings().cluster_name` defaults to `workstation-cluster`.
        *   Assert `Settings().workstation_image` defaults to `codercom/code-server:latest`.
2.  **Step 1.B (The Implementation):** Build the settings class.
    *   *Target File:* `backend/app/core/config.py`
    *   *Exact Change:* Implement `Settings(BaseSettings)` using `pydantic_settings`. Include fields for GCP project, region, cluster name (`workstation-cluster`), and base image (`codercom/code-server:latest`).
3.  **Step 1.C (The Implementation):** Build the Pydantic models.
    *   *Target File:* `backend/app/models/workstation.py`
    *   *Exact Change:* Create `WorkstationStatus(str, Enum)` with states `PROVISIONING`, `RUNNING`, `STOPPED`. Create `WorkstationResponse` and `WorkstationStartRequest` Pydantic models.
4.  **Step 1.D (The Verification):**
    *   *Action:* Run `pytest backend/tests/test_config.py`.
    *   *Success:* Test passes and validates environment bindings.

#### Phase 2: GKE Cluster Orchestration
1.  **Step 2.A (The Unit Test Harness):** Define cluster discovery/creation tests.
    *   *Target File:* `backend/tests/test_gke.py`
    *   *Test Cases to Write:*
        *   Mock `ClusterManagerClient.get_cluster`. Assert `check_cluster_exists` returns `True` when found, `False` when `NotFound` is raised.
        *   Mock `ClusterManagerClient.create_cluster`. Assert `create_autopilot_cluster` passes a payload with `autopilot={"enabled": True}` and the correct cluster name.
2.  **Step 2.B (The Implementation):** Implement the `GKEManager`.
    *   *Target File:* `backend/app/services/gke.py`
    *   *Exact Change:* Implement class `GKEManager` with methods `check_cluster_exists(project_id, region, cluster_name)` and `create_autopilot_cluster(project_id, region, cluster_name)`. Use `google.cloud.container_v1` SDK. Ensure `create_cluster` uses the required Autopilot format.
3.  **Step 2.C (The Verification):**
    *   *Action:* Run `pytest backend/tests/test_gke.py`.
    *   *Success:* All mocked GKE calls verify the intended logic without real API requests.

#### Phase 3: Kubernetes Workstation Management
1.  **Step 3.A (The Unit Test Harness):** Define StatefulSet/PVC generation tests.
    *   *Target File:* `backend/tests/test_k8s.py`
    *   *Test Cases to Write:*
        *   Mock `kubernetes.client`.
        *   Test `create_namespace` applies per-user namespace.
        *   Test `create_pvc` asserts `storageClassName="standard-rwo"`.
        *   Test `create_statefulset` asserts `codercom/code-server:latest` image and volume mount `/home/coder`.
        *   Test `scale_workstation` asserts replicas change to 1 (Start) or 0 (Stop).
2.  **Step 3.B (The Implementation):** Implement the `K8sManager`.
    *   *Target File:* `backend/app/services/k8s.py`
    *   *Exact Change:* Create `K8sManager` using `kubernetes.client`. Implement `ensure_namespace(user_ns)`, `apply_pvc(user_ns, name, size="10Gi")`, `apply_statefulset(user_ns, name, image, replicas)`. Use `client.AppsV1Api` for StatefulSet and `client.CoreV1Api` for PVC/Namespaces. Ensure PVC uses `standard-rwo` (GCE Balanced Persistent Disk).
3.  **Step 3.C (The Verification):**
    *   *Action:* Run `pytest backend/tests/test_k8s.py`.
    *   *Success:* Ensure Kubernetes objects are structured correctly via assertions on the generated Python dictionary or objects.

#### Phase 4: Workstation API Endpoints
1.  **Step 4.A (The Unit Test Harness):** Define API routing tests.
    *   *Target File:* `backend/tests/test_workstations_api.py`
    *   *Test Cases to Write:*
        *   Use `TestClient(app)`.
        *   Mock `GKEManager` and `K8sManager`.
        *   Assert `POST /api/workstations/init` triggers `create_autopilot_cluster`.
        *   Assert `POST /api/workstations/{user_ns}/start` triggers `ensure_namespace`, `apply_pvc`, and `apply_statefulset(replicas=1)`.
        *   Assert `POST /api/workstations/{user_ns}/stop` triggers `apply_statefulset(replicas=0)`.
2.  **Step 4.B (The Implementation):** Implement the API Router.
    *   *Target File:* `backend/app/api/workstations.py`
    *   *Exact Change:* Create an `APIRouter(prefix="/workstations", tags=["workstations"])`. Implement endpoints `/init`, `/{user_ns}/start`, `/{user_ns}/stop`, mapping them to the `GKEManager` and `K8sManager` services.
3.  **Step 4.C (The Integration):** Mount the router.
    *   *Target File:* `backend/app/main.py`
    *   *Exact Change:* Add `from app.api.workstations import router as workstations_router` and `app.include_router(workstations_router, prefix="/api")`.
4.  **Step 4.D (The Verification):**
    *   *Action:* Run `pytest backend/tests/test_workstations_api.py`.
    *   *Success:* All integration flows between the router and services are validated.

### 🧪 Global Testing Strategy
*   **Unit Tests:** Verify individual business rules (cluster name, default images) and SDK integrations (correct payload structures for GKE and Kubernetes) using strict mocks.
*   **Integration Tests:** Verify the FastAPI routing layer successfully unmarshals JSON payloads, passes them to service layers, and returns appropriate HTTP status codes (200 OK, 202 Accepted).

## 🎯 Success Criteria
*   The `GKEManager` successfully orchestrates the creation of a GKE Autopilot cluster using Python.
*   The `K8sManager` generates correct Python representations of Kubernetes `StatefulSet` and `PersistentVolumeClaim` objects mapped to per-user namespaces and `standard-rwo` storage.
*   The API exposes `/start` and `/stop` mechanics that manipulate the `StatefulSet` replicas (1 vs 0).
*   Test coverage is present for all new modules, prioritizing mocked SDK calls.
