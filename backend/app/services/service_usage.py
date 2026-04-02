from google.cloud import service_usage_v1
import logging

logger = logging.getLogger(__name__)

class ServiceUsageManager:
    def __init__(self):
        self.client = service_usage_v1.ServiceUsageClient()

    def enable_service(self, project_id: str, service_name: str = "container.googleapis.com"):
        name = f"projects/{project_id}/services/{service_name}"
        try:
            # For google-cloud-service-usage 1.15.0, the first positional argument is request
            operation = self.client.enable_service(request={"name": name})
            logger.info(f"Enabling service {service_name} for project {project_id}")
            return operation
        except Exception as e:
            logger.error(f"Error enabling service {service_name}: {e}")
            raise e
