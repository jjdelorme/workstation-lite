from enum import Enum
from pydantic import BaseModel
from typing import Optional


class ServiceStatus(str, Enum):
    PROVISIONING = "PROVISIONING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


class ServiceCatalogEntry(BaseModel):
    service_type: str
    label: str
    image: str
    ports: list[int]
    data_mount_path: str
    health_check_command: list[str]
    required_env_vars: dict[str, str] = {}


# Seed data — written to ConfigMap on first access, then ConfigMap is source of truth
DEFAULT_SERVICE_CATALOG: list[ServiceCatalogEntry] = [
    ServiceCatalogEntry(
        service_type="postgresql",
        label="PostgreSQL 16",
        image="postgres:16",
        ports=[5432],
        data_mount_path="/var/lib/postgresql/data",
        health_check_command=["pg_isready"],
        required_env_vars={"PGDATA": "/var/lib/postgresql/data/pgdata", "POSTGRES_PASSWORD": "changeme"},
    ),
    ServiceCatalogEntry(
        service_type="redis",
        label="Redis 7",
        image="redis:7",
        ports=[6379],
        data_mount_path="/data",
        health_check_command=["redis-cli", "ping"],
    ),
    ServiceCatalogEntry(
        service_type="mysql",
        label="MySQL 8",
        image="mysql:8",
        ports=[3306],
        data_mount_path="/var/lib/mysql",
        health_check_command=["mysqladmin", "ping"],
        required_env_vars={"MYSQL_ROOT_PASSWORD": "changeme"},
    ),
    ServiceCatalogEntry(
        service_type="mongodb",
        label="MongoDB 7",
        image="mongo:7",
        ports=[27017],
        data_mount_path="/data/db",
        health_check_command=["mongosh", "--eval", "db.runCommand('ping')"],
    ),
    ServiceCatalogEntry(
        service_type="rabbitmq",
        label="RabbitMQ 3",
        image="rabbitmq:3-management",
        ports=[5672, 15672],
        data_mount_path="/var/lib/rabbitmq",
        health_check_command=["rabbitmq-diagnostics", "check_running"],
    ),
]


class SaveServiceConfigRequest(BaseModel):
    image: Optional[str] = None
    service_type: str = "custom"
    ports: Optional[list[int]] = None
    cpu: Optional[str] = "2000m"
    memory: Optional[str] = "8Gi"
    disk_size: Optional[str] = "5Gi"
    env_vars: Optional[dict[str, str]] = None
    data_mount_path: Optional[str] = None
    health_check_command: Optional[list[str]] = None


class ServiceResponse(BaseModel):
    name: str
    user_ns: str
    status: ServiceStatus
    image: Optional[str] = None
    service_type: str = "custom"
    ports: list[int] = []
    cpu: str = "2000m"
    memory: str = "8Gi"
    disk_size: str = "5Gi"
    env_vars: dict[str, str] = {}
    data_mount_path: str = "/data"
    health_check_command: list[str] = []
    pod_name: Optional[str] = None
    pod_ready: bool = False
    message: Optional[str] = None
    connect_hint: Optional[str] = None


class ServiceListResponse(BaseModel):
    services: list[ServiceResponse]
    count: int
