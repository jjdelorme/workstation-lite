import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_managers():
    with patch("app.api.workstations.gke_manager") as mock_gke, \
         patch("app.api.workstations.k8s_manager") as mock_k8s, \
         patch("app.api.workstations.ar_manager") as mock_ar, \
         patch("app.api.workstations.cb_manager") as mock_cb, \
         patch("app.api.workstations.settings") as mock_settings:
        mock_settings.gcp_project_id = "test-project"
        mock_settings.region = "us-central1"
        mock_settings.cluster_name = "workstation-cluster"
        mock_settings.workstation_image = "codercom/code-server:latest"
        yield mock_gke, mock_k8s, mock_ar, mock_cb

def test_init_cluster(mock_managers):
    mock_gke, _, mock_ar, _ = mock_managers
    mock_gke.check_cluster_exists.return_value = False
    
    response = client.post("/api/workstations/init")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert mock_gke.create_autopilot_cluster.called
    assert mock_ar.ensure_repository.called

def test_start_workstation_custom_image(mock_managers):
    _, mock_k8s, _, _ = mock_managers
    mock_k8s.get_workstation_config.return_value = "custom-image:latest"
    
    response = client.post("/api/workstations/user-1/start")
    
    assert response.status_code == 200
    assert mock_k8s.apply_statefulset.called
    args, kwargs = mock_k8s.apply_statefulset.call_args
    assert args[2] == "custom-image:latest"

def test_build_workstation(mock_managers):
    _, mock_k8s, _, mock_cb = mock_managers
    mock_cb.build_custom_image.return_value = "custom-image:latest"
    
    response = client.post("/api/workstations/user-1/build", json={"dockerfile": "FROM base"})
    
    assert response.status_code == 200
    assert mock_cb.build_custom_image.called
    assert mock_k8s.save_workstation_config.called
    mock_k8s.save_workstation_config.assert_called_with("user-1", "custom-image:latest")

def test_stop_workstation(mock_managers):
    _, mock_k8s, _, _ = mock_managers
    
    response = client.post("/api/workstations/user-1/stop")
    
    assert response.status_code == 200
    assert mock_k8s.scale_workstation.called
    mock_k8s.scale_workstation.assert_called_with("user-1", "workstation", 0)

def test_get_status(mock_managers):
    _, mock_k8s, _, _ = mock_managers
    mock_k8s.get_workstation_status.return_value = "RUNNING"
    
    response = client.get("/api/workstations/user-1/status")
    
    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"

@patch("app.api.workstations.compute_manager")
def test_snapshot_workstation(mock_compute, mock_managers):
    _, mock_k8s, _, _ = mock_managers
    mock_k8s.get_pvc_volume_handle.return_value = "projects/my-project/zones/us-central1-a/disks/pvc-12345"
    
    response = client.post("/api/workstations/user-1/snapshot")
    
    assert response.status_code == 200
    assert mock_compute.create_disk_snapshot.called
