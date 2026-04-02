from backend.app.services.cloud_build import CloudBuildManager
from backend.app.core.config import settings
import time
cb = CloudBuildManager()

# Let's use a failing Dockerfile
dockerfile = """FROM ubuntu
RUN exit 1
"""

tag, bid = cb.build_custom_image(settings.gcp_project_id, settings.region, "user1", "failtest", dockerfile)
print(f"Triggered: {bid}")

while True:
    st = cb.get_build_status(settings.gcp_project_id, bid)
    print(st)
    if st['status'] in ['SUCCESS', 'FAILURE', 'TIMEOUT', 'INTERNAL_ERROR']:
        break
    time.sleep(2)
