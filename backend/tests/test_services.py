import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.services.k8s import K8sManager
from app.main import app
from app.models.service import DEFAULT_SERVICE_CATALOG, ServiceStatus

client = TestClient(app)


# ── Model tests ──────────────────────────────────────────────────────────

def test_service_catalog_has_entries():
    assert len(DEFAULT_SERVICE_CATALOG) >= 5
    types = [e.service_type for e in DEFAULT_SERVICE_CATALOG]
    assert "postgresql" in types
    assert "redis" in types
    assert "mysql" in types
    assert "mongodb" in types
    assert "rabbitmq" in types


def test_service_catalog_postgresql_has_required_env():
    pg = next(e for e in DEFAULT_SERVICE_CATALOG if e.service_type == "postgresql")
    assert pg.image == "postgres:16"
    assert 5432 in pg.ports
    assert "PGDATA" in pg.required_env_vars


def test_service_status_enum():
    assert ServiceStatus.RUNNING == "RUNNING"
    assert ServiceStatus.STOPPED == "STOPPED"


# ── K8s manager tests ───────────────────────────────────────────────────

@pytest.fixture
def mock_k8s_client():
    with patch("kubernetes.client.CoreV1Api") as mock_core, \
         patch("kubernetes.client.AppsV1Api") as mock_apps, \
         patch("kubernetes.config.load_incluster_config"), \
         patch("kubernetes.config.load_kube_config"):
        yield mock_core.return_value, mock_apps.return_value


def test_apply_service_statefulset(mock_k8s_client):
    _, mock_apps = mock_k8s_client
    manager = K8sManager()

    mock_apps.read_namespaced_stateful_set.side_effect = Exception("Not Found")

    manager.apply_service_statefulset(
        "user-1", "my-postgres", "postgres:16", 1,
        ports=[5432], cpu="2000m", memory="8Gi",
        data_mount_path="/var/lib/postgresql/data",
        health_check_command=["pg_isready"],
    )

    assert mock_apps.create_namespaced_stateful_set.called
    args, kwargs = mock_apps.create_namespaced_stateful_set.call_args
    assert kwargs['namespace'] == "user-1"
    sts = kwargs['body']
    assert sts.metadata.name == "svc-my-postgres"
    assert sts.metadata.labels["resource-type"] == "service"
    assert sts.spec.template.spec.containers[0].image == "postgres:16"
    assert sts.spec.template.spec.containers[0].readiness_probe is not None


def test_apply_cluster_ip_service(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()

    mock_core.read_namespaced_service.side_effect = Exception("Not Found")

    manager.apply_cluster_ip_service("user-1", "my-postgres", [5432])

    assert mock_core.create_namespaced_service.called
    args, kwargs = mock_core.create_namespaced_service.call_args
    svc = kwargs['body']
    assert svc.metadata.name == "svc-my-postgres"
    assert svc.spec.type == "ClusterIP"
    assert svc.spec.ports[0].port == 5432


def test_scale_service(mock_k8s_client):
    _, mock_apps = mock_k8s_client
    manager = K8sManager()

    manager.scale_service("user-1", "my-postgres", 0)

    assert mock_apps.patch_namespaced_stateful_set_scale.called
    args, kwargs = mock_apps.patch_namespaced_stateful_set_scale.call_args
    assert kwargs['name'] == "svc-my-postgres"
    assert kwargs['body'].spec.replicas == 0


def test_save_service_config(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()

    mock_core.read_namespaced_config_map.side_effect = Exception("Not Found")

    manager.save_service_config(
        "user-1", "my-postgres", "postgres:16", "postgresql", [5432],
        data_mount_path="/var/lib/postgresql/data",
        health_check_command=["pg_isready"],
    )

    assert mock_core.create_namespaced_config_map.called
    args, kwargs = mock_core.create_namespaced_config_map.call_args
    parsed = json.loads(kwargs['body'].data['my-postgres'])
    assert parsed['image'] == "postgres:16"
    assert parsed['service_type'] == "postgresql"
    assert parsed['ports'] == [5432]
    assert parsed['data_mount_path'] == "/var/lib/postgresql/data"
    assert parsed['health_check_command'] == ["pg_isready"]


def test_get_service_config(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()

    mock_cm = MagicMock()
    mock_cm.data = {"my-postgres": json.dumps({
        "image": "postgres:16", "service_type": "postgresql",
        "ports": [5432], "cpu": "2000m", "memory": "8Gi",
        "disk_size": "5Gi", "env_vars": {"POSTGRES_PASSWORD": "secret"},
        "data_mount_path": "/var/lib/postgresql/data",
        "health_check_command": ["pg_isready"],
    })}
    mock_core.read_namespaced_config_map.return_value = mock_cm

    config = manager.get_service_config("user-1", "my-postgres")
    assert config["image"] == "postgres:16"
    assert config["service_type"] == "postgresql"
    assert config["env_vars"]["POSTGRES_PASSWORD"] == "secret"
    assert config["data_mount_path"] == "/var/lib/postgresql/data"
    assert config["health_check_command"] == ["pg_isready"]


def test_get_service_config_default(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()

    mock_core.read_namespaced_config_map.side_effect = Exception("Not Found")

    config = manager.get_service_config("user-1", "nonexistent")
    assert config["image"] is None
    assert config["cpu"] == "2000m"
    assert config["data_mount_path"] == "/data"
    assert config["health_check_command"] == []


def test_delete_service(mock_k8s_client):
    mock_core, mock_apps = mock_k8s_client
    manager = K8sManager()

    manager.delete_service("user-1", "my-postgres")

    mock_apps.delete_namespaced_stateful_set.assert_called_with(
        name="svc-my-postgres", namespace="user-1"
    )
    mock_core.delete_namespaced_service.assert_called_with(
        name="svc-my-postgres", namespace="user-1"
    )
    mock_core.delete_namespaced_persistent_volume_claim.assert_called_with(
        name="svc-my-postgres-pvc", namespace="user-1"
    )


def test_list_services(mock_k8s_client):
    mock_core, mock_apps = mock_k8s_client
    manager = K8sManager()

    mock_sts = MagicMock()
    mock_sts.metadata.name = "svc-my-redis"
    mock_sts.spec.template.spec.containers = [MagicMock(image="redis:7")]
    mock_sts.spec.replicas = 1
    mock_sts.status.ready_replicas = 1

    mock_list = MagicMock()
    mock_list.items = [mock_sts]
    mock_apps.list_namespaced_stateful_set.return_value = mock_list

    mock_pod = MagicMock()
    mock_pod.status.container_statuses = [MagicMock(state=MagicMock(waiting=None, terminated=None))]
    mock_core.read_namespaced_pod.return_value = mock_pod

    mock_sts_read = MagicMock()
    mock_sts_read.status.ready_replicas = 1
    mock_sts_read.spec.replicas = 1
    mock_apps.read_namespaced_stateful_set.return_value = mock_sts_read

    services = manager.list_services("user-1")
    assert len(services) == 1
    assert services[0]["name"] == "my-redis"
    assert services[0]["status"] == "RUNNING"


def test_seed_service_catalog_templates(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()

    # read raises 404 so seed falls through to create
    mock_core.read_namespaced_config_map.side_effect = Exception("Not Found")

    manager.seed_service_catalog_templates()

    assert mock_core.create_namespaced_config_map.called
    args, kwargs = mock_core.create_namespaced_config_map.call_args
    assert kwargs['namespace'] == "default"
    cm = kwargs['body']
    assert "postgresql" in cm.data
    parsed = json.loads(cm.data["postgresql"])
    assert parsed["image"] == "postgres:16"
    assert parsed["required_env_vars"]["PGDATA"] == "/var/lib/postgresql/data/pgdata"


def test_get_service_catalog_templates_from_configmap(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()

    mock_cm = MagicMock()
    mock_cm.data = {
        "postgresql": json.dumps({
            "service_type": "postgresql", "label": "PostgreSQL 16",
            "image": "postgres:16", "ports": [5432],
            "data_mount_path": "/var/lib/postgresql/data",
            "health_check_command": ["pg_isready"],
            "required_env_vars": {"PGDATA": "/var/lib/postgresql/data/pgdata"},
        }),
    }
    mock_core.read_namespaced_config_map.return_value = mock_cm

    templates = manager.get_service_catalog_templates()
    assert len(templates) == 1
    assert templates[0]["service_type"] == "postgresql"
    assert templates[0]["image"] == "postgres:16"


def test_get_service_catalog_templates_seeds_on_404(mock_k8s_client):
    mock_core, _ = mock_k8s_client
    manager = K8sManager()

    # Call sequence: get reads (404) → seed reads (404) → seed creates →
    #                get retries read → returns data
    not_found_exc1 = type('ApiException', (Exception,), {'status': 404})()
    not_found_exc2 = type('ApiException', (Exception,), {'status': 404})()
    mock_cm = MagicMock()
    mock_cm.data = {
        "redis": json.dumps({
            "service_type": "redis", "label": "Redis 7",
            "image": "redis:7", "ports": [6379],
            "data_mount_path": "/data",
            "health_check_command": ["redis-cli", "ping"],
            "required_env_vars": {},
        }),
    }
    mock_core.read_namespaced_config_map.side_effect = [not_found_exc1, not_found_exc2, mock_cm]

    templates = manager.get_service_catalog_templates()
    assert mock_core.create_namespaced_config_map.called  # seed was called
    assert len(templates) == 1


# ── API tests ────────────────────────────────────────────────────────────

@patch("app.api.services.get_k8s_manager")
def test_catalog_endpoint(mock_get_k8s):
    mock_k8s = MagicMock()
    mock_get_k8s.return_value = mock_k8s
    mock_k8s.get_service_catalog_templates.return_value = [
        {"service_type": "postgresql", "label": "PostgreSQL 16", "image": "postgres:16",
         "ports": [5432], "data_mount_path": "/var/lib/postgresql/data",
         "health_check_command": ["pg_isready"], "required_env_vars": {}},
    ]

    response = client.get("/api/services/catalog")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service_type"] == "postgresql"


@patch("app.api.services.get_k8s_manager")
def test_list_services_api(mock_get_k8s):
    mock_k8s = MagicMock()
    mock_get_k8s.return_value = mock_k8s
    mock_k8s.list_services.return_value = []

    response = client.get("/api/services/user-1/list")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["services"] == []


@patch("app.api.services.get_k8s_manager")
def test_save_service_config_api(mock_get_k8s):
    mock_k8s = MagicMock()
    mock_get_k8s.return_value = mock_k8s
    mock_k8s.get_service_config.return_value = {
        "image": None, "service_type": "custom", "ports": [],
        "cpu": "2000m", "memory": "8Gi", "disk_size": "5Gi", "env_vars": {},
        "data_mount_path": "/data", "health_check_command": [],
    }

    response = client.post("/api/services/user-1/save-config/my-pg", json={
        "service_type": "postgresql",
        "image": "postgres:16",
        "ports": [5432],
        "env_vars": {"POSTGRES_PASSWORD": "secret", "PGDATA": "/var/lib/postgresql/data/pgdata"},
        "data_mount_path": "/var/lib/postgresql/data",
        "health_check_command": ["pg_isready"],
    })
    assert response.status_code == 200
    assert mock_k8s.save_service_config.called
    call_args = mock_k8s.save_service_config.call_args
    assert call_args[0][1] == "my-pg"
    assert call_args[0][2] == "postgres:16"


@patch("app.api.services.get_k8s_manager")
def test_stop_service_api(mock_get_k8s):
    mock_k8s = MagicMock()
    mock_get_k8s.return_value = mock_k8s

    response = client.post("/api/services/user-1/stop/my-pg")
    assert response.status_code == 200
    mock_k8s.scale_service.assert_called_with("user-1", "my-pg", 0)


@patch("app.api.services.get_k8s_manager")
def test_delete_service_api(mock_get_k8s):
    mock_k8s = MagicMock()
    mock_get_k8s.return_value = mock_k8s

    response = client.post("/api/services/user-1/delete/my-pg")
    assert response.status_code == 200
    mock_k8s.delete_service.assert_called_with("user-1", "my-pg")


@patch("app.api.services.get_k8s_manager")
@patch("app.api.services.settings")
def test_connect_script_api(mock_settings, mock_get_k8s):
    mock_settings.cluster_name = "test-cluster"
    mock_settings.gcp_project_id = "test-project"
    mock_settings.region = "us-central1"

    mock_k8s = MagicMock()
    mock_get_k8s.return_value = mock_k8s
    mock_k8s.get_service_config.return_value = {
        "image": "postgres:16", "service_type": "postgresql",
        "ports": [5432], "cpu": "2000m", "memory": "8Gi",
        "disk_size": "5Gi", "env_vars": {},
        "data_mount_path": "/var/lib/postgresql/data",
        "health_check_command": ["pg_isready"],
    }

    response = client.get("/api/services/user-1/connect/my-pg")
    assert response.status_code == 200
    assert "port-forward" in response.text.lower()
    assert "svc-my-pg-0" in response.text


@patch("app.api.services.get_k8s_manager")
@patch("app.api.services.settings")
def test_exec_script_api(mock_settings, mock_get_k8s):
    mock_settings.cluster_name = "test-cluster"
    mock_settings.gcp_project_id = "test-project"
    mock_settings.region = "us-central1"

    response = client.get("/api/services/user-1/exec/my-pg")
    assert response.status_code == 200
    assert "svc-my-pg-0" in response.text
    assert "exec" in response.text.lower()
