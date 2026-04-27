from kubernetes import client
import base64
import logging
import tempfile
from typing import Optional
import google.auth
import google.auth.transport.requests
from google.cloud import container_v1
from app.core.config import settings

logger = logging.getLogger(__name__)

class K8sManager:
    def __init__(self):
        self.api_client = None
        self.core_api = None
        self.apps_api = None
        self._is_ready = False
        self._last_refresh_time = 0
        self._credentials = None
        self._refresh_config()

    def _get_gcp_credentials(self):
        """Get and cache GCP credentials via google.auth.default()."""
        if self._credentials is None:
            self._credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        self._credentials.refresh(google.auth.transport.requests.Request())
        return self._credentials

    def _get_gcp_token(self) -> str:
        """Get a fresh access token via ADC."""
        return self._get_gcp_credentials().token

    def _refresh_config(self):
        import time
        current_time = time.time()

        # Refresh if not ready, or if it's been more than 30 minutes (1800 seconds)
        if self._is_ready and (current_time - self._last_refresh_time < 1800):
            return

        self._last_refresh_time = current_time

        # Connect to GKE using ADC + GKE API (no kubeconfig/kubectl dependency)
        try:
            logger.info("Connecting to GKE via ADC and GKE API...")
            project_id = settings.gcp_project_id
            region = settings.region
            cluster_name = settings.cluster_name

            if not project_id:
                logger.error("GCP project ID not configured, cannot connect to GKE")
                return

            # Use GKE API to get cluster endpoint and CA cert
            gke_client = container_v1.ClusterManagerClient()
            cluster_path = f"projects/{project_id}/locations/{region}/clusters/{cluster_name}"
            cluster = gke_client.get_cluster(request={"name": cluster_path})

            # Build K8s client configuration using ADC token
            token = self._get_gcp_token()

            configuration = client.Configuration()
            configuration.host = f"https://{cluster.endpoint}"
            configuration.api_key['authorization'] = f"Bearer {token}"

            # Set up CA cert
            ca_cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
            ca_cert_file.write(base64.b64decode(cluster.master_auth.cluster_ca_certificate))
            ca_cert_file.close()
            configuration.ssl_ca_cert = ca_cert_file.name

            self.api_client = client.ApiClient(configuration)
            self.core_api = client.CoreV1Api(self.api_client)
            self.apps_api = client.AppsV1Api(self.api_client)
            self._is_ready = True
            logger.info(f"Connected to GKE cluster {cluster_name} via ADC")
        except Exception as e:
            logger.error(f"Failed to connect to GKE via ADC: {e}")
            self._is_ready = False

    def ensure_namespace(self, user_ns: str):
        self._refresh_config()
        if not self.core_api: return
        try:
            self.core_api.read_namespace(name=user_ns)
        except Exception:
            try:
                ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=user_ns))
                self.core_api.create_namespace(body=ns)
            except Exception as e:
                logger.error(f"Failed to create namespace {user_ns}: {e}")
        
        # Always try to ensure the image pull secret exists
        try:
            token = self._get_gcp_token()
            import base64
            import json
            auth_config = {
                "auths": {
                    "us-central1-docker.pkg.dev": {
                        "auth": base64.b64encode(f"_token:{token}".encode()).decode()
                    }
                }
            }
            docker_config_json = base64.b64encode(json.dumps(auth_config).encode()).decode()
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(name="artifact-registry-key"),
                type="kubernetes.io/dockerconfigjson",
                data={".dockerconfigjson": docker_config_json}
            )
            try:
                self.core_api.read_namespaced_secret(name="artifact-registry-key", namespace=user_ns)
                self.core_api.replace_namespaced_secret(name="artifact-registry-key", namespace=user_ns, body=secret)
            except Exception:
                self.core_api.create_namespaced_secret(namespace=user_ns, body=secret)
        except Exception as e:
            logger.error(f"Failed to ensure image pull secret in {user_ns}: {e}")

    def apply_pvc(self, user_ns: str, name: str, size: str = "10Gi"):
        self._refresh_config()
        if not self.core_api: return
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(requests={"storage": size}),
                storage_class_name="standard-rwo"
            )
        )
        try:
            self.core_api.read_namespaced_persistent_volume_claim(name=name, namespace=user_ns)
            logger.info(f"PVC {name} already exists in {user_ns}")
        except Exception:
            try:
                self.core_api.create_namespaced_persistent_volume_claim(namespace=user_ns, body=pvc)
            except Exception as e:
                logger.error(f"Failed to create PVC {name} in {user_ns}: {e}")

    def apply_statefulset(self, user_ns: str, name: str, image: str, replicas: int, ports: list[int] = None,
                          cpu: str = "2000m", memory: str = "8Gi", gpu: str = None, use_spot: bool = False,
                          env_vars: dict = None, run_as_root: bool = False):
        if ports is None:
            ports = []
        self._refresh_config()
        if not self.apps_api: return

        container_ports = [client.V1ContainerPort(container_port=p) for p in ports]

        # Resource requests
        resource_requests = {"cpu": cpu, "memory": memory, "ephemeral-storage": "10Gi"}
        resource_limits = {"ephemeral-storage": "10Gi"}

        # GPU and Spot support
        node_selector = {}
        tolerations = []
        
        if gpu:
            resource_limits["nvidia.com/gpu"] = "1"
            # GKE Autopilot Accelerator class requirements
            node_selector["cloud.google.com/compute-class"] = "Accelerator"
            node_selector["cloud.google.com/gke-accelerator"] = gpu or "nvidia-l4"
            tolerations.append(
                client.V1Toleration(
                    key="nvidia.com/gpu",
                    operator="Exists",
                    effect="NoSchedule"
                )
            )
        
        if use_spot:
            node_selector["cloud.google.com/gke-spot"] = "true"

        if not node_selector:
            node_selector = None
        if not tolerations:
            tolerations = None

        # Volume mounts and volumes
        volume_mounts = [
            client.V1VolumeMount(name="home", mount_path="/home/workspace"),
            client.V1VolumeMount(name="gcp-adc", mount_path="/var/secrets/google", read_only=True),
        ]
        volumes = [
            client.V1Volume(
                name="home",
                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=f"{name}-pvc")
            ),
            client.V1Volume(
                name="gcp-adc",
                secret=client.V1SecretVolumeSource(
                    secret_name="gcp-adc-credentials",
                    optional=True
                )
            ),
            client.V1Volume(
                name="ssh-key",
                secret=client.V1SecretVolumeSource(
                    secret_name="ssh-key-secret",
                    default_mode=0o600,
                    optional=True
                )
            ),
        ]

        # Environment variables for GCP credentials
        from app.core.config import settings
        uid = "0" if run_as_root else "1000"
        gid = "0" if run_as_root else "1000"

        # Robust provisioning step:
        # 1. Ensure home directory ownership (essential for GKE PVCs)
        # 2. Prepare .ssh directory with 700 permissions
        # 3. Copy id_rsa from Secret mount with 600 permissions and correct ownership
        # 4. CRITICAL: Ensure trailing newline exists (OpenSSH is picky)
        init_command = f"chown {uid}:{gid} /home/workspace"
        init_command += f" && mkdir -p /home/workspace/.ssh && chmod 700 /home/workspace/.ssh"
        init_command += f" && if [ -f /tmp/ssh-secret/id_rsa ]; then cp /tmp/ssh-secret/id_rsa /home/workspace/.ssh/id_rsa; fi"
        init_command += f" && if [ -f /home/workspace/.ssh/id_rsa ]; then [ -n \"$(tail -c1 /home/workspace/.ssh/id_rsa)\" ] && echo >> /home/workspace/.ssh/id_rsa; fi"
        init_command += f" && if [ -f /home/workspace/.ssh/id_rsa ]; then chmod 600 /home/workspace/.ssh/id_rsa && chown {uid}:{gid} /home/workspace/.ssh/id_rsa; fi"
        init_command += f" && chown -R {uid}:{gid} /home/workspace/.ssh"

        env_list = [
            client.V1EnvVar(name="PUID", value=uid),
            client.V1EnvVar(name="PGID", value=gid),
            client.V1EnvVar(name="GOOGLE_APPLICATION_CREDENTIALS", value="/var/secrets/google/adc.json"),
            client.V1EnvVar(name="GOOGLE_CLOUD_PROJECT", value=settings.gcp_project_id or ""),
        ]

        # Append user-defined environment variables
        if env_vars:
            for k, v in env_vars.items():
                env_list.append(client.V1EnvVar(name=k, value=v))

        # Pod and Container security context
        pod_sc = client.V1PodSecurityContext(fs_group=int(gid))
        container_sc = None
        if run_as_root:
            container_sc = client.V1SecurityContext(run_as_user=0, run_as_group=0)

        sts = client.V1StatefulSet(
            metadata=client.V1ObjectMeta(
                name=name,
                labels={
                    "app": name,
                    "managed-by": "workstation-lite"
                }
            ),
            spec=client.V1StatefulSetSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels={"app": name}),
                service_name=name,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": name}),
                    spec=client.V1PodSpec(
                        security_context=pod_sc,
                        image_pull_secrets=[client.V1LocalObjectReference(name="artifact-registry-key")],
                        node_selector=node_selector,
                        tolerations=tolerations,
                        init_containers=[
                            client.V1Container(
                                name="fix-permissions",
                                image="busybox",
                                command=["sh", "-c", init_command],
                                security_context=client.V1SecurityContext(
                                    run_as_user=0
                                ),
                                resources=client.V1ResourceRequirements(
                                    requests={"ephemeral-storage": "10Gi"},
                                    limits={"ephemeral-storage": "10Gi"}
                                ),
                                volume_mounts=[
                                    client.V1VolumeMount(name="home", mount_path="/home/workspace"),
                                    client.V1VolumeMount(name="ssh-key", mount_path="/tmp/ssh-secret", read_only=True),
                                ]
                            )
                        ],
                        containers=[
                            client.V1Container(
                                name=name,
                                image=image,
                                ports=container_ports,
                                env=env_list,
                                security_context=container_sc,
                                resources=client.V1ResourceRequirements(
                                    requests=resource_requests,
                                    limits=resource_limits if resource_limits else None
                                ),
                                volume_mounts=volume_mounts
                            )
                        ],
                        volumes=volumes
                    )
                )
            )
        )
        try:
            self.apps_api.read_namespaced_stateful_set(name=name, namespace=user_ns)
            # Use replace instead of patch if patch isn't working as expected
            self.apps_api.replace_namespaced_stateful_set(name=name, namespace=user_ns, body=sts)
        except Exception:
            try:
                self.apps_api.create_namespaced_stateful_set(namespace=user_ns, body=sts)
            except Exception as e:
                logger.error(f"Failed to create StatefulSet {name} in {user_ns}: {e}")

    def scale_workstation(self, user_ns: str, name: str, replicas: int):
        self._refresh_config()
        if not self.apps_api: return
        body = client.V1Scale(
            spec=client.V1ScaleSpec(replicas=replicas)
        )
        try:
            self.apps_api.patch_namespaced_stateful_set_scale(name=name, namespace=user_ns, body=body)
        except Exception as e:
            logger.error(f"Failed to scale {name} in {user_ns}: {e}")
    def get_workstation_status(self, user_ns: str, name: str) -> dict:
        self._refresh_config()
        if not self.apps_api or not self.core_api: 
            return {"status": "UNKNOWN", "pod_name": None, "pod_ready": False}
        try:
            sts = self.apps_api.read_namespaced_stateful_set(name=name, namespace=user_ns)
            
            status = "UNKNOWN"
            pod_ready = False
            pod_name = f"{name}-0"
            error_message = None
            restart_count = 0
            last_restart_time = None
            last_restart_reason = None

            # Check for Pod specific status to detect errors early
            try:
                pod = self.core_api.read_namespaced_pod(name=pod_name, namespace=user_ns)
                if pod.status.container_statuses:
                    container_status = pod.status.container_statuses[0]
                    state = container_status.state

                    restart_count = container_status.restart_count or 0
                    if container_status.last_state and container_status.last_state.terminated:
                        last_term = container_status.last_state.terminated
                        if last_term.finished_at:
                            last_restart_time = last_term.finished_at.isoformat()
                        last_restart_reason = last_term.reason

                    if state.waiting:
                        reason = state.waiting.reason
                        if reason in ["ImagePullBackOff", "ErrImagePull", "CrashLoopBackOff", "CreateContainerConfigError"]:
                            status = "ERROR"
                            error_message = f"Pod Error: {reason} - {state.waiting.message or 'Check logs'}"
                    elif state.terminated:
                        if state.terminated.exit_code != 0:
                            status = "ERROR"
                            error_message = f"Pod Terminated with exit code {state.terminated.exit_code}: {state.terminated.reason}"
            except Exception:
                pass # Pod might not be created yet if STS just started

            # Fetch recent cluster events for the pod (e.g. Evicted, Preempting)
            try:
                events = self.core_api.list_namespaced_event(namespace=user_ns, field_selector=f"involvedObject.name={pod_name}")
                recent_warnings = []
                for e in events.items:
                    if e.type == "Warning" or e.reason in ["Evicted", "Preempting", "Failed", "NodeNotReady"]:
                        recent_warnings.append(e)
                if recent_warnings:
                    recent_warnings.sort(key=lambda x: x.last_timestamp or x.event_time or x.metadata.creation_timestamp, reverse=True)
                    latest_event = recent_warnings[0]
                    event_ts = latest_event.last_timestamp or latest_event.event_time or latest_event.metadata.creation_timestamp
                    if event_ts:
                        event_time_str = event_ts.isoformat()
                        if not last_restart_time or event_time_str > last_restart_time:
                            last_restart_time = event_time_str
                            last_restart_reason = f"Cluster Event ({latest_event.reason}): {latest_event.message}"
                            if restart_count == 0:
                                restart_count = 1
            except Exception as ev_err:
                logger.error(f"Error fetching events for {pod_name}: {ev_err}")

            if status != "ERROR":
                if sts.status.ready_replicas and sts.status.ready_replicas > 0:
                    status = "RUNNING"
                    pod_ready = True
                elif sts.spec.replicas == 0:
                    status = "STOPPED"
                else:
                    status = "PROVISIONING"

            return {
                "status": status,
                "pod_name": pod_name,
                "pod_ready": pod_ready,
                "message": error_message,
                "restart_count": restart_count,
                "last_restart_time": last_restart_time,
                "last_restart_reason": last_restart_reason
            }
        except Exception as e:
            if hasattr(e, 'status') and e.status == 404:
                return {"status": "STOPPED", "pod_name": None, "pod_ready": False}
            if "404" in str(e):
                return {"status": "STOPPED", "pod_name": None, "pod_ready": False}
            logger.error(f"Error getting workstation status for {user_ns}/{name}: {e}")
            return {"status": "UNKNOWN", "pod_name": None, "pod_ready": False}


    def list_workstations(self, user_ns: str) -> list[dict]:
        self._refresh_config()
        if not self.apps_api: return []
        try:
            # 1. Get existing StatefulSets - These are our ACTUAL instances
            stss = self.apps_api.list_namespaced_stateful_set(
                namespace=user_ns,
                label_selector="managed-by=workstation-lite"
            )
            workstations = []
            for sts in stss.items:
                # Skip service pods — they show on the Services tab
                labels = sts.metadata.labels or {}
                if labels.get("resource-type") == "service":
                    continue
                name = sts.metadata.name
                status_info = self.get_workstation_status(user_ns, name)
                status_info["name"] = name
                try:
                    status_info["image"] = sts.spec.template.spec.containers[0].image
                except (IndexError, AttributeError):
                    status_info["image"] = "unknown"
                workstations.append(status_info)

            # We DO NOT merge with ConfigMap here. 
            # Workstations tab = Live Instances. 
            # Images tab = ConfigMap Recipes.
            return workstations
        except Exception as e:
            logger.error(f"Error listing workstations in {user_ns}: {e}")
            return []

    def save_image_dockerfile(self, user_ns: str, image_name: str, dockerfile: str):
        self._refresh_config()
        if not self.core_api: return
        cm_name = "image-dockerfiles"
        try:
            try:
                cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
                if not cm.data: cm.data = {}
                cm.data[image_name] = dockerfile
                self.core_api.patch_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
            except Exception:
                cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name=cm_name),
                    data={image_name: dockerfile}
                )
                self.core_api.create_namespaced_config_map(namespace=user_ns, body=cm)
        except Exception as e:
            logger.error(f"Failed to save dockerfile for {image_name} in {user_ns}: {e}")

    def save_image_build_id(self, user_ns: str, image_name: str, build_id: str):
        self._refresh_config()
        if not self.core_api: return
        cm_name = "image-builds"
        try:
            try:
                cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
                if not cm.data: cm.data = {}
                cm.data[image_name] = build_id
                self.core_api.patch_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
            except Exception:
                cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name=cm_name),
                    data={image_name: build_id}
                )
                self.core_api.create_namespaced_config_map(namespace=user_ns, body=cm)
        except Exception as e:
            logger.error(f"Failed to save build_id for {image_name} in {user_ns}: {e}")

    def get_image_build_ids(self, user_ns: str) -> dict:
        self._refresh_config()
        if not self.core_api: return {}
        cm_name = "image-builds"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            return dict(cm.data) if cm.data else {}
        except Exception:
            return {}

    def delete_image_build_id(self, user_ns: str, image_name: str):
        self._refresh_config()
        if not self.core_api: return
        cm_name = "image-builds"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            if cm.data and image_name in cm.data:
                del cm.data[image_name]
                if not cm.data: cm.data = {}
                self.core_api.replace_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
        except Exception as e:
            logger.info(f"Could not delete build_id for {image_name}: {e}")

    def delete_image_config(self, user_ns: str, image_name: str):
        self._refresh_config()
        if not self.core_api: return

        # Remove from image-dockerfiles
        try:
            cm_name = "image-dockerfiles"
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            if cm.data and image_name in cm.data:
                del cm.data[image_name]
                if not cm.data: cm.data = {}
                self.core_api.replace_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
        except Exception as e:
            logger.info(f"Could not delete {image_name} from image-dockerfiles: {e}")

        # Remove from image-builds
        self.delete_image_build_id(user_ns, image_name)
    def get_image_dockerfile(self, user_ns: str, image_name: str) -> Optional[str]:
        self._refresh_config()
        if not self.core_api: return None
        cm_name = "image-dockerfiles"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            return cm.data.get(image_name)
        except Exception:
            return None

    def delete_workstation(self, user_ns: str, name: str, delete_pvc: bool = False):
        self._refresh_config()
        if not self.apps_api or not self.core_api: return
        
        # 1. Delete StatefulSet
        try:
            self.apps_api.delete_namespaced_stateful_set(name=name, namespace=user_ns)
            logger.info(f"Deleted StatefulSet {name} in {user_ns}")
        except Exception as e:
            if not (hasattr(e, 'status') and e.status == 404):
                logger.error(f"Failed to delete StatefulSet {name} in {user_ns}: {e}")

        # 2. Optionally delete PVC
        if delete_pvc:
            pvc_name = f"{name}-pvc"
            try:
                self.core_api.delete_namespaced_persistent_volume_claim(name=pvc_name, namespace=user_ns)
                logger.info(f"Deleted PVC {pvc_name} in {user_ns}")
            except Exception as e:
                if not (hasattr(e, 'status') and e.status == 404):
                    logger.error(f"Failed to delete PVC {pvc_name} in {user_ns}: {e}")

        # 3. Remove from config - This ensures it doesn't show up in the "Instances" list as STOPPED
        self.delete_workstation_config(user_ns, name)

    def delete_workstation_config(self, user_ns: str, workstation_name: str):
        self._refresh_config()
        if not self.core_api: return
        cm_name = "workstation-configs"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            if cm.data and workstation_name in cm.data:
                del cm.data[workstation_name]
                if not cm.data: cm.data = {}
                self.core_api.replace_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
                logger.info(f"Removed config for {workstation_name} in {user_ns}")
        except Exception as e:
            if not (hasattr(e, 'status') and e.status == 404):
                logger.error(f"Failed to delete config for {workstation_name} in {user_ns}: {e}")

    def save_workstation_config(self, user_ns: str, workstation_name: str, image: str, ports: list[int] = None,
                                cpu: str = "2000m", memory: str = "8Gi", disk_size: str = "10Gi", gpu: str = None,
                                use_spot: bool = False, env_vars: dict = None, run_as_root: bool = False):
        if ports is None:
            ports = []
        self._refresh_config()
        if not self.core_api: return
        import json
        cm_name = "workstation-configs"
        config_data = json.dumps({
            "image": image, 
            "ports": ports, 
            "cpu": cpu, 
            "memory": memory, 
            "disk_size": disk_size, 
            "gpu": gpu, 
            "use_spot": use_spot,
            "env_vars": env_vars or {},
            "run_as_root": run_as_root
        })
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            if not cm.data: cm.data = {}
            cm.data[workstation_name] = config_data
            self.core_api.patch_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
        except Exception:
            cm = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=cm_name),
                data={workstation_name: config_data}
            )
            try:
                self.core_api.create_namespaced_config_map(namespace=user_ns, body=cm)
            except Exception as e:
                logger.error(f"Failed to save config in {user_ns}: {e}")

    def get_workstation_config(self, user_ns: str, workstation_name: str) -> dict:
        self._refresh_config()
        default_config = {"image": None, "ports": [], "cpu": "2000m", "memory": "8Gi", "disk_size": "10Gi", "gpu": None, "use_spot": False, "env_vars": {}, "run_as_root": False}
        if not self.core_api: return default_config
        cm_name = "workstation-configs"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            val = cm.data.get(workstation_name)
            if not val:
                return default_config
            import json
            try:
                parsed = json.loads(val)
                return {
                    "image": parsed.get("image"),
                    "ports": parsed.get("ports", []),
                    "cpu": parsed.get("cpu", "2000m"),
                    "memory": parsed.get("memory", "8Gi"),
                    "disk_size": parsed.get("disk_size", "10Gi"),
                    "gpu": parsed.get("gpu"),
                    "use_spot": parsed.get("use_spot", False),
                    "env_vars": parsed.get("env_vars", {}),
                    "run_as_root": parsed.get("run_as_root", False),
                }
            except json.JSONDecodeError:
                # Backwards compatibility for old config format
                return {"image": val, "ports": [], "cpu": "2000m", "memory": "8Gi", "disk_size": "10Gi", "gpu": None, "use_spot": False, "env_vars": {}, "run_as_root": False}
        except Exception:
            return default_config

    def get_pvc_volume_handle(self, user_ns: str, pvc_name: str) -> Optional[str]:
        self._refresh_config()
        if not self.core_api: return None
        try:
            pvc = self.core_api.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=user_ns)
            pv_name = pvc.spec.volume_name
            if not pv_name:
                return None
            pv = self.core_api.read_persistent_volume(name=pv_name)
            return pv.spec.csi.volume_handle
        except Exception as e:
            logger.error(f"Error getting volume handle for PVC {pvc_name}: {e}")
            return None

    def scale_down_idle_workstations(self) -> list:
        self._refresh_config()
        scaled_namespaces = []
        if not self.apps_api: return scaled_namespaces
        try:
            stss = self.apps_api.list_stateful_set_for_all_namespaces(label_selector="app=workstation")
            for sts in stss.items:
                if sts.spec.replicas and sts.spec.replicas > 0:
                    ns = sts.metadata.namespace
                    name = sts.metadata.name
                    self.scale_workstation(ns, name, 0)
                    scaled_namespaces.append(ns)
        except Exception as e:
            logger.error(f"Error scaling down idle workstations: {e}")
        return scaled_namespaces


    def get_workstation_agents(self, user_ns: str, name: str) -> dict:
        self._refresh_config()
        if not self.core_api:
            return {"panes": []}
        try:
            pod_name = f"{name}-0:8001"
            import json
            import ast
            response = self.core_api.connect_get_namespaced_pod_proxy_with_path(
                name=pod_name,
                namespace=user_ns,
                path="api/panes",
                _preload_content=False
            )
            raw_data = response.read().decode('utf-8')
            
            try:
                return json.loads(raw_data)
            except json.JSONDecodeError:
                # Fallback if k8s client somehow still returns a python dict string
                try:
                    return ast.literal_eval(raw_data)
                except Exception:
                    raise Exception(f"Failed to parse proxy response. Raw data: {raw_data}")
        except Exception as e:
            logger.error(f"Failed to get agents for workstation {name} in {user_ns}: {e}")
            return {"panes": [{"pane_id": "error", "window_name": "ERROR", "command": "API_PROXY", "status": "FAILED", "task_summary": f"K8s Proxy Error: {str(e)}"}]}

    def save_adc_secret(self, user_ns: str, adc_json: str):
        self._refresh_config()
        if not self.core_api: return
        import base64
        import json
        
        # Try to extract project ID from the uploaded JSON
        try:
            data = json.loads(adc_json)
            project_id = data.get("project_id") or data.get("quota_project_id")
            if project_id and not settings.gcp_project_id:
                logger.info(f"Extracted project ID {project_id} from uploaded ADC JSON")
                settings.gcp_project_id = project_id
        except Exception as e:
            logger.warning(f"Could not parse project ID from uploaded ADC JSON: {e}")

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name="gcp-adc-credentials"),
            type="Opaque",
            data={"adc.json": base64.b64encode(adc_json.encode()).decode()}
        )
        try:
            self.core_api.read_namespaced_secret(name="gcp-adc-credentials", namespace=user_ns)
            self.core_api.replace_namespaced_secret(name="gcp-adc-credentials", namespace=user_ns, body=secret)
        except Exception:
            try:
                self.core_api.create_namespaced_secret(namespace=user_ns, body=secret)
            except Exception as e:
                logger.error(f"Failed to create ADC secret in {user_ns}: {e}")

    def check_adc_secret(self, user_ns: str) -> bool:
        self._refresh_config()
        if not self.core_api: return False
        try:
            self.core_api.read_namespaced_secret(name="gcp-adc-credentials", namespace=user_ns)
            return True
        except Exception:
            return False

    def save_ssh_key(self, user_ns: str, ssh_key: str):
        self._refresh_config()
        if not self.core_api: return
        import base64

        # Ensure SSH key ends with a newline. 
        # OpenSSH is extremely picky and often requires a newline after the END delimiter.
        if ssh_key:
            ssh_key = ssh_key.strip() + "\n"

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name="ssh-key-secret"),
            type="Opaque",
            data={"id_rsa": base64.b64encode(ssh_key.encode()).decode()}
        )
        try:
            self.core_api.read_namespaced_secret(name="ssh-key-secret", namespace=user_ns)
            self.core_api.replace_namespaced_secret(name="ssh-key-secret", namespace=user_ns, body=secret)
        except Exception:
            try:
                self.core_api.create_namespaced_secret(namespace=user_ns, body=secret)
            except Exception as e:
                logger.error(f"Failed to create SSH key secret in {user_ns}: {e}")

    def check_ssh_key(self, user_ns: str) -> bool:
        self._refresh_config()
        if not self.core_api: return False
        try:
            self.core_api.read_namespaced_secret(name="ssh-key-secret", namespace=user_ns)
            return True
        except Exception:
            return False

    def list_nodes(self) -> list[dict]:
        self._refresh_config()
        if not self.core_api: return []
        try:
            nodes = self.core_api.list_node()
            result = []
            for node in nodes.items:
                labels = node.metadata.labels or {}
                allocatable = node.status.allocatable or {}
                ready = False
                if node.status.conditions:
                    for cond in node.status.conditions:
                        if cond.type == "Ready":
                            ready = cond.status == "True"
                            break
                result.append({
                    "name": node.metadata.name,
                    "machine_type": labels.get("node.kubernetes.io/instance-type", "unknown"),
                    "zone": labels.get("topology.kubernetes.io/zone", "unknown"),
                    "cpu": allocatable.get("cpu", "0"),
                    "memory": allocatable.get("memory", "0"),
                    "gpu": allocatable.get("nvidia.com/gpu", "0"),
                    "ready": ready,
                })
            return result
        except Exception as e:
            logger.error(f"Error listing nodes: {e}")
            return []

    # ── Service (non-workstation pod) operations ──────────────────────────

    def apply_service_statefulset(self, user_ns: str, name: str, image: str, replicas: int,
                                  ports: list[int] = None, cpu: str = "2000m", memory: str = "8Gi",
                                  env_vars: dict = None, data_mount_path: str = "/data",
                                  health_check_command: list[str] = None):
        """Create or update a StatefulSet for a service pod (database, cache, etc.)."""
        if ports is None:
            ports = []
        self._refresh_config()
        if not self.apps_api:
            return

        k8s_name = f"svc-{name}"

        container_ports = [client.V1ContainerPort(container_port=p) for p in ports]

        resource_requests = {"cpu": cpu, "memory": memory}

        volume_mounts = [
            client.V1VolumeMount(name="data", mount_path=data_mount_path),
        ]
        volumes = [
            client.V1Volume(
                name="data",
                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=f"{k8s_name}-pvc")
            ),
        ]

        env_list = []
        if env_vars:
            for k, v in env_vars.items():
                env_list.append(client.V1EnvVar(name=k, value=v))

        # Readiness probe from catalog health check
        readiness_probe = None
        if health_check_command:
            readiness_probe = client.V1Probe(
                _exec=client.V1ExecAction(command=health_check_command),
                initial_delay_seconds=10,
                period_seconds=10,
                timeout_seconds=5,
            )

        sts = client.V1StatefulSet(
            metadata=client.V1ObjectMeta(
                name=k8s_name,
                labels={
                    "app": k8s_name,
                    "managed-by": "workstation-lite",
                    "resource-type": "service",
                }
            ),
            spec=client.V1StatefulSetSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels={"app": k8s_name}),
                service_name=k8s_name,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={
                        "app": k8s_name,
                        "resource-type": "service",
                    }),
                    spec=client.V1PodSpec(
                        init_containers=[
                            client.V1Container(
                                name="fix-service-permissions",
                                image="busybox",
                                command=["sh", "-c", f"chmod 777 {data_mount_path}"],
                                security_context=client.V1SecurityContext(
                                    run_as_user=0
                                ),
                                volume_mounts=volume_mounts,
                            )
                        ],
                        containers=[
                            client.V1Container(
                                name=k8s_name,
                                image=image,
                                ports=container_ports if container_ports else None,
                                env=env_list if env_list else None,
                                resources=client.V1ResourceRequirements(
                                    requests=resource_requests,
                                ),
                                volume_mounts=volume_mounts,
                                readiness_probe=readiness_probe,
                            )
                        ],
                        volumes=volumes,
                    )
                )
            )
        )
        try:
            self.apps_api.read_namespaced_stateful_set(name=k8s_name, namespace=user_ns)
            self.apps_api.replace_namespaced_stateful_set(name=k8s_name, namespace=user_ns, body=sts)
        except Exception:
            try:
                self.apps_api.create_namespaced_stateful_set(namespace=user_ns, body=sts)
            except Exception as e:
                logger.error(f"Failed to create service StatefulSet {k8s_name} in {user_ns}: {e}")

    def apply_cluster_ip_service(self, user_ns: str, name: str, ports: list[int]):
        """Create or update a ClusterIP Service for a service pod."""
        self._refresh_config()
        if not self.core_api:
            return

        k8s_name = f"svc-{name}"
        svc_ports = [
            client.V1ServicePort(port=p, target_port=p, name=f"port-{p}")
            for p in ports
        ]

        svc = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=k8s_name,
                labels={
                    "managed-by": "workstation-lite",
                    "resource-type": "service",
                }
            ),
            spec=client.V1ServiceSpec(
                selector={"app": k8s_name},
                ports=svc_ports,
                type="ClusterIP",
            )
        )
        try:
            self.core_api.read_namespaced_service(name=k8s_name, namespace=user_ns)
            self.core_api.replace_namespaced_service(name=k8s_name, namespace=user_ns, body=svc)
        except Exception:
            try:
                self.core_api.create_namespaced_service(namespace=user_ns, body=svc)
            except Exception as e:
                logger.error(f"Failed to create ClusterIP Service {k8s_name} in {user_ns}: {e}")

    def get_service_status(self, user_ns: str, name: str) -> dict:
        k8s_name = f"svc-{name}"
        self._refresh_config()
        if not self.apps_api or not self.core_api:
            return {"status": "UNKNOWN", "pod_name": None, "pod_ready": False}
        try:
            sts = self.apps_api.read_namespaced_stateful_set(name=k8s_name, namespace=user_ns)

            status = "UNKNOWN"
            pod_ready = False
            pod_name = f"{k8s_name}-0"
            error_message = None
            restart_count = 0
            last_restart_time = None
            last_restart_reason = None

            try:
                pod = self.core_api.read_namespaced_pod(name=pod_name, namespace=user_ns)
                if pod.status.container_statuses:
                    container_status = pod.status.container_statuses[0]
                    state = container_status.state
                    
                    restart_count = container_status.restart_count or 0
                    if container_status.last_state and container_status.last_state.terminated:
                        last_term = container_status.last_state.terminated
                        if last_term.finished_at:
                            last_restart_time = last_term.finished_at.isoformat()
                        last_restart_reason = last_term.reason

                    if state.waiting:
                        reason = state.waiting.reason
                        if reason in ["ImagePullBackOff", "ErrImagePull", "CrashLoopBackOff", "CreateContainerConfigError"]:
                            status = "ERROR"
                            error_message = f"Pod Error: {reason} - {state.waiting.message or 'Check logs'}"
                    elif state.terminated:
                        if state.terminated.exit_code != 0:
                            status = "ERROR"
                            error_message = f"Pod Terminated with exit code {state.terminated.exit_code}: {state.terminated.reason}"
            except Exception:
                pass

            # Fetch recent cluster events for the pod (e.g. Evicted, Preempting)
            try:
                events = self.core_api.list_namespaced_event(namespace=user_ns, field_selector=f"involvedObject.name={pod_name}")
                recent_warnings = []
                for e in events.items:
                    if e.type == "Warning" or e.reason in ["Evicted", "Preempting", "Failed", "NodeNotReady"]:
                        recent_warnings.append(e)
                if recent_warnings:
                    recent_warnings.sort(key=lambda x: x.last_timestamp or x.event_time or x.metadata.creation_timestamp, reverse=True)
                    latest_event = recent_warnings[0]
                    event_ts = latest_event.last_timestamp or latest_event.event_time or latest_event.metadata.creation_timestamp
                    if event_ts:
                        event_time_str = event_ts.isoformat()
                        if not last_restart_time or event_time_str > last_restart_time:
                            last_restart_time = event_time_str
                            last_restart_reason = f"Cluster Event ({latest_event.reason}): {latest_event.message}"
                            if restart_count == 0:
                                restart_count = 1
            except Exception as ev_err:
                logger.error(f"Error fetching events for {pod_name}: {ev_err}")

            if status != "ERROR":
                if sts.status.ready_replicas and sts.status.ready_replicas > 0:
                    status = "RUNNING"
                    pod_ready = True
                elif sts.spec.replicas == 0:
                    status = "STOPPED"
                else:
                    status = "PROVISIONING"

            return {
                "status": status,
                "pod_name": pod_name,
                "pod_ready": pod_ready,
                "message": error_message,
                "restart_count": restart_count,
                "last_restart_time": last_restart_time,
                "last_restart_reason": last_restart_reason
            }
        except Exception as e:
            if hasattr(e, 'status') and e.status == 404:
                return {"status": "STOPPED", "pod_name": None, "pod_ready": False}
            if "404" in str(e):
                return {"status": "STOPPED", "pod_name": None, "pod_ready": False}
            logger.error(f"Error getting service status for {user_ns}/{name}: {e}")
            return {"status": "UNKNOWN", "pod_name": None, "pod_ready": False}

    def list_services(self, user_ns: str) -> list[dict]:
        self._refresh_config()
        if not self.apps_api:
            return []
        try:
            stss = self.apps_api.list_namespaced_stateful_set(
                namespace=user_ns,
                label_selector="managed-by=workstation-lite,resource-type=service"
            )
            services = []
            for sts in stss.items:
                k8s_name = sts.metadata.name
                # Strip the svc- prefix for the user-facing name
                name = k8s_name[4:] if k8s_name.startswith("svc-") else k8s_name
                status_info = self.get_service_status(user_ns, name)
                status_info["name"] = name
                try:
                    status_info["image"] = sts.spec.template.spec.containers[0].image
                except (IndexError, AttributeError):
                    status_info["image"] = "unknown"
                services.append(status_info)
            return services
        except Exception as e:
            logger.error(f"Error listing services in {user_ns}: {e}")
            return []

    def save_service_config(self, user_ns: str, service_name: str, image: str, service_type: str = "custom",
                            ports: list[int] = None, cpu: str = "2000m", memory: str = "8Gi",
                            disk_size: str = "5Gi", env_vars: dict = None,
                            data_mount_path: str = "/data", health_check_command: list[str] = None):
        if ports is None:
            ports = []
        self._refresh_config()
        if not self.core_api:
            return
        import json
        cm_name = "service-configs"
        config_data = json.dumps({
            "image": image, "service_type": service_type, "ports": ports,
            "cpu": cpu, "memory": memory, "disk_size": disk_size,
            "env_vars": env_vars or {},
            "data_mount_path": data_mount_path,
            "health_check_command": health_check_command or [],
        })
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            if not cm.data:
                cm.data = {}
            cm.data[service_name] = config_data
            self.core_api.patch_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
        except Exception:
            cm = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=cm_name),
                data={service_name: config_data}
            )
            try:
                self.core_api.create_namespaced_config_map(namespace=user_ns, body=cm)
            except Exception as e:
                logger.error(f"Failed to save service config in {user_ns}: {e}")

    def get_service_config(self, user_ns: str, service_name: str) -> dict:
        self._refresh_config()
        default_config = {
            "image": None, "service_type": "custom", "ports": [],
            "cpu": "2000m", "memory": "8Gi", "disk_size": "5Gi", "env_vars": {},
            "data_mount_path": "/data", "health_check_command": [],
        }
        if not self.core_api:
            return default_config
        cm_name = "service-configs"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            val = cm.data.get(service_name)
            if not val:
                return default_config
            import json
            parsed = json.loads(val)
            return {
                "image": parsed.get("image"),
                "service_type": parsed.get("service_type", "custom"),
                "ports": parsed.get("ports", []),
                "cpu": parsed.get("cpu", "2000m"),
                "memory": parsed.get("memory", "8Gi"),
                "disk_size": parsed.get("disk_size", "5Gi"),
                "env_vars": parsed.get("env_vars", {}),
                "data_mount_path": parsed.get("data_mount_path", "/data"),
                "health_check_command": parsed.get("health_check_command", []),
            }
        except Exception:
            return default_config

    def delete_service_config(self, user_ns: str, service_name: str):
        self._refresh_config()
        if not self.core_api:
            return
        cm_name = "service-configs"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace=user_ns)
            if cm.data and service_name in cm.data:
                del cm.data[service_name]
                if not cm.data:
                    cm.data = {}
                self.core_api.replace_namespaced_config_map(name=cm_name, namespace=user_ns, body=cm)
                logger.info(f"Removed service config for {service_name} in {user_ns}")
        except Exception as e:
            if not (hasattr(e, 'status') and e.status == 404):
                logger.error(f"Failed to delete service config for {service_name} in {user_ns}: {e}")

    def delete_service(self, user_ns: str, name: str):
        """Delete a service's StatefulSet, ClusterIP Service, and PVC."""
        self._refresh_config()
        if not self.apps_api or not self.core_api:
            return

        k8s_name = f"svc-{name}"

        # 1. Delete StatefulSet
        try:
            self.apps_api.delete_namespaced_stateful_set(name=k8s_name, namespace=user_ns)
            logger.info(f"Deleted service StatefulSet {k8s_name} in {user_ns}")
        except Exception as e:
            if not (hasattr(e, 'status') and e.status == 404):
                logger.error(f"Failed to delete service StatefulSet {k8s_name} in {user_ns}: {e}")

        # 2. Delete ClusterIP Service
        try:
            self.core_api.delete_namespaced_service(name=k8s_name, namespace=user_ns)
            logger.info(f"Deleted ClusterIP Service {k8s_name} in {user_ns}")
        except Exception as e:
            if not (hasattr(e, 'status') and e.status == 404):
                logger.error(f"Failed to delete ClusterIP Service {k8s_name} in {user_ns}: {e}")

        # 3. Delete PVC
        pvc_name = f"{k8s_name}-pvc"
        try:
            self.core_api.delete_namespaced_persistent_volume_claim(name=pvc_name, namespace=user_ns)
            logger.info(f"Deleted service PVC {pvc_name} in {user_ns}")
        except Exception as e:
            if not (hasattr(e, 'status') and e.status == 404):
                logger.error(f"Failed to delete service PVC {pvc_name} in {user_ns}: {e}")

        # 4. Remove config
        self.delete_service_config(user_ns, name)

    # ── Service catalog template operations ────────────────────────────────

    def get_service_catalog_templates(self) -> list[dict]:
        """Read service catalog templates from ConfigMap. Seeds defaults if missing."""
        self._refresh_config()
        if not self.core_api:
            # Fallback to hardcoded defaults if k8s not available
            from app.models.service import DEFAULT_SERVICE_CATALOG
            return [entry.model_dump() for entry in DEFAULT_SERVICE_CATALOG]
        import json
        cm_name = "service-catalog-templates"
        try:
            cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace="default")
            if not cm.data:
                return []
            templates = []
            for val in cm.data.values():
                templates.append(json.loads(val))
            return templates
        except Exception as e:
            if hasattr(e, 'status') and e.status == 404:
                self.seed_service_catalog_templates()
                # Retry after seeding
                try:
                    cm = self.core_api.read_namespaced_config_map(name=cm_name, namespace="default")
                    if not cm.data:
                        return []
                    return [json.loads(val) for val in cm.data.values()]
                except Exception:
                    pass
            logger.error(f"Error reading service catalog templates: {e}")
            from app.models.service import DEFAULT_SERVICE_CATALOG
            return [entry.model_dump() for entry in DEFAULT_SERVICE_CATALOG]

    def seed_service_catalog_templates(self):
        """Create or update the service catalog ConfigMap with default templates."""
        self._refresh_config()
        if not self.core_api:
            return
        import json
        from app.models.service import DEFAULT_SERVICE_CATALOG
        cm_name = "service-catalog-templates"
        data = {}
        for entry in DEFAULT_SERVICE_CATALOG:
            data[entry.service_type] = json.dumps(entry.model_dump())
        cm = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=cm_name),
            data=data,
        )
        try:
            self.core_api.read_namespaced_config_map(name=cm_name, namespace="default")
            # Already exists — replace it
            self.core_api.replace_namespaced_config_map(name=cm_name, namespace="default", body=cm)
            logger.info("Updated service catalog templates ConfigMap")
        except Exception:
            try:
                self.core_api.create_namespaced_config_map(namespace="default", body=cm)
                logger.info("Seeded service catalog templates ConfigMap")
            except Exception as e:
                logger.error(f"Failed to seed service catalog templates: {e}")

    def scale_service(self, user_ns: str, name: str, replicas: int):
        k8s_name = f"svc-{name}"
        self._refresh_config()
        if not self.apps_api:
            return
        body = client.V1Scale(spec=client.V1ScaleSpec(replicas=replicas))
        try:
            self.apps_api.patch_namespaced_stateful_set_scale(name=k8s_name, namespace=user_ns, body=body)
        except Exception as e:
            logger.error(f"Failed to scale service {k8s_name} in {user_ns}: {e}")


k8s_manager = K8sManager()
