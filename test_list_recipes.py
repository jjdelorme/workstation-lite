import sys
import os
import json
sys.path.insert(0, os.path.abspath('backend'))
from app.services.k8s import K8sManager
from app.core.config import settings

k8s = K8sManager()
k8s._refresh_config()
user_ns = "user-1"
configs = k8s.core_api.read_namespaced_config_map(name="workstation-configs", namespace=user_ns).data
print(f"Workstation Configs: {json.dumps(configs, indent=2)}")
