# IDP Services Plan

Add support for "Services" — non-workstation pods (databases, caches, queues, etc.) that run alongside workstations in the same cluster and namespace, accessible via Kubernetes DNS.

## User-Provided Configuration

| Field | Example | Notes |
|-------|---------|-------|
| **Name** | `my-postgres` | Same naming rules as workstations |
| **Type/Template** | `PostgreSQL 16` | Pre-built catalog of common services |
| **Environment vars** | `POSTGRES_PASSWORD=secret` | Service-specific config |
| **Ports** | `5432` | Port(s) the service listens on |
| **CPU / Memory** | `500m` / `1Gi` | Same resource controls as workstations |
| **Disk size** | `10Gi` | For persistent data |

No Dockerfile editor — users pick from a catalog of pre-built images. Optionally allow custom images for advanced users.

## Data Model

New `ServiceConfig` Pydantic model mirroring `WorkstationConfig`:

```python
class ServiceConfig(BaseModel):
    image: str                          # e.g. "postgres:16"
    service_type: str                   # "postgresql", "redis", "custom"
    ports: List[int] = []              # [5432]
    cpu: str = "250m"
    memory: str = "512Mi"
    disk_size: str = "5Gi"
    env_vars: Dict[str, str] = {}
    # No GPU field — services don't need it
```

Stored in a new ConfigMap (`service-configs`) per user namespace, following the existing workstation pattern.

## Service Catalog Templates

Pre-defined templates for common services. Each template specifies the image, default ports, data mount path, and health check:

| Service | Image | Port | Data Mount Path | Health Check |
|---------|-------|------|-----------------|--------------|
| PostgreSQL 16 | `postgres:16` | 5432 | `/var/lib/postgresql/data` | `pg_isready` |
| Redis 7 | `redis:7` | 6379 | `/data` | `redis-cli ping` |
| MySQL 8 | `mysql:8` | 3306 | `/var/lib/mysql` | `mysqladmin ping` |
| MongoDB 7 | `mongo:7` | 27017 | `/data/db` | `mongosh --eval "db.runCommand('ping')"` |
| RabbitMQ 3 | `rabbitmq:3-management` | 5672, 15672 | `/var/lib/rabbitmq` | `rabbitmq-diagnostics check_running` |
| Custom | user-specified | user-specified | user-specified | none |

## Kubernetes Resources

Each service creates two k8s resources (vs one for workstations):

### StatefulSet

Same pattern as workstations with these differences:

- Name prefix: `svc-` (e.g., `svc-my-postgres`) to avoid collisions with workstation names
- Label `resource-type: service` to distinguish from workstations
- Data mount path varies per service type (not always `/home/workspace`)
- Readiness probe based on catalog health check
- No GPU support
- No init container for permission fixing (upstream images handle their own users)

### ClusterIP Service (NEW — not used for workstations)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-my-postgres
  labels:
    managed-by: workstation-lite
    resource-type: service
spec:
  selector:
    app: svc-my-postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

This gives the service a stable DNS name within the cluster, enabling workstation-to-service connectivity.

## Workstation-to-Service Connectivity

Since both workstations and services run in the same GKE cluster and namespace, Kubernetes DNS handles connectivity automatically:

```bash
# From inside a workstation pod (same namespace):
psql -h svc-my-postgres -p 5432 -U postgres

# Cross-namespace (if needed):
psql -h svc-my-postgres.other-namespace.svc.cluster.local -p 5432 -U postgres
```

No kubectl, no port-forwarding, no external IPs required.

## Terminal One-Liner (Debug Access)

Reuse the existing connect script pattern, adapted for services:

- **Port-forward mode** (primary): Sets up `kubectl port-forward` so users can connect from their laptop (e.g., `psql -h localhost -p 5432`)
- **Exec mode** (debug): `kubectl exec -it` into the service container for troubleshooting

```bash
# Port-forward (connect from laptop)
/bin/bash -c "$(curl -fsSL https://{host}/api/services/{user_ns}/connect/{name})"

# Debug shell
/bin/bash -c "$(curl -fsSL https://{host}/api/services/{user_ns}/exec/{name})"
```

## API Endpoints

New routes under `/api/services/`, mirroring workstation endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/services/catalog` | List available service templates |
| `GET` | `/{user_ns}/list` | List all services in namespace |
| `POST` | `/{user_ns}/save-config/{name}` | Save service config |
| `POST` | `/{user_ns}/start/{name}` | Create & start service |
| `POST` | `/{user_ns}/stop/{name}` | Stop service (scale to 0) |
| `POST` | `/{user_ns}/delete/{name}` | Delete service + PVC |
| `GET` | `/{user_ns}/status/{name}` | Get service status |
| `GET` | `/{user_ns}/connect/{name}` | Generate port-forward script |
| `GET` | `/{user_ns}/exec/{name}` | Generate exec script |

## UI Design

### New Tab

Add a "Services" tab between Workstations and Image Templates:

```
[ Workstations ]  [ Services ]  [ Image Templates ]  [ Infrastructure ]
```

### Service Card

Similar to workstation cards but simpler:

```
┌──────────────────────────────────────────────┐
│  my-postgres                      ● Running  │
│  PostgreSQL 16                               │
│                                              │
│  Connect from workstation:                   │
│  ┌────────────────────────────────────────┐  │
│  │ psql -h svc-my-postgres -p 5432       │ Copy │
│  └────────────────────────────────────────┘  │
│                                              │
│  CPU: 250m  Memory: 512Mi  Disk: 5Gi        │
│                                              │
│  > Environment Variables (1)                 │
│  > Debug Connection (one-liner)              │
│                                              │
│  [ Stop ]  [ Delete ]  [ Edit Config ]       │
└──────────────────────────────────────────────┘
```

Key differences from workstation cards:
- No Dockerfile editor
- Prominent "connect from workstation" string (primary access pattern)
- Debug one-liner in expandable section (not the primary access)
- Service type badge/icon

### "Create Service" Dialog

Catalog picker instead of a blank Dockerfile:

```
┌─ Create Service ──────────────────────────────┐
│                                               │
│  Name: [my-postgres          ]                │
│                                               │
│  Template:                                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│  │Postgr│ │Redis │ │MySQL │ │Mongo │        │
│  └──────┘ └──────┘ └──────┘ └──────┘        │
│  ┌──────┐ ┌──────┐                           │
│  │Rabbit│ │Custom│                           │
│  └──────┘ └──────┘                           │
│                                               │
│  Resources:                                   │
│  CPU: [250m]  Memory: [512Mi]                │
│  Disk: [5Gi]                                  │
│                                               │
│  Environment Variables:                       │
│  POSTGRES_PASSWORD = [********]               │
│  [+ Add Variable]                             │
│                                               │
│              [ Cancel ]  [ Create & Start ]   │
└───────────────────────────────────────────────┘
```

### Cross-Reference on Workstation Cards

On workstation cards (when RUNNING), show a small "Available Services" indicator listing services running in the same namespace.

## Design Considerations

1. **Namespace strategy** — Services go in the same namespace as the user's workstations. This means `svc-my-postgres` is reachable by short name with no DNS suffix.

2. **Naming prefix** — `svc-` prefix on k8s resource names avoids collisions with workstation names. Users see "my-postgres"; k8s sees `svc-my-postgres`.

3. **Data mount paths** — Each service type has its own data directory (unlike workstations which always use `/home/workspace`). The catalog template defines the correct path.

4. **Health checks** — Catalog templates include readiness probes (e.g., `pg_isready`). Health status shown on cards.

5. **No image building** — Services use upstream images directly. No Cloud Build integration needed.

6. **Secret management** — Store service configs containing credentials in a Kubernetes Secret rather than a ConfigMap. Mask passwords in the UI.

7. **Lifecycle & scale-to-zero** — Services should participate in `scale-to-zero` / `stop-all` operations for cost savings, but consider making this configurable per service.

8. **PVC cleanup** — Same as workstations: deleting a service destroys both StatefulSet and PVC.

## Implementation Order

### Step 1: Backend Model + ConfigMap Storage
- Add `ServiceConfig` model to `backend/app/models/`
- Add service catalog definitions (template registry)
- Add ConfigMap CRUD for `service-configs` in `k8s.py`

### Step 2: K8s Resource Creation
- Add `apply_service_statefulset()` to `k8s.py` (adapted from workstation version)
- Add `apply_cluster_ip_service()` to `k8s.py` (new — creates ClusterIP Service)
- Add `delete_service()` to `k8s.py` (deletes StatefulSet + Service + PVC)
- Add readiness probe support based on catalog templates

### Step 3: API Endpoints
- Create `backend/app/api/services.py` mirroring `workstations.py`
- Register routes in `main.py`
- Implement catalog endpoint, CRUD, start/stop/delete, status, connect/exec scripts

### Step 4: Connect Scripts
- Port-forward script for laptop access
- Exec script for debug shell access

### Step 5: UI — Service Tab + Cards
- Add Services tab to `App.tsx`
- Create `ServiceCard` component
- Create `NewServiceDialog` with catalog picker
- Create `EditServiceDialog` for config changes
- Add connection string display with copy button

### Step 6: Cross-References
- Show available services on workstation cards
- Include services in `stop-all` / `scale-to-zero` operations

### Step 7: Tests
- Unit tests for service model, k8s operations, API endpoints
- Mirror existing workstation test patterns
