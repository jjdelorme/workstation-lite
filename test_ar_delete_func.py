import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.services.artifact_registry import ArtifactRegistryManager
from app.core.config import settings

ar = ArtifactRegistryManager()
# We don't want to actually delete it in test, just checking if the path building is correct:
print(f"Name to delete: projects/{settings.gcp_project_id}/locations/{settings.region}/repositories/workstation-images/packages/user-1-openvs-workstation")
