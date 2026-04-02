import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.services.artifact_registry import ArtifactRegistryManager
from app.core.config import settings

ar = ArtifactRegistryManager()
results = ar.client.list_packages(request={"parent": f"projects/{settings.gcp_project_id}/locations/{settings.region}/repositories/workstation-images"})
for pkg in results:
    print(pkg.name)
