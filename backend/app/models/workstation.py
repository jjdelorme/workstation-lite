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
    pod_name: Optional[str] = None
    pod_ready: bool = False
    message: Optional[str] = None

class WorkstationListResponse(BaseModel):
    workstations: list[WorkstationResponse]
    count: int

class WorkstationStartRequest(BaseModel):
    # Optional parameters for the workstation
    pass

class BuildRequest(BaseModel):
    dockerfile: str

class SaveConfigRequest(BaseModel):
    image: str
    ports: Optional[list[int]] = [3000]
