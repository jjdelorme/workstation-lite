import pytest
from unittest.mock import MagicMock, patch
from app.services.compute import ComputeManager

@patch("google.cloud.compute_v1.SnapshotsClient")
def test_create_disk_snapshot(mock_client_class):
    mock_client = mock_client_class.return_value
    
    manager = ComputeManager()
    manager.create_disk_snapshot("proj", "zone", "disk", "snap")
    
    assert mock_client.insert.called
    args, kwargs = mock_client.insert.call_args
    req = kwargs['request']
    assert req['project'] == "proj"
    assert req['snapshot_resource'].name == "snap"
    assert "disks/disk" in req['snapshot_resource'].source_disk
