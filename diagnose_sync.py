import os
import sys

# Add app to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.services.k8s import K8sManager
from backend.app.services.artifact_registry import ArtifactRegistryManager
from backend.app.core.config import settings

def main():
    user_ns = "user-1"
    k8s = K8sManager()
    ar = ArtifactRegistryManager()
    
    print("--- K8S WORKSTATIONS (StatefulSets) ---")
    stss = k8s.apps_api.list_namespaced_stateful_set(namespace=user_ns, label_selector="managed-by=workstation-lite")
    for sts in stss.items:
        print(f"Workstation: {sts.metadata.name}")

    print("\n--- CONFIGMAP: workstation-configs ---")
    try:
        cm = k8s.core_api.read_namespaced_config_map(name="workstation-configs", namespace=user_ns)
        for name, img in (cm.data or {}).items():
            print(f"Recipe: {name} -> {img}")
    except Exception as e:
        print(f"Error or Not Found: {e}")

    print("\n--- CONFIGMAP: image-dockerfiles ---")
    try:
        cm = k8s.core_api.read_namespaced_config_map(name="image-dockerfiles", namespace=user_ns)
        for name in (cm.data or {}).keys():
            print(f"Dockerfile for: {name}")
    except Exception as e:
        print(f"Error or Not Found: {e}")

    print("\n--- ARTIFACT REGISTRY (Tagged Images) ---")
    images = ar.list_images(settings.gcp_project_id, settings.region, "workstation-images")
    for img in images:
        print(f"Image: {img['uri']} (Tags: {img['tags']})")

if __name__ == "__main__":
    main()
