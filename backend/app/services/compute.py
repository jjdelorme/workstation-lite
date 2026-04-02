from google.cloud import compute_v1
import logging

logger = logging.getLogger(__name__)

class ComputeManager:
    def __init__(self):
        self.snapshots_client = compute_v1.SnapshotsClient()

    def create_disk_snapshot(self, project_id: str, zone: str, disk_name: str, snapshot_name: str):
        snapshot_resource = compute_v1.Snapshot(
            name=snapshot_name,
            source_disk=f"projects/{project_id}/zones/{zone}/disks/{disk_name}"
        )
        try:
            operation = self.snapshots_client.insert(
                request={
                    "project": project_id,
                    "snapshot_resource": snapshot_resource
                }
            )
            logger.info(f"Snapshot {snapshot_name} creation initiated for disk {disk_name}")
            return operation.name
        except Exception as e:
            logger.error(f"Error creating disk snapshot: {e}")
            raise e
