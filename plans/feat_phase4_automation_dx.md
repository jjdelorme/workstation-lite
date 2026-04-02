# Feature Implementation Plan: Phase 4 Automation & DX

## 🔍 Analysis & Context
*   **Objective:** Implement DX improvements (connection UI commands), cost-saving automation (Scale-to-Zero endpoint for Cloud Scheduler), and data safety (GCE disk snapshots).
*   **Affected Files:**
    *   `backend/requirements.txt`
    *   `backend/app/main.py`
    *   `backend/app/api/workstations.py`
    *   `backend/app/api/admin.py` (New)
    *   `backend/app/services/k8s.py`
    *   `backend/app/services/compute.py` (New)
    *   `backend/tests/test_compute.py` (New)
    *   `backend/tests/test_admin.py` (New)
    *   `frontend/src/App.tsx`
    *   `frontend/src/components/ConnectionInstructions.tsx` (New)
*   **Key Dependencies:** `google-cloud-compute` (Python SDK)
*   **Risks/Edge Cases:**
    *   *Scale-to-Zero:* Accidentally scaling down a workstation that is currently in use. The MVP will simply scale down all running workstations (to be invoked nightly by a Cloud Scheduler).
    *   *Snapshot:* Retrieving the correct GCE Persistent Disk name from the Kubernetes PersistentVolume's CSI `volume_handle` requires correct string parsing.

## 📋 Micro-Step Checklist
- [ ] Phase 1: Dependency & Compute Service Scaffold
  - [ ] Step 1.A: Add `google-cloud-compute` to `requirements.txt`.
  - [ ] Step 1.B: Add Unit Tests for `ComputeManager`.
  - [ ] Step 1.C: Implement `ComputeManager` (`backend/app/services/compute.py`).
- [ ] Phase 2: K8s Integration for Volume Handle Discovery
  - [ ] Step 2.A: Add tests for `k8s_manager.get_pvc_volume_handle` and `scale_down_idle_workstations`.
  - [ ] Step 2.B: Implement `K8sManager` methods in `backend/app/services/k8s.py`.
- [ ] Phase 3: Backend API Endpoints (Snapshot & Scale-to-Zero)
  - [ ] Step 3.A: Add tests for new endpoints in `test_api.py` and `test_admin.py`.
  - [ ] Step 3.B: Add `/workstations/{user_ns}/snapshot` endpoint.
  - [ ] Step 3.C: Add `/admin/scale-to-zero` endpoint in `backend/app/api/admin.py` and register it in `main.py`.
- [ ] Phase 4: Frontend DX
  - [ ] Step 4.A: Create `ConnectionInstructions.tsx`.
  - [ ] Step 4.B: Integrate Connection UI and Snapshot button into `App.tsx`.

## 📝 Step-by-Step Implementation Details

### Prerequisites
Run `pip install -r requirements.txt` after updating the dependencies to ensure the Compute SDK is available.

#### Phase 1: Dependency & Compute Service Scaffold
1.  **Step 1.A (Dependencies):** Add the Compute SDK.
    *   *Target File:* `backend/requirements.txt`
    *   *Exact Change:* Add `google-cloud-compute==1.15.0` (or `google-cloud-compute` latest) to the bottom of the file.
2.  **Step 1.B (The Unit Test Harness):** Define ComputeManager tests.
    *   *Target File:* `backend/tests/test_compute.py` (Create)
    *   *Test Cases to Write:* Assert `create_disk_snapshot` successfully calls `compute_v1.SnapshotsClient().insert()`. Use `@patch("app.services.compute.compute_v1.SnapshotsClient")` to mock the GCP client.
3.  **Step 1.C (The Implementation):** Implement the `ComputeManager`.
    *   *Target File:* `backend/app/services/compute.py` (Create)
    *   *Exact Change:* Implement class `ComputeManager` with method `create_disk_snapshot(self, project_id: str, zone: str, disk_name: str, snapshot_name: str)`. Initialize `self.snapshots_client = compute_v1.SnapshotsClient()`. Use `compute_v1.Snapshot(name=snapshot_name, source_disk=f"projects/{project_id}/zones/{zone}/disks/{disk_name}")`. Call `self.snapshots_client.insert(project=project_id, snapshot_resource=...)`. Return the operation name.

#### Phase 2: K8s Integration for Volume Handle Discovery
1.  **Step 2.A (The Unit Test Harness):** Define the K8s verification requirement.
    *   *Target File:* `backend/tests/test_k8s.py`
    *   *Test Cases to Write:* Mock `core_api.read_namespaced_persistent_volume_claim` and `read_persistent_volume` to return a fake PV with `csi.volume_handle = "projects/my-project/zones/us-central1-a/disks/pvc-12345"`. Assert `get_pvc_volume_handle` correctly returns the handle string. Test `scale_down_idle_workstations` mocks `list_stateful_set_for_all_namespaces` and asserts `scale_workstation` is called on active pods.
2.  **Step 2.B (The Implementation):** Extract Volume Handle & Scale Down Logic.
    *   *Target File:* `backend/app/services/k8s.py`
    *   *Exact Change:* Add `get_pvc_volume_handle(self, user_ns: str, pvc_name: str) -> Optional[str]`. Read PVC to get `spec.volume_name`. Read PV by `volume_name` to get `pv.spec.csi.volume_handle`. Add `scale_down_idle_workstations(self) -> list` that iterates `self.apps_api.list_stateful_set_for_all_namespaces(label_selector="app=workstation").items`, checks if `replicas > 0`, calls `self.scale_workstation(ns, name, 0)`, and returns the namespace list.

#### Phase 3: Backend API Endpoints (Snapshot & Scale-to-Zero)
1.  **Step 3.A (The Unit Test Harness):** Verify API contracts.
    *   *Target File:* `backend/tests/test_api.py` and `backend/tests/test_admin.py` (Create)
    *   *Test Cases to Write:* Test `POST /api/workstations/{user_ns}/snapshot` returns a `200 OK` status and triggers the mock snapshot service. Test `POST /api/admin/scale-to-zero` returns the mocked scaled namespaces list.
2.  **Step 3.B (Snapshot Implementation):** Execute the snapshot logic.
    *   *Target File:* `backend/app/api/workstations.py`
    *   *Exact Change:* Implement `@router.post("/{user_ns}/snapshot")`. Call `k8s_manager.get_pvc_volume_handle(user_ns, "workstation-pvc")`. Parse the handle string using `handle.split("/")` to extract `project_id`, `zone`, and `disk_name`. Initialize `ComputeManager` and call `create_disk_snapshot(project_id, zone, disk_name, f"{disk_name}-snap-{timestamp}")`. Return success status.
3.  **Step 3.C (Admin Scale Implementation):** Execute scale-to-zero endpoint.
    *   *Target File:* `backend/app/api/admin.py` (Create)
    *   *Exact Change:* Create a new FastAPI router with prefix `/admin`. Implement `@router.post("/scale-to-zero")` calling `k8s_manager.scale_down_idle_workstations()` and returning `{"status": "ok", "scaled_namespaces": [...]}`. Register `app.include_router(admin_router, prefix="/api")` in `backend/app/main.py`.

#### Phase 4: Frontend DX (Connection & Snapshot UI)
1.  **Step 4.A (Connection UI Component):** Implement standard terminal output.
    *   *Target File:* `frontend/src/components/ConnectionInstructions.tsx` (Create)
    *   *Exact Change:* Create a React functional component accepting `userNs: string`. Display an MUI `Paper` containing a `<Box component="pre">` with two bash commands (`kubectl port-forward pod/workstation-0 8080:8080 -n ${userNs}` and `kubectl exec -it pod/workstation-0 -n ${userNs} -- /bin/bash`). Add a "Copy" button using `navigator.clipboard.writeText`.
2.  **Step 4.B (Integrate into App):** Update the main dashboard.
    *   *Target File:* `frontend/src/App.tsx`
    *   *Exact Change:* Import `ConnectionInstructions`. In the `status?.status === 'RUNNING'` view, conditionally render the `<ConnectionInstructions userNs={user_ns} />` component. Add a "Snapshot Disk" `Button` beneath the "Start/Stop" buttons that triggers `fetch('/api/workstations/user-1/snapshot', { method: 'POST' })` and updates UI status accordingly.

### 🧪 Global Testing Strategy
*   **Unit Tests:** Pure backend Python logic for parsing the CSI volume handle and verifying the GCE Snapshot payload.
*   **Integration Tests:** Start workstation -> Assert UI shows connection commands in browser -> Click Snapshot button -> Stop workstation -> Trigger `POST /api/admin/scale-to-zero` manually to verify idle machines shut down.

## 🎯 Success Criteria
*   The web UI displays a clear, copyable `kubectl port-forward` command when the state is RUNNING.
*   Cloud Scheduler can anonymously hit `POST /api/admin/scale-to-zero` to successfully shut down all active workstations.
*   Clicking "Snapshot Disk" successfully calls the `google-cloud-compute` Python SDK and triggers a disk snapshot of the underlying GCE persistent disk.
