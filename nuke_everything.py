import os
import sys

# Add app to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.services.k8s import K8sManager
from backend.app.core.config import settings

def main():
    user_ns = "user-1"
    k8s = K8sManager()
    
    print(f"--- NUKING ALL WORKSTATIONS IN {user_ns} ---")
    
    # 1. Delete all StatefulSets
    try:
        stss = k8s.apps_api.list_namespaced_stateful_set(namespace=user_ns, label_selector="managed-by=workstation-lite")
        for sts in stss.items:
            name = sts.metadata.name
            print(f"Deleting StatefulSet: {name}")
            k8s.delete_workstation(user_ns, name, delete_pvc=True)
    except Exception as e:
        print(f"Error deleting statefulsets: {e}")

    # 2. Cleanup any orphaned PVCs
    try:
        pvcs = k8s.core_api.list_namespaced_persistent_volume_claim(namespace=user_ns)
        for pvc in pvcs.items:
            name = pvc.metadata.name
            if name.endswith("-pvc"):
                print(f"Deleting orphaned PVC: {name}")
                k8s.core_api.delete_namespaced_persistent_volume_claim(name=name, namespace=user_ns)
    except Exception as e:
        print(f"Error deleting PVCs: {e}")

    # 3. Wipe ConfigMaps
    cms = ["workstation-configs", "image-dockerfiles"]
    for cm_name in cms:
        try:
            print(f"Deleting ConfigMap: {cm_name}")
            k8s.core_api.delete_namespaced_config_map(name=cm_name, namespace=user_ns)
        except Exception as e:
            print(f"Error deleting ConfigMap {cm_name}: {e}")

    print("\nNUKE COMPLETE. Workspace is fresh.")

if __name__ == "__main__":
    main()
