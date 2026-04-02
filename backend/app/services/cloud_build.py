from google.cloud.devtools import cloudbuild_v1
import logging

logger = logging.getLogger(__name__)

class CloudBuildManager:
    def __init__(self):
        self.client = cloudbuild_v1.CloudBuildClient()

    def build_custom_image(self, project_id: str, region: str, user_ns: str, workstation_name: str, dockerfile_content: str) -> str:
        import base64
        # Use both user_ns and workstation_name for a unique image tag
        image_name = f"{user_ns}-{workstation_name}".lower().replace("_", "-")
        image_tag = f"{region}-docker.pkg.dev/{project_id}/workstation-images/{image_name}:latest"
        
        # Clean up the dockerfile: strip trailing whitespace and remove empty lines at the end
        lines = [line.rstrip() for line in dockerfile_content.splitlines()]
        cleaned_dockerfile = "\n".join(lines).strip() + "\n"
        
        encoded_dockerfile = base64.b64encode(cleaned_dockerfile.encode('utf-8')).decode('utf-8')
        
        # Split the encoded content into chunks to avoid "arg too long" errors
        # Max arg length in Cloud Build is 10,000, but we'll use a safer 8,000
        chunk_size = 8000
        chunks = [encoded_dockerfile[i:i+chunk_size] for i in range(0, len(encoded_dockerfile), chunk_size)]
        
        build_steps = []
        for i, chunk in enumerate(chunks):
            op = ">" if i == 0 else ">>"
            build_steps.append({
                "name": "ubuntu",
                "entrypoint": "bash",
                "args": ["-c", f"echo '{chunk}' {op} Dockerfile.base64"]
            })
        
        build_steps.extend([
            # 2. Decode Dockerfile
            {
                "name": "ubuntu",
                "entrypoint": "bash",
                "args": ["-c", "base64 -d Dockerfile.base64 > Dockerfile"]
            },
            # 3. Build image
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["build", "-t", image_tag, "."]
            },
            # 4. Push image
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["push", image_tag]
            }
        ])
        
        build = cloudbuild_v1.Build()
        build.steps = build_steps
        
        try:
            operation = self.client.create_build(request={"project_id": project_id, "build": build})
            # create_build returns a long-running operation. 
            # The build ID is in the metadata.
            build_id = operation.metadata.build.id
            return image_tag, build_id
        except Exception as e:
            logger.error(f"Error triggering cloud build: {e}")
            raise e

    def get_build_status(self, project_id: str, build_id: str) -> dict:
        try:
            build = self.client.get_build(request={"project_id": project_id, "id": build_id})
            return {
                "id": build.id,
                "status": build.status.name,
                "log_url": build.log_url
            }
        except Exception as e:
            logger.error(f"Error getting build status: {e}")
            raise e
