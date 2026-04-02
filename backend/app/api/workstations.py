from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.services.gke import GKEManager
from app.services.artifact_registry import ArtifactRegistryManager
from app.services.cloud_build import CloudBuildManager
from app.services.compute import ComputeManager
from app.services.service_usage import ServiceUsageManager
from app.models.workstation import WorkstationResponse, WorkstationListResponse, WorkstationStatus, BuildRequest, SaveConfigRequest
from app.core.config import settings
import google.auth
import logging
import time
import subprocess

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workstations", tags=["workstations"])

# Global singletons (instantiated on first use)
_gke_manager = None
_ar_manager = None
_cb_manager = None
_compute_manager = None
_service_usage_manager = None
_k8s_manager = None

def get_k8s_manager():
    global _k8s_manager
    if _k8s_manager is None:
        from app.services.k8s import K8sManager
        _k8s_manager = K8sManager()
    _k8s_manager._refresh_config()
    return _k8s_manager

def get_gke_manager():
    global _gke_manager
    if _gke_manager is None:
        _gke_manager = GKEManager()
    return _gke_manager

def get_ar_manager():
    global _ar_manager
    if _ar_manager is None:
        _ar_manager = ArtifactRegistryManager()
    return _ar_manager

def get_cb_manager():
    global _cb_manager
    if _cb_manager is None:
        _cb_manager = CloudBuildManager()
    return _cb_manager

def get_compute_manager():
    global _compute_manager
    if _compute_manager is None:
        _compute_manager = ComputeManager()
    return _compute_manager

def get_service_usage_manager():
    global _service_usage_manager
    if _service_usage_manager is None:
        _service_usage_manager = ServiceUsageManager()
    return _service_usage_manager

@router.get("/config")
def get_app_config():
    try:
        account = None
        try:
            credentials, project = google.auth.default()
            if hasattr(credentials, 'service_account_email') and credentials.service_account_email:
                account = credentials.service_account_email
            elif hasattr(credentials, 'signer_email') and credentials.signer_email:
                account = credentials.signer_email
            elif hasattr(credentials, 'account') and credentials.account:
                account = credentials.account
        except Exception as auth_e:
            logger.warning(f"Google auth default failed: {auth_e}")

        # Fallback to gcloud config if running locally and still unknown

        if not account:
            # try:
            #     result = subprocess.run(
            #         ["gcloud", "config", "get-value", "account"],
            #         capture_output=True,
            #         text=True,
            #         check=False
            #     )
            #     if result.returncode == 0 and result.stdout.strip():
            #         account = result.stdout.strip()
            # except Exception:
            #     pass
            pass
        return {
            "project_id": settings.gcp_project_id,
            "region": settings.region,
            "account": account or "Unknown"
        }
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return {
            "project_id": settings.gcp_project_id,
            "region": settings.region,
            "account": "Error"
        }

@router.post("/enable-gke")
def enable_gke_api():
    try:
        if not settings.gcp_project_id:
            raise HTTPException(status_code=400, detail="GCP Project ID not configured")
        
        manager = get_service_usage_manager()
        manager.enable_service(settings.gcp_project_id, "container.googleapis.com")
        return {"status": "ok", "message": "GKE API enablement initiated"}
    except Exception as e:
        logger.error(f"Error enabling GKE API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/init")
def init_project():
    try:
        if not settings.gcp_project_id:
            return {"status": "error", "message": "GCP Project ID not configured"}
            
        gke = get_gke_manager()
        ar = get_ar_manager()

        # 1. GKE Cluster
        exists = gke.check_cluster_exists(
            settings.gcp_project_id, 
            settings.region, 
            settings.cluster_name
        )
        if not exists:
            gke.create_autopilot_cluster(
                settings.gcp_project_id, 
                settings.region, 
                settings.cluster_name
            )
        
        # 2. Artifact Registry
        ar.ensure_repository(
            settings.gcp_project_id,
            settings.region,
            "workstation-images"
        )
        
        return {"status": "ok", "message": "Project initialization initiated"}
    except Exception as e:
        if "Kubernetes Engine API has not been used" in str(e) or "SERVICE_DISABLED" in str(e):
             raise HTTPException(status_code=403, detail="GKE API is disabled. Click 'Enable GKE API' to proceed.")
        logger.error(f"Error initializing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete-infrastructure")
def delete_infrastructure():
    try:
        if not settings.gcp_project_id:
            return {"status": "error", "message": "GCP Project ID not configured"}
            
        gke = get_gke_manager()
        gke.delete_cluster(
            settings.gcp_project_id, 
            settings.region, 
            settings.cluster_name
        )
        return {"status": "ok", "message": "Infrastructure deletion initiated"}
    except Exception as e:
        logger.error(f"Error deleting infrastructure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop-all")
def stop_all_workstations():
    try:
        manager = get_k8s_manager()
        scaled_namespaces = manager.scale_down_idle_workstations()
        return {"status": "ok", "message": f"Stop-all initiated. Scaled down workstations in {len(scaled_namespaces)} namespaces."}
    except Exception as e:
        logger.error(f"Error stopping all workstations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cluster-status")
def get_cluster_status():
    try:
        if not settings.gcp_project_id:
            return {"status": "UNKNOWN", "message": "GCP Project ID not configured"}
            
        gke = get_gke_manager()
        status = gke.get_cluster_status(
            settings.gcp_project_id, 
            settings.region, 
            settings.cluster_name
        )
        return {"status": status}
    except Exception as e:
        if "Kubernetes Engine API has not been used" in str(e) or "SERVICE_DISABLED" in str(e):
            return {"status": "ERROR", "message": "GKE API is disabled. Please enable it to proceed."}
        logger.error(f"Error getting cluster status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/images")
def list_available_images(user_ns: str = "user-1"):
    try:
        if not settings.gcp_project_id:
            return []
            
        # 1. Get physical images from Artifact Registry (Already filtered for tags)
        ar = get_ar_manager()
        physical_images = ar.list_images(
            settings.gcp_project_id,
            settings.region,
            "workstation-images"
        )
        
        # 2. Get saved configurations (Templates/Recipes) from ConfigMap
        k8s = get_k8s_manager()
        recipes = {}
        
        # Check 'image-dockerfiles' (raw source)
        try:
            sources_cm = k8s.core_api.read_namespaced_config_map(name="image-dockerfiles", namespace=user_ns)
            if sources_cm.data:
                for name in sources_cm.data.keys():
                    if name in recipes:
                        recipes[name]["has_dockerfile"] = True
                    else:
                        # Draft recipe with no build yet
                        recipes[name] = {
                            "uri": None,
                            "tags": [name],
                            "update_time": None,
                            "is_recipe": True,
                            "has_dockerfile": True
                        }
        except Exception: pass

        # 3. Merge and Enrich
        final_list = []
        seen_uris = set()

        def get_base_uri(uri):
            if not uri: return ""
            return uri.split('@')[0].split(':')[0]

        physical_by_base = {}
        for img in physical_images:
            base = get_base_uri(img["uri"])
            if base not in physical_by_base or (img.get("update_time") and physical_by_base[base].get("update_time") and img["update_time"] > physical_by_base[base]["update_time"]):
                physical_by_base[base] = img

        # Add all our intentional Recipes first
        for name, data in recipes.items():
            base_uri = get_base_uri(data["uri"])
            if base_uri in physical_by_base:
                match = physical_by_base[base_uri]
                data["update_time"] = match["update_time"]
                data["uri"] = match["uri"]
                seen_uris.add(base_uri)
            final_list.append(data)

        # Add any remaining physical images that aren't mapped to a recipe (orphan artifacts)
        for base, img in physical_by_base.items():
            if base not in seen_uris:
                repo_path = base.split('/')[-1]
                name = repo_path
                prefix = f"{user_ns}-"
                if name.startswith(prefix):
                    name = name[len(prefix):]
                
                final_list.append({
                    **img,
                    "tags": [name],
                    "is_recipe": False,
                    "has_dockerfile": False
                })
            
        return final_list
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        return []

@router.delete("/{user_ns}/images/{name}")
def delete_custom_image(user_ns: str, name: str):
    try:
        # 1. Delete from k8s config maps
        get_k8s_manager().delete_image_config(user_ns, name)
        
        # 2. Delete from Artifact Registry if project is configured
        if settings.gcp_project_id:
            ar = get_ar_manager()
            # The package name in artifact registry uses the user_ns-name format we built it with
            package_name = f"{user_ns}-{name}".lower().replace("_", "-")
            try:
                ar.delete_package(settings.gcp_project_id, settings.region, "workstation-images", package_name)
            except Exception as e:
                logger.error(f"Failed to delete package {package_name} from AR: {e}")
                # We don't fail the whole request if the AR image was already deleted or missing
                pass
                
        return {"status": "ok", "message": f"Image {name} deleted"}
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_ns}/images/{name}/dockerfile")
def get_image_dockerfile_endpoint(user_ns: str, name: str):
    try:
        dockerfile = get_k8s_manager().get_image_dockerfile(user_ns, name)
        if not dockerfile:
            raise HTTPException(status_code=404, detail="Dockerfile not found for this image")
        return {"dockerfile": dockerfile}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dockerfile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_ns}/save-config/{name}")
def save_workstation_config_endpoint(user_ns: str, name: str, req: SaveConfigRequest):
    try:
        get_k8s_manager().save_workstation_config(user_ns, name, req.image, req.ports)
        return {"status": "ok", "message": f"Config for {name} saved"}
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/{user_ns}/list", response_model=WorkstationListResponse)
def list_all_workstations(user_ns: str):
    res = get_k8s_manager().list_workstations(user_ns)
    workstations = []
    for w in res:
        config = get_k8s_manager().get_workstation_config(user_ns, w["name"])
        ports = config.get("ports", [3000]) if isinstance(config, dict) else [3000]
        workstations.append(
            WorkstationResponse(
                name=w["name"],
                user_ns=user_ns,
                status=WorkstationStatus(w["status"]),
                image=w.get("image"),
                ports=ports,
                pod_name=w.get("pod_name"),
                pod_ready=w.get("pod_ready", False),
                message=w.get("message")
            )
        )
    return WorkstationListResponse(workstations=workstations, count=len(workstations))
@router.post("/{user_ns}/start/{name}")
def start_named_workstation(user_ns: str, name: str):
    try:
        # 1. Ensure Namespace exists
        get_k8s_manager().ensure_namespace(user_ns)
        
        # 2. Ensure PVC exists
        pvc_name = f"{name}-pvc"
        get_k8s_manager().apply_pvc(user_ns, pvc_name)
        
        # 3. Check for custom image
        config = get_k8s_manager().get_workstation_config(user_ns, name)
        custom_image = config.get("image") if isinstance(config, dict) else config
        ports = config.get("ports", [3000]) if isinstance(config, dict) else [3000]
        final_image = custom_image if custom_image else settings.workstation_image

        # 4. Apply StatefulSet
        get_k8s_manager().apply_statefulset(
            user_ns,
            name,
            final_image,
            replicas=1,
            ports=ports
        )        
        return {"status": "ok", "message": f"Workstation {name} start initiated", "image": final_image}
    except Exception as e:
        logger.error(f"Error starting workstation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_ns}/build/{name}")
def build_named_workstation(user_ns: str, name: str, req: BuildRequest):
    try:
        if not settings.gcp_project_id:
            return {"status": "error", "message": "GCP Project ID not configured"}
            
        cb = get_cb_manager()
        # 1. Trigger Cloud Build
        image_tag, build_id = cb.build_custom_image(
            settings.gcp_project_id,
            settings.region,
            user_ns,
            name,
            req.dockerfile
        )
        
        # 2. Save custom image preference in K8s ConfigMap
        get_k8s_manager().save_workstation_config(user_ns, name, image_tag)
        
        # 3. Save the Dockerfile for this image
        get_k8s_manager().save_image_dockerfile(user_ns, name, req.dockerfile)
        
        return {
            "status": "ok", 
            "message": f"Build for {name} triggered", 
            "image": image_tag,
            "build_id": build_id
        }
    except Exception as e:
        logger.error(f"Error building workstation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_ns}/builds/{build_id}")
def get_build_status(user_ns: str, build_id: str):
    try:
        cb = get_cb_manager()
        status = cb.get_build_status(settings.gcp_project_id, build_id)
        return status
    except Exception as e:
        logger.error(f"Error getting build status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_ns}/stop/{name}")
def stop_named_workstation(user_ns: str, name: str):
    try:
        get_k8s_manager().scale_workstation(user_ns, name, 0)
        return {"status": "ok", "message": f"Workstation {name} stop initiated"}
    except Exception as e:
        logger.error(f"Error stopping workstation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_ns}/delete/{name}")
def delete_named_workstation(user_ns: str, name: str, delete_pvc: bool = True):
    try:
        get_k8s_manager().delete_workstation(user_ns, name, delete_pvc=delete_pvc)
        return {"status": "ok", "message": f"Workstation {name} and its storage deleted"}
    except Exception as e:
        logger.error(f"Error deleting workstation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_ns}/connect/{name}", response_class=PlainTextResponse)
def get_connect_script(user_ns: str, name: str, request: Request):
    try:
        cluster_name = settings.cluster_name
        project_id = settings.gcp_project_id
        region = settings.region
        
        config = get_k8s_manager().get_workstation_config(user_ns, name)
        ports = config.get("ports", [3000]) if isinstance(config, dict) else [3000]
        
        lsof_full = f"lsof " + " ".join([f"-ti:{p}" for p in ports]) + f" | xargs kill -9 2>/dev/null || true"
        
        pf_args = " ".join([f"{p}:{p}" for p in ports])

        script = f"""#!/bin/bash
# Magic Connect Script for Workstation Lite
set -e

echo "Configuring connection to your workstation {name}..."
gcloud config set project {project_id} --quiet
# We use ADC token to avoid kubectl plugin requirements
TOKEN=$(gcloud auth application-default print-access-token)
ENDPOINT=$(gcloud container clusters describe {cluster_name} --region {region} --format="value(endpoint)")

# Setup temp bin for kubectl if needed
TEMP_BIN_DIR="/tmp/workstation-bin"
mkdir -p $TEMP_BIN_DIR
export PATH="$TEMP_BIN_DIR:$PATH"

if ! command -v kubectl &> /dev/null; then
    echo "kubectl not found, downloading standalone binary..."
    curl -s -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    mv kubectl $TEMP_BIN_DIR/
fi

echo "Starting port-forwarding ({','.join(map(str, ports))}) and launching terminal..."
# Kill any existing port-forward to {','.join(map(str, ports))}
{lsof_full}

# Start port-forward in background using token-based auth to bypass plugin
kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify port-forward pod/{name}-0 {pf_args} -n {user_ns} > /dev/null 2>&1 &
PF_PID=$!

# Trap exit to kill port-forward
trap "kill $PF_PID" EXIT

# Wait for port-forward
sleep 2

echo "Connecting to shell..."
# Try ZSH first (custom image), fallback to BASH
if kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec pod/{name}-0 -n {user_ns} -- which zsh &>/dev/null; then
    SHELL_BIN="/bin/zsh"
else
    SHELL_BIN="/bin/bash"
fi

kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec -it pod/{name}-0 -n {user_ns} -- $SHELL_BIN < /dev/tty
"""
        return script
    except Exception as e:
        logger.error(f"Error generating connect script: {e}")
        return f"echo 'Error generating connect script: {str(e)}'\n"

@router.get("/{user_ns}/status/{name}", response_model=WorkstationResponse)
def get_workstation_status(user_ns: str, name: str):
    res = get_k8s_manager().get_workstation_status(user_ns, name)
    return WorkstationResponse(
        name=name,
        user_ns=user_ns, 
        status=WorkstationStatus(res["status"]),
        pod_name=res["pod_name"],
        pod_ready=res["pod_ready"],
        image=res.get("image")
    )
