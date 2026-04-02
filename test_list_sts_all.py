import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.services.k8s import K8sManager
k8s = K8sManager()
k8s._refresh_config()
res = k8s.apps_api.list_stateful_set_for_all_namespaces()
for r in res.items:
    print(f"STS: {r.metadata.namespace}/{r.metadata.name}")
