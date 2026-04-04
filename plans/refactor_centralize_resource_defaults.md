# Refactoring Plan: Centralizing Resource Defaults

## 1. Objective
Eliminate the "Shotgun Surgery" anti-pattern by centralizing the resource defaults (CPU, Memory, Disk) into a Single Source of Truth. This ensures that future changes to these values can be made in one place rather than across 10+ files in both the frontend and backend.

## 2. Current State Analysis
Resource defaults are currently hardcoded as literal strings (e.g., `"2000m"`, `"8Gi"`) in:
- **Backend Models:** `backend/app/models/workstation.py`, `backend/app/models/service.py`
- **Backend Services:** `backend/app/services/k8s.py`
- **Backend API Layer:** `backend/app/api/workstations.py`, `backend/app/api/services.py`
- **Frontend Components:** `NewWorkstationDialog.tsx`, `EditWorkstationDialog.tsx`, `NewServiceDialog.tsx`, `EditServiceDialog.tsx`, `App.tsx`
- **Backend Tests:** `tests/test_services.py`, `tests/test_save_config_optional_image.py`

## 3. Proposed Architecture (Single Source of Truth)

### A. Backend Centralization
Use the existing Pydantic-based `Settings` class in `backend/app/core/config.py` to hold these values. This allows them to be overridden via environment variables if needed.

### B. API Exposure
Expose these defaults through the `/api/workstations/config` endpoint so the frontend can stay in sync with the backend dynamically.

### C. Frontend Centralization
Introduce a `ResourceDefaults` provider or a global configuration object in the frontend that is populated once from the API on application startup.

## 4. Implementation Steps

### Phase 1: Backend Refactoring
1.  **Update `backend/app/core/config.py`**:
    - Add fields to the `Settings` class:
        - `default_cpu_workstation`: "2000m"
        - `default_memory_workstation`: "8Gi"
        - `default_disk_workstation`: "10Gi"
        - `default_cpu_service`: "2000m"
        - `default_memory_service`: "8Gi"
        - `default_disk_service`: "5Gi"
2.  **Update `backend/app/models/`**:
    - Import `settings` and use these values as field defaults in `WorkstationResponse`, `SaveConfigRequest`, etc.
3.  **Update `backend/app/services/k8s.py`**:
    - Replace hardcoded defaults in method signatures (e.g., `cpu: str = "2000m"`) with references to `settings`.
4.  **Update `backend/app/api/`**:
    - Use `settings` in the API routers instead of hardcoded fallbacks in `.get("cpu", "2000m")`.

### Phase 2: Expose via API
1.  **Update `/api/workstations/config`**:
    - Add a `defaults` object to the response containing the CPU, memory, and disk values for both workstations and services.

### Phase 3: Frontend Refactoring
1.  **Update `App.tsx`**:
    - Modify the `fetchConfig` logic to store the returned defaults in a global state or context.
2.  **Update Dialog Components**:
    - Modify `useState` initializations (e.g., `useState('2000m')`) to use the values from the global config instead of hardcoded strings.
    - Components affected: `NewWorkstationDialog`, `EditWorkstationDialog`, `NewServiceDialog`, `EditServiceDialog`.

### Phase 4: Test Suite Update
1.  **Update Mock Assertions**:
    - In `tests/test_services.py` and others, import `settings` and use `settings.default_cpu_workstation` in assertions to ensure tests automatically adjust when defaults change.

## 5. Verification Strategy
1.  **Backend**: Run `pytest` to ensure all logic still holds with the centralized configuration.
2.  **Frontend**: Build the frontend (`npm run build`) and verify there are no type errors or regressions in the UI forms.
3.  **Integration**: Verify that changing a single value in `backend/.env` or `config.py` correctly updates the default values in both the backend K8s manifests and the frontend text boxes.
