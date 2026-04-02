import os
import sys

# Add app to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.services.k8s import K8sManager

def main():
    user_ns = "user-1"
    k8s = K8sManager()
    k8s.delete_workstation_config(user_ns, "vscodium-image")
    print("Cleaned up vscodium-image recipe from ConfigMap.")

if __name__ == "__main__":
    main()
