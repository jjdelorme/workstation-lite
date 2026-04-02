import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)

@patch("app.api.admin.k8s_manager")
def test_scale_to_zero(mock_k8s):
    mock_k8s.scale_down_idle_workstations.return_value = ["user-1", "user-2"]
    
    response = client.post("/api/admin/scale-to-zero")
    
    assert response.status_code == 200
    assert response.json()["scaled_namespaces"] == ["user-1", "user-2"]
