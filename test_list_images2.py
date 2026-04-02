import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.services.artifact_registry import ArtifactRegistryManager
from app.core.config import settings

ar = ArtifactRegistryManager()
images = ar.list_images(settings.gcp_project_id, settings.region, "workstation-images")
for img in images:
    print(img['uri'])
