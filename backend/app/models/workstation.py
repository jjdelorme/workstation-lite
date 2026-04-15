from enum import Enum
from pydantic import BaseModel
from typing import Optional

class WorkstationStatus(str, Enum):
    PROVISIONING = "PROVISIONING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"

class WorkstationResponse(BaseModel):
    name: str
    user_ns: str
    status: WorkstationStatus
    image: Optional[str] = None
    ports: list[int] = []
    cpu: str = "2000m"
    memory: str = "8Gi"
    disk_size: str = "10Gi"
    gpu: Optional[str] = None
    use_spot: bool = False
    run_as_root: bool = False
    env_vars: dict[str, str] = {}
    pod_name: Optional[str] = None
    pod_ready: bool = False
    message: Optional[str] = None
    restart_count: int = 0
    last_restart_time: Optional[str] = None
    last_restart_reason: Optional[str] = None

class WorkstationListResponse(BaseModel):
    workstations: list[WorkstationResponse]
    count: int

class WorkstationStartRequest(BaseModel):
    # Optional parameters for the workstation
    pass

class BuildRequest(BaseModel):
    dockerfile: str

class SaveConfigRequest(BaseModel):
    image: Optional[str] = None
    ports: Optional[list[int]] = []
    cpu: Optional[str] = "2000m"
    memory: Optional[str] = "8Gi"
    disk_size: Optional[str] = "10Gi"
    gpu: Optional[str] = None
    use_spot: Optional[bool] = False
    run_as_root: Optional[bool] = False
    env_vars: Optional[dict[str, str]] = None
