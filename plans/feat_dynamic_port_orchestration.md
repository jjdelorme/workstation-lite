# Feature Implementation Plan: Dynamic Port Orchestration

## 🔍 Analysis & Context
*   **Objective:** Enable dynamic port configuration for workstations. This ensures that the port selected in the UI is correctly mapped from the host to the container, and that the application inside the container (e.g., VSCodium) listens on that specific port.
*   **Current State:**
    *   `templates/Dockerfile.template` uses `linuxserver/vscodium-web`, which defaults to port 8000.
    *   `backend/app/services/k8s.py` maps ports 1:1 but doesn't inform the container which port to use.
    *   `frontend/src/components/NewWorkstationDialog.tsx` defaults to port 3000, creating a mismatch with the default image (8000).
*   **Affected Files:**
    *   `templates/Dockerfile.template`
    *   `backend/app/services/k8s.py`
    *   `backend/app/api/workstations.py`
*   **Key Dependencies:** None (standard Docker/K8s/FastAPI).
*   **Risks/Edge Cases:** Multiple ports being exposed; the first port in the list should be treated as the "Primary IDE Port".

## 📋 Micro-Step Checklist
- [ ] Phase 1: Dockerfile Enhancement
  - [ ] Step 1.A: Update `Dockerfile.template` to support a dynamic `PORT` variable.
- [ ] Phase 2: Backend Orchestration
  - [ ] Step 2.A: Update `K8sManager.apply_statefulset` to inject the `PORT` environment variable.
  - [ ] Step 2.B: Update `get_connect_script` to use the primary port for the main connection.
- [ ] Phase 3: Validation
  - [ ] Step 3.A: Verify port-forwarding works with non-default ports.

## 📝 Step-by-Step Implementation Details

### Phase 1: Dockerfile Enhancement
1.  **Step 1.A (Dynamic Port Support):** Update the template to use an environment variable for the internal port.
    *   *Target File:* `templates/Dockerfile.template`
    *   *Exact Change:* 
        *   Add `ENV PORT=3000` as a default.
        *   Add `ENV CODE_ARGS="--port ${PORT}"` to pass the port to the VSCodium binary.
        *   Add `EXPOSE ${PORT}`.

### Phase 2: Backend Orchestration
1.  **Step 2.A (Injecting PORT Env Var):** Ensure the container knows which port it should be listening on.
    *   *Target File:* `backend/app/services/k8s.py`
    *   *Exact Change:* Inside `apply_statefulset`, before creating the `V1Container`, check if `ports` is provided. If so, inject `PORT` into the `env_list`.
        ```python
        if ports:
            # The first port is considered the primary IDE port
            env_list.append(client.V1EnvVar(name="PORT", value=str(ports[0])))
        ```

2.  **Step 2.B (Connection Script Update):** Ensure the `connect` script correctly handles the primary port.
    *   *Target File:* `backend/app/api/workstations.py`
    *   *Exact Change:* In `get_connect_script`, ensure the `ports` list is retrieved from the workstation config and used for the `kubectl port-forward` command. (Already partially implemented, but verify consistency).

### Phase 3: Validation
1.  **Step 3.A (End-to-End Test):**
    *   Create a new workstation with port `8080`.
    *   Verify the StatefulSet has `PORT=8080` in its environment.
    *   Verify `kubectl port-forward ... 8080:8080` allows access to the IDE.

## 🎯 Success Criteria
*   Workstations can be started on any valid port defined in the UI.
*   The `PORT` environment variable is correctly injected into the K8s Pod.
*   The `Dockerfile.template` correctly translates `PORT` into `CODE_ARGS` for VSCodium.
*   The "Magic Connect" script port-forwards the correct ports.
