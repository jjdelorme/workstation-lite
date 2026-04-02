import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.services.k8s import K8sManager
k8s = K8sManager()
k8s._refresh_config()

namespace = "user-1"
workstation_name = "test5"

print(f"--- Checking Pods for {workstation_name} in {namespace} ---")
pods = k8s.core_api.list_namespaced_pod(namespace, label_selector=f"app={workstation_name}")
for pod in pods.items:
    print(f"Pod: {pod.metadata.name}")
    print(f"Status: {pod.status.phase}")
    for container in pod.status.container_statuses:
        print(f"  Container: {container.name}")
        print(f"  Ready: {container.ready}")
        print(f"  Restart Count: {container.restart_count}")
        if container.state.waiting:
            print(f"  Waiting Reason: {container.state.waiting.reason}")
            print(f"  Waiting Message: {container.state.waiting.message}")
        if container.state.terminated:
            print(f"  Terminated Reason: {container.state.terminated.reason}")
            print(f"  Exit Code: {container.state.terminated.exit_code}")

    print("\n--- Latest Logs ---")
    try:
        logs = k8s.core_api.read_namespaced_pod_log(pod.metadata.name, namespace, tail_lines=50)
        print(logs)
    except Exception as e:
        print(f"Could not fetch logs: {e}")
