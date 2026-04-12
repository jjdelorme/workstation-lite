from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.services.gke import GKEManager
from app.services.artifact_registry import ArtifactRegistryManager
from app.services.cloud_build import CloudBuildManager
from app.services.compute import ComputeManager
from app.services.service_usage import ServiceUsageManager
from app.models.workstation import WorkstationResponse, WorkstationListResponse, WorkstationStatus, BuildRequest, SaveConfigRequest
from pydantic import BaseModel
from app.core.config import settings
import google.auth
import logging
import time
import subprocess
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workstations", tags=["workstations"])

# Global singletons (instantiated on first use)
_gke_manager = None
_ar_manager = None
_cb_manager = None
_compute_manager = None
_service_usage_manager = None
_k8s_manager = None

@router.get("/templates/default", response_class=PlainTextResponse)
def get_default_template():
    try:
        # Current file is at backend/app/api/workstations.py
        # root is 3 levels up: api/ -> app/ -> backend/ -> root/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        template_path = os.path.join(root_dir, "templates", "Dockerfile.template")
        
        if os.path.exists(template_path):
            with open(template_path, "r") as f:
                return f.read()
        else:
            logger.warning(f"Default template not found at {template_path}")
            # Fallback to a basic template if file is missing
            return "FROM gitpod/openvscode-server:latest\n"
    except Exception as e:
        logger.error(f"Error reading default template: {e}")
        return f"Error: {str(e)}"

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
            
        # 1. Get physical images from Artifact Registry
        ar = get_ar_manager()
        physical_images = ar.list_images(
            settings.gcp_project_id,
            settings.region,
            "workstation-images"
        )
        
        # Helper to get the base URI (without tags/shas)
        def get_base_uri(uri):
            if not uri: return ""
            return uri.split('@')[0].split(':')[0]

        # Map physical images by their base URI for quick lookup
        physical_by_base = {}
        for img in physical_images:
            base = get_base_uri(img["uri"])
            # Keep the newest version if multiple exist
            if base not in physical_by_base or (img.get("update_time") and physical_by_base[base].get("update_time") and img["update_time"] > physical_by_base[base]["update_time"]):
                physical_by_base[base] = img

        # 2. Get saved configurations (Templates/Recipes) from ConfigMap
        k8s = get_k8s_manager()
        recipe_names = []

        try:
            sources_cm = k8s.core_api.read_namespaced_config_map(name="image-dockerfiles", namespace=user_ns)
            if sources_cm.data:
                recipe_names = list(sources_cm.data.keys())
        except Exception:
            pass

        # 2b. Get stored build IDs and check their status
        build_ids = k8s.get_image_build_ids(user_ns)
        build_statuses = {}
        if build_ids and settings.gcp_project_id:
            cb = get_cb_manager()
            for img_name, bid in build_ids.items():
                try:
                    status_info = cb.get_build_status(settings.gcp_project_id, bid)
                    build_statuses[img_name] = status_info
                except Exception as e:
                    logger.warning(f"Failed to check build status for {img_name} (build {bid}): {e}")

        # 3. Merge and Enrich
        final_list = []
        seen_uris = set()
        
        # Base path for this project's images in AR
        ar_repo_base = f"{settings.region}-docker.pkg.dev/{settings.gcp_project_id}/workstation-images"

        # Add all our intentional Recipes first
        for name in recipe_names:
            # Calculate what the URI SHOULD be if it were built
            expected_name = f"{user_ns}-{name}".lower().replace("_", "-")
            expected_base_uri = f"{ar_repo_base}/{expected_name}"
            
            recipe_data = {
                "uri": None,
                "tags": [name],
                "update_time": None,
                "is_recipe": True,
                "has_dockerfile": True,
                "build_id": None,
                "build_status": None,
                "build_log_url": None,
            }

            # Check if we have a matching physical image in the registry
            if expected_base_uri in physical_by_base:
                match = physical_by_base[expected_base_uri]
                recipe_data["uri"] = match["uri"]
                recipe_data["update_time"] = match["update_time"]
                seen_uris.add(expected_base_uri)

            # Attach build status if available
            if name in build_statuses:
                bs = build_statuses[name]
                recipe_data["build_id"] = bs.get("id")
                recipe_data["build_status"] = bs.get("status")
                recipe_data["build_log_url"] = bs.get("log_url")

            final_list.append(recipe_data)

        # 4. Add any remaining physical images that aren't mapped to a recipe (orphan artifacts)
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
        current_config = get_k8s_manager().get_workstation_config(user_ns, name)
        image = req.image if req.image else current_config.get("image")
        ports = req.ports if req.ports is not None else current_config.get("ports", [])
        cpu = req.cpu if req.cpu is not None else current_config.get("cpu", "2000m")
        memory = req.memory if req.memory is not None else current_config.get("memory", "8Gi")
        disk_size = req.disk_size if req.disk_size is not None else current_config.get("disk_size", "10Gi")
        gpu = req.gpu if req.gpu is not None else current_config.get("gpu")
        use_spot = req.use_spot if req.use_spot is not None else current_config.get("use_spot", False)
        env_vars = req.env_vars if req.env_vars is not None else current_config.get("env_vars", {})
        run_as_root = req.run_as_root if req.run_as_root is not None else current_config.get("run_as_root", False)
        get_k8s_manager().save_workstation_config(user_ns, name, image, ports, cpu, memory, disk_size, gpu, use_spot, env_vars, run_as_root)
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
        ports = config.get("ports", []) if isinstance(config, dict) else []
        workstations.append(
            WorkstationResponse(
                name=w["name"],
                user_ns=user_ns,
                status=WorkstationStatus(w["status"]),
                image=w.get("image"),
                ports=ports,
                cpu=config.get("cpu", "2000m"),
                memory=config.get("memory", "8Gi"),
                disk_size=config.get("disk_size", "10Gi"),
                gpu=config.get("gpu"),
                use_spot=config.get("use_spot", False),
                run_as_root=config.get("run_as_root", False),
                env_vars=config.get("env_vars", {}),
                pod_name=w.get("pod_name"),
                pod_ready=w.get("pod_ready", False),
                message=w.get("message"),
                restart_count=w.get("restart_count", 0),
                last_restart_time=w.get("last_restart_time"),
                last_restart_reason=w.get("last_restart_reason")
            )
        )
    return WorkstationListResponse(workstations=workstations, count=len(workstations))
@router.post("/{user_ns}/start/{name}")
def start_named_workstation(user_ns: str, name: str):
    try:
        # 1. Ensure Namespace exists
        get_k8s_manager().ensure_namespace(user_ns)

        # 2. Read workstation config
        config = get_k8s_manager().get_workstation_config(user_ns, name)
        custom_image = config.get("image") if isinstance(config, dict) else config
        ports = config.get("ports", []) if isinstance(config, dict) else []
        cpu = config.get("cpu", "2000m")
        memory = config.get("memory", "8Gi")
        disk_size = config.get("disk_size", "10Gi")
        gpu = config.get("gpu")
        use_spot = config.get("use_spot", False)
        user_env_vars = config.get("env_vars", {}) if isinstance(config, dict) else {}
        run_as_root = config.get("run_as_root", False)
        final_image = custom_image if custom_image else settings.workstation_image

        # 3. Ensure PVC exists
        pvc_name = f"{name}-pvc"
        get_k8s_manager().apply_pvc(user_ns, pvc_name, size=disk_size)

        # 4. Apply StatefulSet
        get_k8s_manager().apply_statefulset(
            user_ns,
            name,
            final_image,
            replicas=1,
            ports=ports,
            cpu=cpu,
            memory=memory,
            gpu=gpu,
            use_spot=use_spot,
            env_vars=user_env_vars,
            run_as_root=run_as_root,
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

        # 4. Save build_id so we can track status across page navigations
        get_k8s_manager().save_image_build_id(user_ns, name, build_id)

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
        ports = config.get("ports", []) if isinstance(config, dict) else []
        run_as_root = config.get("run_as_root", False) if isinstance(config, dict) else False
        user_env_vars = config.get("env_vars", {}) if isinstance(config, dict) else {}
        # Build whitelist of env vars to preserve through su -l (which resets env)
        whitelist_vars = ["GOOGLE_CLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS", "CLAUDE_CODE_USE_VERTEX"] + list(user_env_vars.keys())
        whitelist_str = ",".join(whitelist_vars)

        if ports:
            lsof_full = "lsof " + " ".join([f"-ti:{p}" for p in ports]) + " | xargs kill -9 2>/dev/null || true"
            pf_args = " ".join([f"{p}:{p}" for p in ports])
            port_forward_block = f"""
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
"""
        else:
            port_forward_block = ""

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
{port_forward_block}
echo "Connecting to shell..."
# Try ZSH first (custom image), fallback to BASH
if kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec pod/{name}-0 -n {user_ns} -- which zsh &>/dev/null; then
    SHELL_BIN="/bin/zsh"
else
    SHELL_BIN="/bin/bash"
fi

if [ "{run_as_root}" = "True" ]; then
    kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec -it pod/{name}-0 -n {user_ns} -- $SHELL_BIN < /dev/tty
else
    kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec -it pod/{name}-0 -n {user_ns} -- su -l abc -w {whitelist_str} -s $SHELL_BIN < /dev/tty
fi
"""
        return script
    except Exception as e:
        logger.error(f"Error generating connect script: {e}")
        return f"echo 'Error generating connect script: {str(e)}'\n"

@router.post("/{user_ns}/snapshot")
def snapshot_workstation(user_ns: str):
    try:
        k8s = get_k8s_manager()
        compute = get_compute_manager()
        
        # We assume the workstation name is "workstation" for this simplified endpoint
        name = "workstation"
        
        volume_handle = k8s.get_pvc_volume_handle(user_ns, f"{name}-pvc")
        if not volume_handle:
            raise HTTPException(status_code=404, detail="Volume handle not found")
        
        # handle format: projects/{project}/zones/{zone}/disks/{disk_name}
        parts = volume_handle.split('/')
        if len(parts) < 6:
            raise HTTPException(status_code=500, detail=f"Invalid volume handle format: {volume_handle}")
        project = parts[1]
        zone = parts[3]
        disk_name = parts[5]
        
        snapshot_name = f"snap-{name}-{int(time.time())}"
        compute.create_disk_snapshot(project, zone, disk_name, snapshot_name)
        
        return {"status": "ok", "snapshot_name": snapshot_name}
    except Exception as e:
        logger.error(f"Error creating snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_ns}/status/{name}", response_model=WorkstationResponse)
def get_workstation_status(user_ns: str, name: str):
    res = get_k8s_manager().get_workstation_status(user_ns, name)
    config = get_k8s_manager().get_workstation_config(user_ns, name)
    return WorkstationResponse(
        name=name,
        user_ns=user_ns,
        status=WorkstationStatus(res["status"]),
        pod_name=res["pod_name"],
        pod_ready=res["pod_ready"],
        image=res.get("image"),
        run_as_root=config.get("run_as_root", False),
        message=res.get("message"),
        restart_count=res.get("restart_count", 0),
        last_restart_time=res.get("last_restart_time"),
        last_restart_reason=res.get("last_restart_reason")
    )

@router.get("/nodes")
def list_cluster_nodes():
    try:
        nodes = get_k8s_manager().list_nodes()
        return {"nodes": nodes}
    except Exception as e:
        logger.error(f"Error listing nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class AdcSecretRequest(BaseModel):
    adc_json: str

@router.get("/{user_ns}/adc-secret")
def check_adc_secret(user_ns: str):
    exists = get_k8s_manager().check_adc_secret(user_ns)
    return {"exists": exists}

@router.post("/{user_ns}/adc-secret")
def save_adc_secret(user_ns: str, req: AdcSecretRequest):
    try:
        get_k8s_manager().ensure_namespace(user_ns)
        get_k8s_manager().save_adc_secret(user_ns, req.adc_json)
        return {"status": "ok", "message": "ADC credentials saved"}
    except Exception as e:
        logger.error(f"Error saving ADC secret: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SshKeyRequest(BaseModel):
    ssh_key: str

@router.get("/{user_ns}/ssh-key")
def check_ssh_key(user_ns: str):
    exists = get_k8s_manager().check_ssh_key(user_ns)
    return {"exists": exists}

@router.post("/{user_ns}/ssh-key")
def save_ssh_key(user_ns: str, req: SshKeyRequest):
    try:
        get_k8s_manager().ensure_namespace(user_ns)
        get_k8s_manager().save_ssh_key(user_ns, req.ssh_key)
        return {"status": "ok", "message": "SSH key saved"}
    except Exception as e:
        logger.error(f"Error saving SSH key: {e}")
        raise HTTPException(status_code=500, detail=str(e))
