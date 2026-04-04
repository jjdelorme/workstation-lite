import pytest
import base64
from unittest.mock import MagicMock, patch
from app.services.k8s import K8sManager

@pytest.fixture
def mock_k8s_client():
    with patch("kubernetes.client.CoreV1Api") as mock_core, \
         patch("kubernetes.client.AppsV1Api") as mock_apps, \
         patch("kubernetes.config.load_incluster_config"), \
         patch("kubernetes.config.load_kube_config"):
        yield mock_core.return_value, mock_apps.return_value

def test_save_ssh_key_create(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    # Mock secret doesn't exist
    mock_core.read_namespaced_secret.side_effect = Exception("Not Found")
    
    ssh_key = "test-ssh-key"
    manager.save_ssh_key("user-1", ssh_key)
    
    assert mock_core.create_namespaced_secret.called
    kwargs = mock_core.create_namespaced_secret.call_args[1]
    assert kwargs['namespace'] == "user-1"
    secret = kwargs['body']
    assert secret.metadata.name == "ssh-key-secret"
    assert secret.data["id_rsa"] == base64.b64encode(ssh_key.encode()).decode()

def test_save_ssh_key_update(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    # Mock secret exists
    mock_core.read_namespaced_secret.return_value = MagicMock()
    
    ssh_key = "new-ssh-key"
    manager.save_ssh_key("user-1", ssh_key)
    
    assert mock_core.replace_namespaced_secret.called
    kwargs = mock_core.replace_namespaced_secret.call_args[1]
    assert kwargs['name'] == "ssh-key-secret"
    secret = kwargs['body']
    assert secret.data["id_rsa"] == base64.b64encode(ssh_key.encode()).decode()

def test_check_ssh_key_exists(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    mock_core.read_namespaced_secret.return_value = MagicMock()
    assert manager.check_ssh_key("user-1") is True

def test_check_ssh_key_not_exists(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()
    
    mock_core.read_namespaced_secret.side_effect = Exception("Not Found")
    assert manager.check_ssh_key("user-1") is False

def test_apply_statefulset_ssh_mount(mock_k8s_client):
    _, mock_apps = mock_k8s_client
    manager = K8sManager()
    
    mock_apps.read_namespaced_stateful_set.side_effect = Exception("Not Found")
    
    manager.apply_statefulset("user-1", "ws", "image", 1)
    
    assert mock_apps.create_namespaced_stateful_set.called
    sts = mock_apps.create_namespaced_stateful_set.call_args[1]['body']
    pod_spec = sts.spec.template.spec
    
    # Check volume mount
    container = pod_spec.containers[0]
    ssh_mount = next(m for m in container.volume_mounts if m.name == "ssh-key")
    assert ssh_mount.mount_path == "/home/workspace/.ssh"
    assert ssh_mount.read_only is True
    
    # Check volume
    ssh_vol = next(v for v in pod_spec.volumes if v.name == "ssh-key")
    assert ssh_vol.secret.secret_name == "ssh-key-secret"
    assert ssh_vol.secret.default_mode == 0o600
    assert ssh_vol.secret.optional is True
