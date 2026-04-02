import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.services.k8s import K8sManager
k8s = K8sManager()
k8s._refresh_config()
res = k8s.apps_api.list_namespaced_stateful_set(namespace="user-1")
for r in res.items:
    print(r.metadata.name)
