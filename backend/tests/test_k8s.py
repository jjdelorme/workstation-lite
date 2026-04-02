import pytest
from unittest.mock import MagicMock, patch
from app.services.k8s import K8sManager

@pytest.fixture
def mock_k8s_client():
    with patch("kubernetes.client.CoreV1Api") as mock_core, \
         patch("kubernetes.client.AppsV1Api") as mock_apps, \
         patch("kubernetes.config.load_incluster_config"), \
         patch("kubernetes.config.load_kube_config"):
        yield mock_core.return_value, mock_apps.return_value

def test_ensure_namespace(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    # Mock namespace doesn't exist initially
    mock_core.read_namespace.side_effect = Exception("Not Found")
    
    manager.ensure_namespace("user-1")
    
    assert mock_core.create_namespace.called
    args, kwargs = mock_core.create_namespace.call_args
    assert kwargs['body'].metadata.name == "user-1"

def test_apply_pvc(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    # Mock PVC doesn't exist initially
    mock_core.read_namespaced_persistent_volume_claim.side_effect = Exception("Not Found")
    
    manager.apply_pvc("user-1", "workstation-pvc")
    
    assert mock_core.create_namespaced_persistent_volume_claim.called
    args, kwargs = mock_core.create_namespaced_persistent_volume_claim.call_args
    assert kwargs['namespace'] == "user-1"
    pvc = kwargs['body']
    assert pvc.spec.storage_class_name == "standard-rwo"

def test_apply_statefulset(mock_k8s_client):
    _, mock_apps = mock_k8s_client
    manager = K8sManager()
    
    # Mock StatefulSet doesn't exist initially
    mock_apps.read_namespaced_stateful_set.side_effect = Exception("Not Found")
    
    manager.apply_statefulset("user-1", "workstation", "image:latest", 1)
    
    assert mock_apps.create_namespaced_stateful_set.called
    args, kwargs = mock_apps.create_namespaced_stateful_set.call_args
    assert kwargs['namespace'] == "user-1"
    sts = kwargs['body']
    assert sts.spec.replicas == 1
    assert sts.spec.template.spec.containers[0].image == "image:latest"

def test_scale_workstation(mock_k8s_client):
    _, mock_apps = mock_k8s_client
    manager = K8sManager()
    
    manager.scale_workstation("user-1", "workstation", 0)
    
    assert mock_apps.patch_namespaced_stateful_set_scale.called
    args, kwargs = mock_apps.patch_namespaced_stateful_set_scale.call_args
    assert kwargs['namespace'] == "user-1"
    assert kwargs['body'].spec.replicas == 0

def test_save_workstation_config(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    # Mock CM doesn't exist initially
    mock_core.read_namespaced_config_map.side_effect = Exception("Not Found")
    
    manager.save_workstation_config("user-1", "ws-1", "custom-image")
    
    assert mock_core.create_namespaced_config_map.called
    args, kwargs = mock_core.create_namespaced_config_map.call_args
    import json
    assert json.loads(kwargs['body'].data['ws-1'])['image'] == "custom-image"

def test_get_workstation_config(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    mock_cm = MagicMock()
    import json
    mock_cm.data = {"ws-1": json.dumps({"image": "custom-image", "ports": [3000]})}
    mock_core.read_namespaced_config_map.return_value = mock_cm
    
    config = manager.get_workstation_config("user-1", "ws-1")
    assert config["image"] == "custom-image"

def test_get_pvc_volume_handle(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    # Mock PVC
    mock_pvc = MagicMock()
    mock_pvc.spec.volume_name = "pv-123"
    mock_core.read_namespaced_persistent_volume_claim.return_value = mock_pvc
    
    # Mock PV
    mock_pv = MagicMock()
    mock_pv.spec.csi.volume_handle = "projects/p/zones/z/disks/d"
    mock_core.read_persistent_volume.return_value = mock_pv
    
    handle = manager.get_pvc_volume_handle("user-1", "pvc-name")
    assert handle == "projects/p/zones/z/disks/d"

def test_scale_down_idle_workstations(mock_k8s_client):
    _, mock_apps = mock_k8s_client
    manager = K8sManager()
    
    # Mock list of STS
    mock_sts = MagicMock()
    mock_sts.metadata.namespace = "user-1"
    mock_sts.metadata.name = "workstation"
    mock_sts.spec.replicas = 1
    
    mock_list = MagicMock()
    mock_list.items = [mock_sts]
    mock_apps.list_stateful_set_for_all_namespaces.return_value = mock_list
    
    scaled = manager.scale_down_idle_workstations()
    
    assert "user-1" in scaled
    assert mock_apps.patch_namespaced_stateful_set_scale.called
