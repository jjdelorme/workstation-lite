import pytest
from unittest.mock import MagicMock, patch
from google.api_core import exceptions
from app.services.gke import GKEManager

@patch("google.cloud.container_v1.ClusterManagerClient")
def test_check_cluster_exists_true(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.get_cluster.return_value = MagicMock()
    
    manager = GKEManager()
    exists = manager.check_cluster_exists("proj", "region", "cluster")
    
    assert exists is True
    mock_client.get_cluster.assert_called_once()

@patch("google.cloud.container_v1.ClusterManagerClient")
def test_check_cluster_exists_false(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.get_cluster.side_effect = exceptions.NotFound("Not Found")
    
    manager = GKEManager()
    exists = manager.check_cluster_exists("proj", "region", "cluster")
    
    assert exists is False

@patch("google.cloud.container_v1.ClusterManagerClient")
def test_create_autopilot_cluster(mock_client_class):
    mock_client = mock_client_class.return_value
    
    manager = GKEManager()
    manager.create_autopilot_cluster("proj", "region", "cluster")
    
    # Check that create_cluster was called with autopilot enabled
    args, kwargs = mock_client.create_cluster.call_args
    cluster_obj = kwargs['cluster']
    assert cluster_obj.autopilot.enabled is True
    assert cluster_obj.name == "cluster"
