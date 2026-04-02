import os
import sys

# Add app to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.services.artifact_registry import ArtifactRegistryManager
from backend.app.core.config import settings

def main():
    print(f"Project: {settings.gcp_project_id}")
    print(f"Region: {settings.region}")
    
    ar = ArtifactRegistryManager()
    images = ar.list_images(settings.gcp_project_id, settings.region, "workstation-images")
    
    print(f"Found {len(images)} images.")
    for img in images:
        print(f" - {img['uri']} (Tags: {img['tags']})")

if __name__ == "__main__":
    main()
