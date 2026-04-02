from google.cloud import container_v1
from google.api_core import exceptions
import logging

logger = logging.getLogger(__name__)

class GKEManager:
    def __init__(self):
        self.client = container_v1.ClusterManagerClient()

    def check_cluster_exists(self, project_id: str, region: str, cluster_name: str) -> bool:
        return self.get_cluster_status(project_id, region, cluster_name) != "NOT_FOUND"

    def get_cluster_status(self, project_id: str, region: str, cluster_name: str) -> str:
        name = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}"
        try:
            cluster = self.client.get_cluster(request={"name": name})
            return cluster.status.name
        except exceptions.NotFound:
            return "NOT_FOUND"
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            raise e

    def create_autopilot_cluster(self, project_id: str, region: str, cluster_name: str):
        parent = f"projects/{project_id}/locations/{region}"
        cluster = container_v1.Cluster(
            name=cluster_name,
            autopilot=container_v1.Autopilot(enabled=True)
        )
        try:
            # This is a long-running operation
            operation = self.client.create_cluster(request={"parent": parent, "cluster": cluster})
            return operation
        except Exception as e:
            logger.error(f"Error creating autopilot cluster: {e}")
            raise e

    def delete_cluster(self, project_id: str, region: str, cluster_name: str):
        name = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}"
        try:
            operation = self.client.delete_cluster(request={"name": name})
            return operation
        except Exception as e:
            logger.error(f"Error deleting cluster: {e}")
            raise e
