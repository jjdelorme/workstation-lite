from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.models.service import (
    SaveServiceConfigRequest, ServiceResponse, ServiceListResponse,
    ServiceStatus, SERVICE_CATALOG, SERVICE_CATALOG_BY_TYPE,
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/services", tags=["services"])

_k8s_manager = None


def get_k8s_manager():
    global _k8s_manager
    if _k8s_manager is None:
        from app.services.k8s import K8sManager
        _k8s_manager = K8sManager()
    _k8s_manager._refresh_config()
    return _k8s_manager


@router.get("/catalog")
def list_service_catalog():
    return [entry.model_dump() for entry in SERVICE_CATALOG]


@router.get("/{user_ns}/list", response_model=ServiceListResponse)
def list_all_services(user_ns: str):
    res = get_k8s_manager().list_services(user_ns)
    services = []
    for s in res:
        config = get_k8s_manager().get_service_config(user_ns, s["name"])
        k8s_name = f"svc-{s['name']}"
        ports = config.get("ports", [])
        connect_hint = None
        if ports:
            connect_hint = f"{k8s_name}:{ports[0]}"
        services.append(
            ServiceResponse(
                name=s["name"],
                user_ns=user_ns,
                status=ServiceStatus(s["status"]),
                image=s.get("image"),
                service_type=config.get("service_type", "custom"),
                ports=ports,
                cpu=config.get("cpu", "250m"),
                memory=config.get("memory", "512Mi"),
                disk_size=config.get("disk_size", "5Gi"),
                env_vars=config.get("env_vars", {}),
                pod_name=s.get("pod_name"),
                pod_ready=s.get("pod_ready", False),
                message=s.get("message"),
                connect_hint=connect_hint,
            )
        )
    return ServiceListResponse(services=services, count=len(services))


@router.post("/{user_ns}/save-config/{name}")
def save_service_config_endpoint(user_ns: str, name: str, req: SaveServiceConfigRequest):
    try:
        current_config = get_k8s_manager().get_service_config(user_ns, name)

        # Resolve from catalog if service_type is provided and not custom
        catalog_entry = SERVICE_CATALOG_BY_TYPE.get(req.service_type)

        image = req.image if req.image else (
            catalog_entry.image if catalog_entry else current_config.get("image")
        )
        ports = req.ports if req.ports is not None else (
            catalog_entry.ports if catalog_entry else current_config.get("ports", [])
        )
        cpu = req.cpu if req.cpu is not None else current_config.get("cpu", "250m")
        memory = req.memory if req.memory is not None else current_config.get("memory", "512Mi")
        disk_size = req.disk_size if req.disk_size is not None else current_config.get("disk_size", "5Gi")
        env_vars = req.env_vars if req.env_vars is not None else current_config.get("env_vars", {})

        get_k8s_manager().save_service_config(
            user_ns, name, image, req.service_type, ports, cpu, memory, disk_size, env_vars,
        )
        return {"status": "ok", "message": f"Service config for {name} saved"}
    except Exception as e:
        logger.error(f"Error saving service config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_ns}/start/{name}")
def start_service(user_ns: str, name: str):
    try:
        get_k8s_manager().ensure_namespace(user_ns)

        config = get_k8s_manager().get_service_config(user_ns, name)
        image = config.get("image")
        if not image:
            raise HTTPException(status_code=400, detail="No image configured for this service")

        service_type = config.get("service_type", "custom")
        ports = config.get("ports", [])
        cpu = config.get("cpu", "250m")
        memory = config.get("memory", "512Mi")
        disk_size = config.get("disk_size", "5Gi")
        env_vars = config.get("env_vars", {})

        # Resolve catalog entry for mount path and health check
        catalog_entry = SERVICE_CATALOG_BY_TYPE.get(service_type)
        data_mount_path = catalog_entry.data_mount_path if catalog_entry else "/data"
        health_check_command = catalog_entry.health_check_command if catalog_entry else None

        # Ensure PVC
        k8s_name = f"svc-{name}"
        pvc_name = f"{k8s_name}-pvc"
        get_k8s_manager().apply_pvc(user_ns, pvc_name, size=disk_size)

        # Apply StatefulSet
        get_k8s_manager().apply_service_statefulset(
            user_ns, name, image, replicas=1,
            ports=ports, cpu=cpu, memory=memory,
            env_vars=env_vars,
            data_mount_path=data_mount_path,
            health_check_command=health_check_command,
        )

        # Apply ClusterIP Service
        if ports:
            get_k8s_manager().apply_cluster_ip_service(user_ns, name, ports)

        return {"status": "ok", "message": f"Service {name} start initiated", "image": image}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_ns}/stop/{name}")
def stop_service(user_ns: str, name: str):
    try:
        get_k8s_manager().scale_service(user_ns, name, 0)
        return {"status": "ok", "message": f"Service {name} stop initiated"}
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_ns}/delete/{name}")
def delete_service(user_ns: str, name: str):
    try:
        get_k8s_manager().delete_service(user_ns, name)
        return {"status": "ok", "message": f"Service {name} and its storage deleted"}
    except Exception as e:
        logger.error(f"Error deleting service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_ns}/status/{name}", response_model=ServiceResponse)
def get_service_status(user_ns: str, name: str):
    res = get_k8s_manager().get_service_status(user_ns, name)
    config = get_k8s_manager().get_service_config(user_ns, name)
    return ServiceResponse(
        name=name,
        user_ns=user_ns,
        status=ServiceStatus(res["status"]),
        image=config.get("image"),
        service_type=config.get("service_type", "custom"),
        ports=config.get("ports", []),
        pod_name=res.get("pod_name"),
        pod_ready=res.get("pod_ready", False),
        message=res.get("message"),
    )


@router.get("/{user_ns}/connect/{name}", response_class=PlainTextResponse)
def get_service_connect_script(user_ns: str, name: str):
    """Generate a port-forward script for connecting from a laptop."""
    try:
        cluster_name = settings.cluster_name
        project_id = settings.gcp_project_id
        region = settings.region

        config = get_k8s_manager().get_service_config(user_ns, name)
        ports = config.get("ports", [])
        k8s_name = f"svc-{name}"

        if not ports:
            return f"echo 'No ports configured for service {name}'\n"

        lsof_full = "lsof " + " ".join([f"-ti:{p}" for p in ports]) + " | xargs kill -9 2>/dev/null || true"
        pf_args = " ".join([f"{p}:{p}" for p in ports])

        script = f"""#!/bin/bash
# Port-Forward Script for Service: {name}
set -e

echo "Configuring port-forward to service {name}..."
gcloud config set project {project_id} --quiet
TOKEN=$(gcloud auth application-default print-access-token)
ENDPOINT=$(gcloud container clusters describe {cluster_name} --region {region} --format="value(endpoint)")

TEMP_BIN_DIR="/tmp/workstation-bin"
mkdir -p $TEMP_BIN_DIR
export PATH="$TEMP_BIN_DIR:$PATH"

if ! command -v kubectl &> /dev/null; then
    echo "kubectl not found, downloading standalone binary..."
    curl -s -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    mv kubectl $TEMP_BIN_DIR/
fi

echo "Starting port-forwarding ({','.join(map(str, ports))})..."
{lsof_full}

kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify port-forward pod/{k8s_name}-0 {pf_args} -n {user_ns} &
PF_PID=$!

trap "kill $PF_PID 2>/dev/null" EXIT

sleep 2
echo ""
echo "Port-forward active. Connect using:"
{chr(10).join([f'echo "  localhost:{p}"' for p in ports])}
echo ""
echo "Press Ctrl+C to stop."
wait $PF_PID
"""
        return script
    except Exception as e:
        logger.error(f"Error generating connect script: {e}")
        return f"echo 'Error generating connect script: {str(e)}'\n"


@router.get("/{user_ns}/exec/{name}", response_class=PlainTextResponse)
def get_service_exec_script(user_ns: str, name: str):
    """Generate an exec script for debug shell access into the service container."""
    try:
        cluster_name = settings.cluster_name
        project_id = settings.gcp_project_id
        region = settings.region
        k8s_name = f"svc-{name}"

        script = f"""#!/bin/bash
# Debug Shell for Service: {name}
set -e

echo "Connecting to service {name} debug shell..."
gcloud config set project {project_id} --quiet
TOKEN=$(gcloud auth application-default print-access-token)
ENDPOINT=$(gcloud container clusters describe {cluster_name} --region {region} --format="value(endpoint)")

TEMP_BIN_DIR="/tmp/workstation-bin"
mkdir -p $TEMP_BIN_DIR
export PATH="$TEMP_BIN_DIR:$PATH"

if ! command -v kubectl &> /dev/null; then
    echo "kubectl not found, downloading standalone binary..."
    curl -s -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    mv kubectl $TEMP_BIN_DIR/
fi

echo "Launching shell..."
kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec -it pod/{k8s_name}-0 -n {user_ns} -- /bin/sh < /dev/tty
"""
        return script
    except Exception as e:
        logger.error(f"Error generating exec script: {e}")
        return f"echo 'Error generating exec script: {str(e)}'\n"
