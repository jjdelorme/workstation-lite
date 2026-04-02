from google.cloud import artifactregistry_v1
from google.api_core import exceptions
import logging

logger = logging.getLogger(__name__)

class ArtifactRegistryManager:
    def __init__(self):
        self.client = artifactregistry_v1.ArtifactRegistryClient()

    def ensure_repository(self, project_id: str, region: str, repo_name: str):
        parent = f"projects/{project_id}/locations/{region}"
        repo = artifactregistry_v1.Repository(
            format_=artifactregistry_v1.Repository.Format.DOCKER
        )
        try:
            self.client.create_repository(
                request={
                    "parent": parent,
                    "repository_id": repo_name,
                    "repository": repo
                }
            )
            logger.info(f"Repository {repo_name} created in {region}")
        except exceptions.AlreadyExists:
            logger.info(f"Repository {repo_name} already exists in {region}")
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            raise e

    def delete_package(self, project_id: str, region: str, repo_name: str, package_name: str):
        name = f"projects/{project_id}/locations/{region}/repositories/{repo_name}/packages/{package_name}"
        try:
            # Operation is returned
            op = self.client.delete_package(request={"name": name})
            op.result() # Wait for completion
            logger.info(f"Deleted package {name}")
            return True
        except exceptions.NotFound:
            logger.info(f"Package {name} not found, already deleted.")
            return True
        except Exception as e:
            logger.error(f"Error deleting package {name}: {e}")
            raise e

    def list_images(self, project_id: str, region: str, repo_name: str):
        parent = f"projects/{project_id}/locations/{region}/repositories/{repo_name}"
        try:
            # We use list_docker_images for a higher-level view of images in a repository
            results = self.client.list_docker_images(request={"parent": parent})
            images = []
            for img in results:
                # ONLY include images that have tags. Untagged images are usually old build artifacts.
                if img.tags:
                    images.append({
                        "uri": img.uri,
                        "tags": list(img.tags),
                        "update_time": img.update_time.isoformat() if img.update_time else None,
                        "media_type": img.media_type
                    })
            return images
        except Exception as e:
            logger.error(f"Error listing images in {repo_name}: {e}")
            return []
