import pytest
from unittest.mock import MagicMock, patch
from google.api_core import exceptions
from app.services.artifact_registry import ArtifactRegistryManager

@patch("google.cloud.artifactregistry_v1.ArtifactRegistryClient")
def test_ensure_repository_creates_if_not_exists(mock_client_class):
    mock_client = mock_client_class.return_value
    
    manager = ArtifactRegistryManager()
    manager.ensure_repository("proj", "region", "repo")
    
    assert mock_client.create_repository.called
    args, kwargs = mock_client.create_repository.call_args
    assert kwargs['request']['repository_id'] == "repo"

@patch("google.cloud.artifactregistry_v1.ArtifactRegistryClient")
def test_ensure_repository_handles_already_exists(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.create_repository.side_effect = exceptions.AlreadyExists("Exists")
    
    manager = ArtifactRegistryManager()
    # Should not raise
    manager.ensure_repository("proj", "region", "repo")
    
    assert mock_client.create_repository.called
