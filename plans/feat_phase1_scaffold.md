# Feature Implementation Plan: Phase 1 - Foundational Scaffold

## 🔍 Analysis & Context
*   **Objective:** Establish the core monorepo structure, initializing a FastAPI backend with Google Cloud SDKs and a React+TypeScript+MUI frontend configured for Material Design 3, packaged for single-command deployment to Cloud Run.
*   **Affected Files:** `backend/`, `frontend/`, `Dockerfile`, `deploy.sh` (all net-new creations).
*   **Key Dependencies:** `fastapi`, `uvicorn`, `google-cloud-container`, `google-cloud-build`, `kubernetes` (Backend); `react`, `typescript`, `@mui/material`, `@emotion/react`, `@emotion/styled`, `vite` (Frontend).
*   **Risks/Edge Cases:** The FastAPI backend must correctly serve the compiled Vite Single-Page Application (SPA) without conflicting with its own `/api` routes. The multi-stage Dockerfile must correctly path the `dist` files to where the Python app expects them (i.e., `backend/app/static`).

## 📋 Micro-Step Checklist
- [ ] Phase 1: Backend Scaffold (FastAPI)
  - [ ] Step 1.A: Define Python dependencies
  - [ ] Step 1.B: Create test harness for the API
  - [ ] Step 1.C: Implement the core FastAPI app structure
  - [ ] Step 1.D: Verify Backend
- [ ] Phase 2: Frontend Scaffold (React + Vite)
  - [ ] Step 2.A: Initialize Vite project
  - [ ] Step 2.B: Install UI Dependencies
  - [ ] Step 2.C: Create M3 Theme
  - [ ] Step 2.D: Update Main React Components
  - [ ] Step 2.E: Verify Frontend Build
- [ ] Phase 3: Integration & Deployment configuration
  - [ ] Step 3.A: Update backend tests for SPA serving
  - [ ] Step 3.B: Implement SPA catch-all route in FastAPI
  - [ ] Step 3.C: Create multi-stage Dockerfile
  - [ ] Step 3.D: Create Cloud Run deployment script

## 📝 Step-by-Step Implementation Details

### Prerequisites
*   Ensure Node.js and npm are available in the workspace.
*   Ensure Python 3 is available in the workspace.

#### Phase 1: Backend Scaffold (FastAPI)
1.  **Step 1.A (Define Python dependencies):** Define the required libraries.
    *   *Target File:* `/home/jasondel/dev/workstation/backend/requirements.txt`
    *   *Exact Change:* Create the file with the following content:
        ```text
        fastapi==0.109.2
        uvicorn[standard]==0.27.1
        google-cloud-container==2.35.0
        google-cloud-build==3.22.0
        kubernetes==29.0.0
        pydantic-settings==2.1.0
        httpx==0.26.0
        pytest==8.0.0
        ```
2.  **Step 1.B (Create test harness for the API):** Define the unit test verification.
    *   *Target File:* `/home/jasondel/dev/workstation/backend/tests/test_api.py`
    *   *Exact Change:* Create the test file:
        ```python
        import pytest
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        def test_health_check():
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        ```
    *   *Target File:* `/home/jasondel/dev/workstation/backend/tests/__init__.py`
    *   *Exact Change:* Create an empty file.
3.  **Step 1.C (Implement the core FastAPI app structure):** Create the app routers and main entrypoint.
    *   *Target File:* `/home/jasondel/dev/workstation/backend/app/__init__.py`
    *   *Exact Change:* Create an empty file.
    *   *Target File:* `/home/jasondel/dev/workstation/backend/app/api/__init__.py`
    *   *Exact Change:* Create an empty file.
    *   *Target File:* `/home/jasondel/dev/workstation/backend/app/api/health.py`
    *   *Exact Change:* Create the health router:
        ```python
        from fastapi import APIRouter

        router = APIRouter()

        @router.get("/health")
        def health_check():
            return {"status": "ok"}
        ```
    *   *Target File:* `/home/jasondel/dev/workstation/backend/app/main.py`
    *   *Exact Change:* Wire up the router to the FastAPI application:
        ```python
        from fastapi import FastAPI
        from app.api.health import router as health_router

        app = FastAPI(title="Workstation Lite API")

        # Mount API routes
        app.include_router(health_router, prefix="/api")
        ```
4.  **Step 1.D (Verify Backend):** Verify the harness.
    *   *Action:* Run the test command in the `backend` directory.
    *   *Command:* `cd /home/jasondel/dev/workstation/backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pytest`
    *   *Success:* Test passes and no regressions.

#### Phase 2: Frontend Scaffold (React + Vite)
1.  **Step 2.A (Initialize Vite project):** Scaffold the initial TS React app.
    *   *Action:* Execute the Vite init command.
    *   *Command:* `cd /home/jasondel/dev/workstation && npm create vite@latest frontend -- --template react-ts`
    *   *Note:* Ensure you do not overwrite existing files if the command prompts.
2.  **Step 2.B (Install UI Dependencies):** Install Material UI with M3 components.
    *   *Action:* Execute the npm install.
    *   *Command:* `cd /home/jasondel/dev/workstation/frontend && npm install @mui/material @emotion/react @emotion/styled @fontsource/roboto @mui/icons-material react-router-dom`
3.  **Step 2.C (Create M3 Theme):** Define the Material 3 configuration.
    *   *Target File:* `/home/jasondel/dev/workstation/frontend/src/theme.ts`
    *   *Exact Change:* Create a robust M3 theme config:
        ```typescript
        import { createTheme } from '@mui/material/styles';

        const theme = createTheme({
          colorSchemes: {
            light: true,
            dark: true,
          },
          components: {
            MuiButton: {
              styleOverrides: {
                root: {
                  borderRadius: 20, // M3 pill-shaped
                  textTransform: 'none',
                },
              },
            },
          },
          typography: {
            fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
          },
        });

        export default theme;
        ```
4.  **Step 2.D (Update Main React Components):** Integrate the theme and create a placeholder homepage.
    *   *Target File:* `/home/jasondel/dev/workstation/frontend/src/main.tsx`
    *   *Exact Change:* Wrap the application in `ThemeProvider` and `CssBaseline`:
        ```tsx
        import React from 'react';
        import ReactDOM from 'react-dom/client';
        import { ThemeProvider, CssBaseline } from '@mui/material';
        import App from './App.tsx';
        import theme from './theme.ts';
        import '@fontsource/roboto/300.css';
        import '@fontsource/roboto/400.css';
        import '@fontsource/roboto/500.css';
        import '@fontsource/roboto/700.css';

        ReactDOM.createRoot(document.getElementById('root')!).render(
          <React.StrictMode>
            <ThemeProvider theme={theme}>
              <CssBaseline />
              <App />
            </ThemeProvider>
          </React.StrictMode>,
        );
        ```
    *   *Target File:* `/home/jasondel/dev/workstation/frontend/src/App.tsx`
    *   *Exact Change:* Add a simple UI demonstrating M3 standards:
        ```tsx
        import { AppBar, Toolbar, Typography, Container, Button, Box } from '@mui/material';

        function App() {
          return (
            <>
              <AppBar position="static" color="primary" elevation={0}>
                <Toolbar>
                  <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                    Workstation Lite
                  </Typography>
                  <Button color="inherit">Login</Button>
                </Toolbar>
              </AppBar>
              <Container maxWidth="md">
                <Box sx={{ mt: 4, textAlign: 'center' }}>
                  <Typography variant="h3" gutterBottom>
                    Zero-Infra Dev Environments
                  </Typography>
                  <Typography variant="body1" color="text.secondary" paragraph>
                    A single git clone and gcloud run deploy away from a highly customizable, portable workspace.
                  </Typography>
                  <Button variant="contained" size="large" sx={{ mt: 2 }}>
                    Initialize Project
                  </Button>
                </Box>
              </Container>
            </>
          );
        }

        export default App;
        ```
5.  **Step 2.E (Verify Frontend Build):** Ensure Vite compiles the code correctly.
    *   *Action:* Run the build command.
    *   *Command:* `cd /home/jasondel/dev/workstation/frontend && npm run build`
    *   *Success:* `dist/` folder is generated without compilation errors.

#### Phase 3: Integration & Deployment configuration
1.  **Step 3.A (Update backend tests for SPA serving):** Create a test asserting static routes return 200, but preserve 404 behavior for unknown API routes.
    *   *Target File:* `/home/jasondel/dev/workstation/backend/tests/test_spa.py`
    *   *Exact Change:* Create test logic handling the SPA fallback:
        ```python
        import pytest
        import os
        from fastapi.testclient import TestClient
        from app.main import app

        # Create a mock static/index.html to test against
        @pytest.fixture(autouse=True)
        def setup_static():
            base_dir = os.path.join(os.path.dirname(__file__), "..", "app", "static")
            os.makedirs(base_dir, exist_ok=True)
            index_path = os.path.join(base_dir, "index.html")
            with open(index_path, "w") as f:
                f.write("<html>Mock Frontend</html>")
            yield
            # Teardown logic
            os.remove(index_path)
            try:
                os.rmdir(base_dir)
            except OSError:
                pass

        client = TestClient(app)

        def test_frontend_fallback_route():
            # Any non-API route should fallback to index.html
            response = client.get("/some-react-route")
            assert response.status_code == 200
            assert "Mock Frontend" in response.text

        def test_api_404_remains():
            # Missing API routes should still 404
            response = client.get("/api/unknown")
            assert response.status_code == 404
        ```
2.  **Step 3.B (Implement SPA catch-all route in FastAPI):** Route any unmatched path to the generated `index.html`.
    *   *Target File:* `/home/jasondel/dev/workstation/backend/app/main.py`
    *   *Exact Change:* Overwrite the file to include SPA mounting logic:
        ```python
        from fastapi import FastAPI, Request
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
        from app.api.health import router as health_router
        import os

        app = FastAPI(title="Workstation Lite API")

        # Mount API routes
        app.include_router(health_router, prefix="/api")

        # Static assets routing
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        assets_dir = os.path.join(static_dir, "assets")

        # Ensure directory exists to avoid startup errors during dev
        os.makedirs(assets_dir, exist_ok=True)

        # Mount the /assets directory for CSS/JS
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.middleware("http")
        async def spa_middleware(request: Request, call_next):
            response = await call_next(request)
            
            # If the request is not for /api/ and returned a 404, we assume it's an SPA route
            if response.status_code == 404 and not request.url.path.startswith("/api/"):
                index_path = os.path.join(static_dir, "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
                    
            return response
        ```
    *   *Action:* Verify test logic passes by running `cd /home/jasondel/dev/workstation/backend && source venv/bin/activate && pytest`.
3.  **Step 3.C (Create multi-stage Dockerfile):** Consolidate frontend and backend into a single container.
    *   *Target File:* `/home/jasondel/dev/workstation/Dockerfile`
    *   *Exact Change:* Define the build pipeline:
        ```dockerfile
        # Stage 1: Build Frontend
        FROM node:20-alpine AS frontend-builder
        WORKDIR /app/frontend
        COPY frontend/package*.json ./
        RUN npm ci || npm install
        COPY frontend/ ./
        RUN npm run build

        # Stage 2: Build Backend & Serve
        FROM python:3.11-slim
        WORKDIR /app

        # Install backend dependencies
        COPY backend/requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        # Copy backend source
        COPY backend/app ./app

        # Copy built frontend assets to the location FastAPI expects
        COPY --from=frontend-builder /app/frontend/dist ./app/static

        # Expose port required by Cloud Run
        ENV PORT=8080
        EXPOSE 8080

        # Run Uvicorn
        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
        ```
4.  **Step 3.D (Create Cloud Run deployment script):** Create a robust `deploy.sh` script to automate deployment.
    *   *Target File:* `/home/jasondel/dev/workstation/deploy.sh`
    *   *Exact Change:* Create the shell script with proper error handling:
        ```bash
        #!/bin/bash
        set -e

        # Default configuration
        SERVICE_NAME=${SERVICE_NAME:-"workstation-lite"}
        REGION=${REGION:-"us-central1"}
        PROJECT_ID=$(gcloud config get-value project)

        if [ -z "$PROJECT_ID" ]; then
            echo "Error: No GCP project configured. Run 'gcloud config set project <YOUR_PROJECT_ID>'."
            exit 1
        fi

        echo "Deploying $SERVICE_NAME to Google Cloud Run in $REGION for project $PROJECT_ID..."

        # Deploy directly from source using Cloud Build integration
        gcloud run deploy "$SERVICE_NAME" \
            --source . \
            --region "$REGION" \
            --project "$PROJECT_ID" \
            --allow-unauthenticated \
            --port 8080

        echo "✅ Deployment complete!"
        ```
    *   *Action:* Make the script executable: `chmod +x /home/jasondel/dev/workstation/deploy.sh`.

### 🧪 Global Testing Strategy
*   **Unit Tests:** Pure testing of Python API routes via `TestClient`. Mocking of frontend static paths using temp files during test.
*   **Integration Tests:** Verify that Vite-built `/dist` structure precisely matches the expectations of the FastAPI SPA fallback logic by running `npm run build` and verifying Docker build succeeds.

## 🎯 Success Criteria
*   Backend directory is correctly scaffolded with Python dependencies and tests.
*   Frontend directory is correctly scaffolded with Vite, React, TS, and MUI.
*   The `Dockerfile` successfully builds a multi-stage image incorporating both tiers.
*   A single execution of `deploy.sh` is configured to push the entire repository to Google Cloud Run from source.
