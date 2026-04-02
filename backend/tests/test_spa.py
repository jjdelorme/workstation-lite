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
    if os.path.exists(index_path):
        os.remove(index_path)
    try:
        if os.path.exists(base_dir):
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
