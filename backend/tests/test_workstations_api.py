import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_managers():
    with patch("app.api.workstations.get_gke_manager") as mock_get_gke, \
         patch("app.api.workstations.get_k8s_manager") as mock_get_k8s, \
         patch("app.api.workstations.get_ar_manager") as mock_get_ar, \
         patch("app.api.workstations.get_cb_manager") as mock_get_cb, \
         patch("app.api.workstations.settings") as mock_settings:
        
        mock_gke = MagicMock()
        mock_k8s = MagicMock()
        mock_ar = MagicMock()
        mock_cb = MagicMock()
        
        mock_get_gke.return_value = mock_gke
        mock_get_k8s.return_value = mock_k8s
        mock_get_ar.return_value = mock_ar
        mock_get_cb.return_value = mock_cb
        
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
    mock_k8s.get_workstation_config.return_value = {"image": "custom-image:latest"}
    
    response = client.post("/api/workstations/user-1/start/workstation")
    
    assert response.status_code == 200
    assert mock_k8s.apply_statefulset.called
    args, kwargs = mock_k8s.apply_statefulset.call_args
    assert args[2] == "custom-image:latest"

def test_build_workstation(mock_managers):
    _, mock_k8s, _, mock_cb = mock_managers
    mock_cb.build_custom_image.return_value = ("custom-image:latest", "build-123")
    
    response = client.post("/api/workstations/user-1/build/workstation", json={"dockerfile": "FROM base"})
    
    assert response.status_code == 200
    assert mock_cb.build_custom_image.called
    assert mock_k8s.save_workstation_config.called
    # It's called with (user_ns, name, image_tag)
    mock_k8s.save_workstation_config.assert_called_with("user-1", "workstation", "custom-image:latest")

def test_stop_workstation(mock_managers):
    _, mock_k8s, _, _ = mock_managers
    
    response = client.post("/api/workstations/user-1/stop/workstation")
    
    assert response.status_code == 200
    assert mock_k8s.scale_workstation.called
    mock_k8s.scale_workstation.assert_called_with("user-1", "workstation", 0)

def test_get_status(mock_managers):
    _, mock_k8s, _, _ = mock_managers
    mock_k8s.get_workstation_status.return_value = {"status": "RUNNING", "pod_name": "workstation-0", "pod_ready": True}
    
    response = client.get("/api/workstations/user-1/status/workstation")
    
    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"

def test_start_workstation_as_root(mock_managers):
    _, mock_k8s, _, _ = mock_managers
    mock_k8s.get_workstation_config.return_value = {
        "image": "custom-image:latest",
        "run_as_root": True
    }
    
    response = client.post("/api/workstations/user-1/start/workstation")
    
    assert response.status_code == 200
    assert mock_k8s.apply_statefulset.called
    args, kwargs = mock_k8s.apply_statefulset.call_args
    # args: (user_ns, name, final_image, replicas, ports, cpu, memory, gpu, env_vars, run_as_root)
    assert kwargs.get("run_as_root") is True

def test_save_config_as_root(mock_managers):
    _, mock_k8s, _, _ = mock_managers
    mock_k8s.get_workstation_config.return_value = {}

    response = client.post(
        "/api/workstations/user-1/save-config/workstation",
        json={"run_as_root": True, "image": "some-image"}
    )

    assert response.status_code == 200
    assert mock_k8s.save_workstation_config.called
    # args: (user_ns, name, image, ports, cpu, memory, disk_size, gpu, env_vars, run_as_root)
    call_args = mock_k8s.save_workstation_config.call_args[0]
    assert call_args[9] is True

@patch("app.api.workstations.get_compute_manager")
def test_snapshot_workstation(mock_get_compute, mock_managers):
    _, mock_k8s, _, _ = mock_managers
    mock_compute = MagicMock()
    mock_get_compute.return_value = mock_compute
    mock_k8s.get_pvc_volume_handle.return_value = "projects/my-project/zones/us-central1-a/disks/pvc-12345"
    
    response = client.post("/api/workstations/user-1/snapshot")
    
    assert response.status_code == 200
    assert mock_compute.create_disk_snapshot.called
