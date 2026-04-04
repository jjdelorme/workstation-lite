import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@patch("app.api.workstations.get_k8s_manager")
def test_save_config_optional_image(mock_get_k8s_manager):
    mock_k8s = MagicMock()
    mock_get_k8s_manager.return_value = mock_k8s
    
    # Mock current config
    mock_k8s.get_workstation_config.return_value = {"image": "old-image", "ports": [3000]}
    
    # Call save-config with only ports
    response = client.post(
        "/api/workstations/user-1/save-config/test-ws",
        json={"ports": [8080, 9090]}
    )
    
    assert response.status_code == 200
    # Verify save_workstation_config was called with old image and new ports
    mock_k8s.save_workstation_config.assert_called_with("user-1", "test-ws", "old-image", [8080, 9090], '2000m', '8Gi', '10Gi', None, False, {}, False)

@patch("app.api.workstations.get_k8s_manager")
def test_save_config_with_image(mock_get_k8s_manager):
    mock_k8s = MagicMock()
    mock_get_k8s_manager.return_value = mock_k8s
    
    # Mock current config (though it shouldn't be used for image if provided)
    mock_k8s.get_workstation_config.return_value = {"image": "old-image", "ports": [3000]}
    
    # Call save-config with image and ports
    response = client.post(
        "/api/workstations/user-1/save-config/test-ws",
        json={"image": "new-image", "ports": [8080]}
    )
    
    assert response.status_code == 200
    mock_k8s.save_workstation_config.assert_called_with("user-1", "test-ws", "new-image", [8080], '2000m', '8Gi', '10Gi', None, False, {}, False)
