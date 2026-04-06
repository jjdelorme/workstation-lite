# Feature Plan: In-Browser Web TTY for Workstations

## 1. Objective
Add a "Terminal" button to the workstation list that opens a fully functional, interactive terminal session directly in the browser. This eliminates the need for local `kubectl` or SSH configuration for quick tasks.

## 2. Architecture
The implementation will use a WebSocket bridge between the browser and the Kubernetes Pod.

- **Frontend:** [xterm.js](https://xtermjs.org/) to render the terminal in the browser.
- **Backend:** FastAPI WebSocket endpoint that proxies traffic to the GKE Pod using the `kubernetes` Python client's `stream` module.

## 3. Backend Implementation (FastAPI)

### 3.1. New WebSocket Endpoint
Add a new route in `backend/app/api/workstations.py`:
`WS /api/workstations/{user_ns}/{name}/terminal`

### 3.2. Kubernetes Stream Integration
- Use `get_k8s_manager()` to obtain a configured Kubernetes client.
- Use `kubernetes.stream.stream` to call `connect_get_namespaced_pod_exec`.
- **Command:** Try `/bin/bash` with a fallback to `/bin/sh`.
- **TTY:** Enable `tty=True`, `stdin=True`, `stdout=True`, `stderr=True`.

### 3.3. Protocol Handling
- **Data Transfer:** Forward binary or text data from WebSocket to Pod `stdin`, and Pod `stdout/stderr` to WebSocket.
- **Resizing:** Handle a special JSON message from the frontend (e.g., `{"type": "resize", "cols": 80, "rows": 24}`) and call the stream's `write_channel(3, ...)` to send a `SIGWINCH` signal to the K8s PTY.
- **Heartbeats:** Send a "ping" (e.g., a null byte or a specific JSON message) every 20 seconds to prevent Cloud Run / GFE from terminating the idle connection.

## 4. Frontend Implementation (React)

### 4.1. Dependencies
Install the following:
- `xterm`: Core terminal emulator.
- `xterm-addon-fit`: Automatically resizes the terminal to fit its container.
- `xterm-addon-web-links`: Makes URLs clickable in the terminal.

### 4.2. Terminal Component
Create `frontend/src/components/WorkstationTerminal.tsx`:
- Manage the `WebSocket` lifecycle (open on mount, close on unmount).
- Initialize `Terminal` and attach to a DOM element.
- Handle `onData` from xterm to send to WebSocket.
- Handle `onMessage` from WebSocket to write to xterm.
- Use `ResizeObserver` to trigger the `fit` addon and send resize messages to the backend.

### 4.3. UI Integration
- Add a "Terminal" button to the `App.tsx` workstation list (next to Start/Stop).
- Open the terminal in a full-screen MUI `Dialog` or a dedicated panel.

## 5. Security & Authentication
- **Permissions:** The Cloud Run service account must have `pods/exec` permissions in the workstation namespaces.
- **WebSocket Auth:** Since the browser `WebSocket` API does not support custom headers, the authentication token will be passed via a query parameter: `?token=...`.
- **Namespace Validation:** Ensure the user can only exec into pods within their authorized `user_ns`.

## 6. Challenges & Mitigations
- **Cloud Run Timeout:** Cloud Run has a 60-minute maximum request duration.
    - *Mitigation:* Display a clear "Session Expired" message and provide a "Reconnect" button.
- **Idle Timeout:** GFE kills idle sockets.
    - *Mitigation:* Implement a 20-second heartbeat ping from either the client or server.
- **Shell Availability:** Some minimal images might not have `bash`.
    - *Mitigation:* The backend will attempt to detect/fallback to `/bin/sh`.

## 7. Execution Steps (Proposed)
1. **Backend:** Implement the WebSocket endpoint and K8s stream logic.
2. **Frontend:** Add `xterm.js` and the basic Terminal component.
3. **Integration:** Connect the two and test basic input/output.
4. **Polish:** Implement resizing, heartbeats, and proper error handling for disconnected states.
