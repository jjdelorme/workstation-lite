# Feature Implementation Plan: Phase 3 - Customization & Persistence

## 🔍 Analysis & Context
*   **Objective:** Enable users to build custom workstation images using Cloud Build, store them in Artifact Registry, and edit their Dockerfiles via a Monaco editor in the frontend, ensuring `/home/coder` persistence.
*   **Affected Files:**
    *   `backend/requirements.txt`
    *   `backend/app/services/cloud_build.py` (New)
    *   `backend/app/services/artifact_registry.py` (New)
    *   `backend/app/services/k8s.py`
    *   `backend/app/api/workstations.py`
    *   `backend/app/models/workstation.py`
    *   `backend/tests/test_cloud_build.py` (New)
    *   `backend/tests/test_artifact_registry.py` (New)
    *   `backend/tests/test_k8s.py`
    *   `backend/tests/test_workstations_api.py`
    *   `frontend/package.json`
    *   `frontend/src/components/WorkstationEditor.tsx` (New)
    *   `frontend/src/App.tsx`
*   **Key Dependencies:** `google-cloud-build`, `google-cloud-artifact-registry`, `@monaco-editor/react`.
*   **Risks/Edge Cases:** Cloud Build job taking too long causing UI timeouts; handling K8s ConfigMap creation/updates correctly to store custom image references without a traditional database.

## 📋 Micro-Step Checklist
- [ ] Phase 1: Backend Infrastructure (Artifact Registry & Cloud Build)
  - [ ] Step 1.A: Add GCP SDK Dependencies
  - [ ] Step 1.B: Implement Artifact Registry Manager & Tests
  - [ ] Step 1.C: Implement Cloud Build Manager & Tests
- [ ] Phase 2: Backend Integration & Persistence
  - [ ] Step 2.A: Add ConfigMap storage to K8sManager & Tests
  - [ ] Step 2.B: Update API Endpoints (init, build, start) & Tests
- [ ] Phase 3: Frontend Editor Integration
  - [ ] Step 3.A: Add Frontend Dependencies
  - [ ] Step 3.B: Create WorkstationEditor Component
  - [ ] Step 3.C: Integrate Editor into App

## 📝 Step-by-Step Implementation Details
*CRITICAL: Be extremely specific. You MUST include exact file paths, target line numbers (if known), function signatures, and structural code snippets.*

### Prerequisites
None beyond the existing setup.

#### Phase 1: Backend Infrastructure (Artifact Registry & Cloud Build)
1.  **Step 1.A (The Dependencies):** Update Python dependencies.
    *   *Target File:* `backend/requirements.txt`
    *   *Exact Change:* Append `google-cloud-build==3.24.0` and `google-cloud-artifact-registry==1.11.1`.

2.  **Step 1.B (Artifact Registry Manager):** Create AR repository manager and its tests.
    *   *Target File:* `backend/tests/test_artifact_registry.py`
    *   *Test Cases to Write:* Test `ensure_repository` creates repo if it doesn't exist, and gracefully handles the `AlreadyExists` exception if it does. Mock `google.cloud.artifactregistry_v1.ArtifactRegistryClient`.
    *   *Target File:* `backend/app/services/artifact_registry.py`
    *   *Exact Change:* Implement `ArtifactRegistryManager` class with method `ensure_repository(self, project_id: str, region: str, repo_name: str)`.
        *   It should use `artifactregistry_v1.ArtifactRegistryClient()`.
        *   Construct `parent = f"projects/{project_id}/locations/{region}"`.
        *   Construct `repo = artifactregistry_v1.Repository(format_=artifactregistry_v1.Repository.Format.DOCKER)`.
        *   Call `create_repository(request={"parent": parent, "repository_id": repo_name, "repository": repo})`. Catch `google.api_core.exceptions.AlreadyExists`.

3.  **Step 1.C (Cloud Build Manager):** Create Cloud Build manager and its tests.
    *   *Target File:* `backend/tests/test_cloud_build.py`
    *   *Test Cases to Write:* Test `build_custom_image` correctly constructs the `Build` object with an inline Dockerfile echo step and a docker build/push step. Mock `google.cloud.devtools.cloudbuild_v1.CloudBuildClient`.
    *   *Target File:* `backend/app/services/cloud_build.py`
    *   *Exact Change:* Implement `CloudBuildManager` class with method `build_custom_image(self, project_id: str, region: str, user_ns: str, dockerfile_content: str) -> str`.
        *   Construct image tag: `{region}-docker.pkg.dev/{project_id}/workstation-images/{user_ns}:latest`.
        *   Define `build_steps`:
            1. `{"name": "ubuntu", "entrypoint": "bash", "args": ["-c", f"echo '{dockerfile_content}' > Dockerfile"]}`
            2. `{"name": "gcr.io/cloud-builders/docker", "args": ["build", "-t", image_tag, "."]}`
            3. `{"name": "gcr.io/cloud-builders/docker", "args": ["push", image_tag]}`
        *   Call `client.create_build(project_id=project_id, build={"steps": build_steps})` and return the `image_tag`. (Return the target tag so it can be saved in the ConfigMap).

#### Phase 2: Backend Integration & Persistence
1.  **Step 2.A (ConfigMap Storage):** Update `K8sManager` to store/retrieve custom image preferences.
    *   *Target File:* `backend/tests/test_k8s.py`
    *   *Test Cases to Write:* Add `test_save_workstation_config` (verifies creation/patching of ConfigMap `workstation-config` with `{"image": "..."}`) and `test_get_workstation_config` (verifies data extraction).
    *   *Target File:* `backend/app/services/k8s.py`
    *   *Exact Change:*
        *   Add `save_workstation_config(self, user_ns: str, image: str)`: Creates a `V1ConfigMap` named `workstation-config` with `data={"image": image}`. Tries to `read_namespaced_config_map`. If exists, uses `patch_namespaced_config_map`, else `create_namespaced_config_map`.
        *   Add `get_workstation_config(self, user_ns: str) -> Optional[str]`: Tries to read the ConfigMap and return `data.get("image")`. Catch exceptions and return `None` if not found.

2.  **Step 2.B (Update API):** Wire everything into the endpoints.
    *   *Target File:* `backend/app/models/workstation.py`
    *   *Exact Change:* Add `class BuildRequest(BaseModel): dockerfile: str`.
    *   *Target File:* `backend/tests/test_workstations_api.py`
    *   *Test Cases to Write:*
        *   Test `/init` calls `ar_manager.ensure_repository`.
        *   Test `POST /{user_ns}/build` calls `cloud_build_manager.build_custom_image` and `k8s_manager.save_workstation_config`.
        *   Test `POST /{user_ns}/start` retrieves the custom image via `k8s_manager.get_workstation_config` and applies it to the StatefulSet.
    *   *Target File:* `backend/app/api/workstations.py`
    *   *Exact Change:*
        *   Import and instantiate `ArtifactRegistryManager` and `CloudBuildManager`.
        *   In `init_project`, after cluster creation checks, call `ar_manager.ensure_repository(settings.gcp_project_id, settings.region, "workstation-images")`.
        *   Add a new endpoint `@router.post("/{user_ns}/build")` that accepts `BuildRequest`. It should call `cloud_build_manager.build_custom_image(..., req.dockerfile)` and then `k8s_manager.save_workstation_config(user_ns, target_image)`. Returns `{"status": "ok", "message": "Build triggered", "image": target_image}`.
        *   In `start_workstation`, update logic:
            ```python
            custom_image = k8s_manager.get_workstation_config(user_ns)
            final_image = custom_image if custom_image else settings.workstation_image
            k8s_manager.apply_statefulset(..., final_image, ...)
            ```

#### Phase 3: Frontend Editor Integration
1.  **Step 3.A (Frontend Dependencies):** Install Monaco React.
    *   *Action:* In `frontend/`, run `npm install @monaco-editor/react`. (This will update `package.json` and `package-lock.json`).

2.  **Step 3.B (Workstation Editor Component):** Create the code editor UI.
    *   *Target File:* `frontend/src/components/WorkstationEditor.tsx`
    *   *Exact Change:*
        *   Create a functional component using `@monaco-editor/react` `<Editor>`.
        *   Maintain a local state for `dockerfileContent` initialized to `FROM codercom/code-server:latest\nRUN sudo apt-get update && sudo apt-get install -y git jq`.
        *   Include a `Button` ("Save & Build") that sends a `POST` request to `http://localhost:8000/workstations/user-1/build` with the JSON payload `{ "dockerfile": dockerfileContent }`. (Hardcode `user-1` as the namespace for now since auth isn't fully wired yet).
        *   Add basic error/success handling with a Material UI `<Alert>` or `<Snackbar>`.

3.  **Step 3.C (Integrate Editor):** Add the editor to the main app view.
    *   *Target File:* `frontend/src/App.tsx`
    *   *Exact Change:*
        *   Import `WorkstationEditor`.
        *   Render the component inside a MUI `Card` or `Box` beneath the primary action buttons in the `Container`. Ensure it has some margin/padding for visual hierarchy.

### 🧪 Global Testing Strategy
*   **Unit Tests:** Backend unit tests will comprehensively cover the `ArtifactRegistryManager`, `CloudBuildManager`, and the updated `K8sManager` utilizing strict mocking. The API layer tests will ensure that requests route to the right managers and K8s configuration persists correctly.
*   **Integration Tests:** Start the backend and frontend locally. Click "Save & Build" in the UI. Ensure a valid request is sent to `POST /workstations/user-1/build` and that the backend responds 200 OK. Verify via tests that the `get_workstation_config` returns the generated string instead of the fallback default.

## 🎯 Success Criteria
*   Backend successfully creates the `workstation-images` AR repo during `/init`.
*   Backend can construct a Cloud Build `Build` object using an inline Dockerfile string.
*   Custom image references are stored and retrieved using Kubernetes ConfigMaps in the user's namespace.
*   The `StatefulSet` starts with the custom image if one is defined.
*   Frontend displays a Monaco editor for the Dockerfile and triggers the build process via API.
*   All unit tests pass and cover the new logic.