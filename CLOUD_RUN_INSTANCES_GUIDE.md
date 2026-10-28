# Cloud Run Instances as Remote Workstations Guide

This guide documents how to run **Workstation Lite** container images on **Google Cloud Run Instances** (`gcloud alpha run instances`), achieve local-disk I/O performance with persistent Google Cloud Storage backups via the **Hybrid Local-Disk + Background `rsync` Architecture**, connect via SSH or remote IDEs (**VS Code Remote-SSH** and **Zed**), and update the underlying container image.

---

## 1. Overview & Architecture Differences (GKE vs. Cloud Run Instances)

| Feature | GKE Workstation (`StatefulSet`) | Cloud Run Instance (`run instances`) |
| :--- | :--- | :--- |
| **Compute Model** | Pod scheduled on GKE Autopilot node | Dedicated long-running microVM container |
| **Lifecycle** | `kubectl scale --replicas=0 / 1` | `gcloud alpha run instances stop / start / restart` |
| **Local Root Disk** | Ephemeral (except mounted PVCs) | **Ephemeral (`tmpfs`/overlay)** — wiped on `stop`, `restart`, or `update` |
| **Active `/home/workspace`** | GCE Zonal Persistent Disk (`standard-rwo` PVC, `ext4`) | **Fast Local Container Filesystem** hydrated on startup from `/mnt/gcs-workspace` |
| **Persistent Backing Store** | GCE Zonal Persistent Disk (`pd.csi.storage.gke.io`) | **Cloud Storage FUSE** (`type=cloud-storage`) mounted at `/mnt/gcs-workspace` + background `rsync` |
| **Incoming SSH Auth** | OpenSSH (`sshd`) or `kubectl exec` | Cloud Run native IAM-authenticated WebSocket tunnel (enabled by default in `gcloud 591.0.0+`) |
| **Console Location** | Kubernetes Engine > Workloads | **Cloud Run > Instances** tab (`https://console.cloud.google.com/run/instances`) |

> [!IMPORTANT]
> **Cloud Run Console Tab:** Cloud Run Instances are a distinct resource type from Cloud Run *Services* and *Jobs*. They do **not** appear under the default Services list—always check the **Instances** tab in the Cloud Run Console or filter by your deployment region (e.g., `us-east4`).

---

## 2. Creating & Managing a Cloud Run Instance

### Prerequisites
Ensure `gcloud` is up to date (`591.0.0+`) and the `alpha` component is installed:
```bash
gcloud components update
gcloud components install alpha
```

### Creating an Instance with Hybrid Local-Disk + GCS Persistence
Instead of mounting the GCS bucket directly at `/home/workspace` (which suffers from severe object-store latency on small files), mount the GCS bucket at `/mnt/gcs-workspace`. The container automatically hydrates `/home/workspace` onto fast local disk at startup and runs a background S6 `rsync` service (`workspace-sync`) to persist changes back to `/mnt/gcs-workspace`:

```bash
# 1. Create a regional GCS bucket in the same region as the instance for low latency
gcloud storage buckets create gs://jasondel-cloudrun10-workstation-workspace \
  --project=jasondel-cloudrun10 \
  --location=us-east4 \
  --uniform-bucket-level-access

# 2. Grant the Cloud Run service account access to the bucket (required for GCS FUSE mount)
gcloud storage buckets add-iam-policy-binding gs://jasondel-cloudrun10-workstation-workspace \
  --member="serviceAccount:1076242320305-compute@developer.gserviceaccount.com" \
  --role="roles/storage.admin" \
  --project=jasondel-cloudrun10

# 3. Create the Cloud Run Instance with GCS mounted at /mnt/gcs-workspace
# (Note: SSH is enabled by default in gcloud 591.0.0+; --enable-ssh is no longer needed)
gcloud alpha run instances create vs-codium29-instance \
  --image=us-central1-docker.pkg.dev/jasondel-cloudrun10/workstation-images/user-1-vs-codium30:latest \
  --project=jasondel-cloudrun10 \
  --region=us-east4 \
  --port=8000 \
  --cpu=4 \
  --memory=16Gi \
  --no-invoker-iam-check \
  --set-env-vars="PUID=1000,PGID=1000,GOOGLE_CLOUD_PROJECT=jasondel-cloudrun10,WORKSPACE_SYNC_INTERVAL=30" \
  --add-volume=name=workspace,type=cloud-storage,bucket=jasondel-cloudrun10-workstation-workspace,mount-options="uid=1000;gid=1000;file-mode=0700;dir-mode=0700;implicit-dirs;stat-cache-max-size-mb=-1;type-cache-max-size-mb=-1;metadata-cache-ttl-secs=120" \
  --add-volume-mount=volume=workspace,mount-path=/mnt/gcs-workspace
```

> [!NOTE]
> **Regional Capacity:** During Preview/Alpha, some regions (such as `us-central1`) may return `REGION_CAPACITY_EXHAUSTED`. Deploying the instance in `us-east4` while pulling the container image from Artifact Registry in `us-central1` works seamlessly.

### Stopping, Starting, and Restarting
```bash
# Stop the instance (triggers SIGTERM final rsync flush; stops compute billing; GCS data persists)
gcloud alpha run instances stop vs-codium29-instance --region=us-east4 --project=jasondel-cloudrun10 --quiet

# Start a stopped instance (hydrates /home/workspace from /mnt/gcs-workspace on boot)
gcloud alpha run instances start vs-codium29-instance --region=us-east4 --project=jasondel-cloudrun10 --quiet

# Restart a running instance
gcloud alpha run instances restart vs-codium29-instance --region=us-east4 --project=jasondel-cloudrun10 --quiet
```

---

## 3. Hybrid Local-Disk + Background `rsync` Storage Architecture

### Why Direct GCS FUSE on `/home/workspace` Is Too Slow for IDEs & Git
Cloud Storage is an immutable object store, not a POSIX block filesystem. When a GCS bucket is mounted directly at `/home/workspace` via Cloud Storage FUSE (`type=cloud-storage`), every `close()` or `fsync()` call must stage and upload the entire object over HTTP to GCS.

Real-world benchmarks on `vs-codium29-instance` (`us-east4`) comparing direct GCS FUSE vs. local container disk:

| Workload | Direct GCS FUSE (`/mnt/gcs-workspace`) | Local Container Disk (`/home/workspace`) | Speedup |
| :--- | :--- | :--- | :--- |
| **Write 50 small files (`4 KiB` each)** | `12.05s` (~240ms/file) | `0.005s` (~0.1ms/file) | **~2,400x faster** |
| **`git status` (medium repo)** | `3.30s` | `0.015s` | **~220x faster** |
| **Incremental `rsync` (`--inplace`, warm cache, 1 file changed)** | `0.24s` | — | Near-instant background flush |

### Why GCS FUSE `cache-dir` (File Cache) Alone Does Not Replace Local Disk
The [Cloud Run Instances Cloud Storage volume mounts documentation](https://docs.cloud.google.com/run/docs/configuring/instances/cloud-storage-volume-mounts) describes an optional `cache-dir=cr-volume:<in-memory-volume>` mount option that caches downloaded objects in an in-memory volume. While useful for read-heavy media/model serving, **`cache-dir` alone cannot replace a local `/home/workspace` for software development** because:
1. **Read-Only Cache (No Write-Back Buffering):** `cache-dir` only accelerates reads. Every file write, save, `git commit`, or `npm install` still flushes synchronously to GCS on `close()`/`fsync()`, incurring ~200ms+ HTTP upload latency per file and ~64 MiB of memory staging per open write stream.
2. **No Per-File POSIX Permissions (`chmod` / `chown`):** GCS FUSE applies uniform mount-wide `file-mode`/`dir-mode` bits; `chmod 600 ~/.ssh/id_rsa` is a no-op without custom mount options.
3. **Lack of Native POSIX File Locking & Atomic Rename Semantics:** Tools like Git (`.git/index.lock`), SQLite (`.claude`, `.codex` state databases), and IDE language servers rely on fast atomic renames and POSIX locks. On GCS FUSE, every rename is a server-side `CopyObject` + `DeleteObject` API round-trip.

### How the Hybrid Architecture Works (`templates/Dockerfile.template`)

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Cloud Run Instance Container (16Gi–32Gi RAM, 4–8 vCPU)                     │
│                                                                            │
│  ┌──────────────────────────────┐    1. Startup Hydration (16x parallel)   │
│  │ /home/workspace (Local Disk) │ ◄──────────────────────────────────────┐ │
│  │ - Native POSIX perms & locks │                                        │ │
│  │ - 0.005s for 50 file writes  │    2. Periodic (30s) + SIGTERM Sync    │ │
│  │ - 0.015s git status          │ ─────────────────────────────────────► │ │
│  │ - Full node_modules / .venv  │    rsync -rltD --inplace --delete      │ │
│  └──────────────────────────────┘    (excludes node_modules, venv, etc.) │ │
│                                                                          ▼ │
│                                     ┌────────────────────────────────────┐ │
│                                     │ /mnt/gcs-workspace (GCS FUSE)      │ │
│                                     │ gs://...-workstation-workspace     │ │
│                                     │ stat/type cache: -1 (unlimited)    │ │
│                                     │ metadata-cache-ttl-secs: 120       │ │
│                                     └────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

1. **Startup Hydration (`/custom-cont-init.d/99-setup-user`):**
   * Runs synchronously during S6 container initialization (`init-custom-files`), before `svc-vscodium-web` or `custom-svc-workspace-sync` starts.
   * Detects if `/mnt/gcs-workspace` is mounted in `/proc/mounts` and `/home/workspace` is not a volume mount. (If running on GKE where `/mnt/gcs-workspace` is not mounted, hydration and background sync are automatically no-ops.)
   * Uses 16 parallel `rsync` workers (`find /mnt/gcs-workspace -mindepth 1 -maxdepth 1 -print0 | xargs -0 -r -P 16 -I {} rsync -a ... "{}" /home/workspace/`) with `set -o pipefail` to saturate GCS FUSE read concurrency, hydrating ~1 GiB / 6,500+ files in ~35–75 seconds instead of 5+ minutes with single-threaded `rsync`.
   * Only if the parallel hydration pipeline exits with status `0` does it record the initial local file manifest (`/run/workspace-sync/manifest`) and write the `/run/workspace-hydrated` sentinel file. The sync daemon refuses to run unless `/run/workspace-hydrated` exists, preventing an unhydrated or partially hydrated `/home/workspace` from ever wiping the bucket.
   * Sets ownership (`chown -R abc:abc /home/workspace`) and enforces true POSIX permissions on `/home/workspace/.ssh` (`chmod 700 ~/.ssh`, `chmod 600` on private keys, `chmod 644` on `.pub`, `known_hosts`, and `config`).
2. **Periodic & Graceful-Shutdown Incremental Sync (`/custom-services.d/workspace-sync` & `/usr/local/bin/workspace-sync-now`):**
   * Supervised by S6 Overlay v3 as `custom-svc-workspace-sync` with `ENV S6_SERVICES_GRACETIME=8000` (giving S6 services an 8-second shutdown grace period within Cloud Run's 10-second `SIGTERM` window instead of S6's default 3-second timeout).
   * Runs `/usr/local/bin/workspace-sync-now` every `WORKSPACE_SYNC_INTERVAL` seconds (default `30s`) and traps `SIGTERM`, `SIGINT`, and `SIGHUP` to perform a final blocking sync (`workspace-sync-now --wait`) when the instance stops or restarts.
   * Uses `flock` on `/run/workspace-sync/lock` (inside a mode `0777` `/run/workspace-sync` directory with `umask 000` so both `root` and `abc` can invoke it) to prevent overlapping sync runs, and ignores `rsync` exit code `24` (vanished temporary files during active builds).
   * You can also trigger an immediate sync manually at any time (as either `abc` or `root`) by running:
     ```bash
     workspace-sync-now --wait
     # Or force a full destination directory walk with rsync --delete:
     workspace-sync-now --wait --full-delete
     ```
3. **Why Local Manifest Deletion Tracking + 16x Parallel `rsync -rltDO --inplace --no-perms --no-owner --no-group` Is Used:**
   * **Avoiding Temp-File Rename Overhead (`--inplace`):** Standard `rsync -a` writes every updated file to a temporary `.filename.XXXXXX` object and then renames it over `filename`. On GCS FUSE, a `rename()` triggers a server-side GCS `CopyObject` + `DeleteObject`, doubling the API requests and write latency (`2.61s` vs `1.26s` for 10 files). Passing `--inplace` writes directly to the target object in a single `close()`/upload.
   * **Avoiding GCS FUSE `readdir()` Scans via Local Manifest Diffing (`1.3s` vs `42.8s`):** In GCS FUSE, `stat-cache` and `type-cache` only cache `lstat()` (`LookUpInode`/`GetInodeAttributes`), *not* directory listings (`readdir()` / `Objects: list`). Running a single-threaded `rsync --delete` forces `rsync` to call `readdir()` on all ~1,400 directories in `/mnt/gcs-workspace` sequentially (~30ms HTTP call per directory = **42.8 seconds** per sync!). Instead, `workspace-sync-now` scans local `/home/workspace` in **~50ms** (`cd /home/workspace && find . ... -print0 | LC_ALL=C sort -z`), diffs against the previous manifest (`/run/workspace-sync/manifest`) with `LC_ALL=C comm -z -23` to unlink any locally deleted files/directories directly on `/mnt/gcs-workspace`, and runs 16 parallel `rsync -rltDO --inplace` workers that hit GCS FUSE's in-memory `stat-cache` in **~1.3 seconds** total.
   * **Skipping Redundant FUSE Metadata Calls (`-O --no-perms --no-owner --no-group`):** Because `/mnt/gcs-workspace` is mounted with `uid=1000;gid=1000;file-mode=0700;dir-mode=0700`, skipping redundant `chown`/`chmod` and directory mtime (`-O`) syscalls on FUSE avoids unnecessary metadata round-trips while preserving file modification timestamps (`-t`) and symlinks (`-l`).
   * **Exclusions:** Heavy regenerable directories (`node_modules`, `venv`, `.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.cache`, `.gemini`, `.npm`, `.tmp`, `lost+found`) stay strictly on fast local disk and are excluded from GCS sync.

### Recommended GCS FUSE `mount-options` for `/mnt/gcs-workspace`
Based on the [official Cloud Run Instances GCS Volume Mount documentation](https://docs.cloud.google.com/run/docs/configuring/instances/cloud-storage-volume-mounts):

```text
mount-options="uid=1000;gid=1000;file-mode=0700;dir-mode=0700;implicit-dirs;stat-cache-max-size-mb=-1;type-cache-max-size-mb=-1;metadata-cache-ttl-secs=120"
```
*(Note: Use semicolons `;` in `gcloud alpha run instances` CLI flags, or commas `,` in YAML `mountOptions`.)*

* `uid=1000;gid=1000`: Mounts the volume owned by `abc:abc` (`1000:1000` when `PUID=1000,PGID=1000` is set). By default, Cloud Run mounts GCS volumes as `root:root` (`0:0`), and `chown -R` on GCS FUSE is a no-op.
* `file-mode=0700;dir-mode=0700`: Preserves executable bits (`+x`) on scripts and CLI binaries in `.local/bin` (such as `claude`) across container restarts.
* `implicit-dirs`: Ensures GCS FUSE recognizes directories created by external tools (`gcloud storage cp/rsync`) that lack explicit directory placeholder objects.
* `stat-cache-max-size-mb=-1;type-cache-max-size-mb=-1`: Allows GCS FUSE's in-memory stat and type caches to grow as needed without evicting entries when workspaces exceed 20,000 files (~1,500 bytes/file for stat cache, ~200 bytes/file for type cache).
* `metadata-cache-ttl-secs=120`: Keeps file/directory metadata cached in memory for 120 seconds (longer than the 30-second `rsync` interval), so periodic `rsync` scans hit RAM instead of issuing GCS `Objects: list`/`stat` calls.

### Memory Accounting & Git Repository Maintenance
* **Container Memory Accounting:** In Cloud Run Instances, the container's writable local filesystem (`/home/workspace` on root overlay/`tmpfs`), GCS FUSE's in-memory metadata caches, and GCS FUSE write staging buffers (~64 MiB per open write stream) **all count toward the container's memory limit** (up to `32 GiB` max). Provision at least `16Gi`–`32Gi` of memory (`--memory=16Gi` or `--memory=32Gi`).
* **Keep `.git` Repositories Packed (`git gc`):** A repository with thousands of loose `.git/objects/xx/...` files creates thousands of separate GCS objects. Running `git gc` inside large repositories packs thousands of loose objects into a single `.pack` + `.idx` file pair (e.g., reducing `cycling-coach/.git` from `6,339` objects to `220` files), dramatically speeding up both startup hydration and background `rsync`.

---

## 4. Connecting via Terminal SSH, VS Code Remote-SSH, and Zed IDE

### A. Terminal SSH
To open an interactive shell directly from your terminal:
```bash
gcloud alpha run instances ssh vs-codium29-instance \
  --project=jasondel-cloudrun10 \
  --region=us-east4
```
*(Note: The Cloud Run SSH tunnel logs you into the container as `root`. To switch to the standard workstation user `abc` with Oh My Zsh, run `su - abc`.)*

### B. Configuring `~/.ssh/config` for Remote IDEs (VS Code & Zed)
Under the hood, `gcloud alpha run instances ssh` generates a short-lived SSH certificate (`~/.ssh/google_compute_engine_cert/<project>_<region>_instance_<name>-cert.pub`), establishes an IAM-authenticated WebSocket tunnel (`gcloud alpha run start-iap-tunnel`), and connects standard OpenSSH over that tunnel.

First, run the CLI SSH command once so `gcloud` generates your Google Compute Engine SSH keypair (`~/.ssh/google_compute_engine`) and certificate (`~/.ssh/google_compute_engine_cert/...`):
```bash
printf "exit\n" | gcloud alpha run instances ssh vs-codium29-instance \
  --project=jasondel-cloudrun10 \
  --region=us-east4
```

Then add the following verified host entry to your local `~/.ssh/config`:
```sshconfig
Host cloudrun-workstation
    HostName cloud-run-default
    User root
    IdentityFile ~/.ssh/google_compute_engine
    CertificateFile ~/.ssh/google_compute_engine_cert/jasondel-cloudrun10_us-east4_instance_vs-codium29-instance-cert.pub
    IdentitiesOnly yes
    CheckHostIP no
    HashKnownHosts no
    HostKeyAlias cloud-run-default
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/google_compute_known_hosts
    ProxyUseFdpass no
    ProxyCommand gcloud alpha run start-iap-tunnel --project_number=1076242320305 --project_id=jasondel-cloudrun10 --workload_type=instance --deployment_name=vs-codium29-instance --region=us-east4 --iap-tunnel-url-override=wss://us-east4.ssh.run.app/v4
```
*(Tip: If the short-lived SSH certificate expires later, simply run `gcloud alpha run instances ssh vs-codium29-instance --project=jasondel-cloudrun10 --region=us-east4` once to refresh it.)*

### C. Connecting with VS Code Remote-SSH
1. Install the **Remote - SSH** extension (`ms-vscode-remote.remote-ssh`) in VS Code.
2. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) -> **Remote-SSH: Connect to Host...**
3. Select **`cloudrun-workstation`**.
4. Open folder `/home/workspace`.

### D. Connecting with Zed IDE
Zed natively uses your system OpenSSH configuration and `ProxyCommand`:
1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) -> **`projects: open remote`** (or click **Open Remote...**).
2. Select **`cloudrun-workstation`** (or add host `cloudrun-workstation`).
3. Zed will automatically download `zed-remote-server` into `~/.zed_server` on the container and open `/home/workspace`.

---

## 5. Updating the Container Image & Installed CLI Tools

### Building a New Image in Artifact Registry
Workstation images are stored in Artifact Registry under:
```text
us-central1-docker.pkg.dev/jasondel-cloudrun10/workstation-images/user-1-<template-name>:latest
```
For example, `user-1-vs-codium30:latest` includes:
* **`rsync`** + `/usr/local/bin/workspace-sync-now` + S6 service `/custom-services.d/workspace-sync`
* **Antigravity CLI (`agy`)** at `/usr/local/bin/agy`
* **Claude Code (`claude`)** (hydrated into `/home/workspace/.local/bin/claude` or auto-installed on first launch)
* **OpenCode (`opencode`)** and **Codex (`codex`)** in `/opt/nvm/versions/node/v20.20.2/bin`

### Updating the Running Cloud Run Instance to a New Image
When updating the volume mount path from `/home/workspace` to `/mnt/gcs-workspace` (or updating the container image), use `gcloud alpha run instances update`:

```bash
gcloud alpha run instances update vs-codium29-instance \
  --image=us-central1-docker.pkg.dev/jasondel-cloudrun10/workstation-images/user-1-vs-codium30:latest \
  --project=jasondel-cloudrun10 \
  --region=us-east4 \
  --port=8000 \
  --set-env-vars="PUID=1000,PGID=1000,GOOGLE_CLOUD_PROJECT=jasondel-cloudrun10,WORKSPACE_SYNC_INTERVAL=30" \
  --remove-volume-mount=/home/workspace \
  --remove-volume=workspace \
  --add-volume=name=workspace,type=cloud-storage,bucket=jasondel-cloudrun10-workstation-workspace,mount-options="uid=1000;gid=1000;file-mode=0700;dir-mode=0700;implicit-dirs;stat-cache-max-size-mb=-1;type-cache-max-size-mb=-1;metadata-cache-ttl-secs=120" \
  --add-volume-mount=volume=workspace,mount-path=/mnt/gcs-workspace
```

### Migrating / Syncing Data from a GKE Workstation PVC to the GCS Bucket
You can copy files live from a running GKE workstation pod (such as `user27-0` in namespace `user-1`) directly to the Cloud Run Instance's GCS bucket without stopping the GKE pod:

```bash
kubectl exec -n user-1 user27-0 -- gcloud storage rsync -r \
  --exclude="\.gemini/.*|\.cache/.*|lost\+found/.*|libpod/.*|\.npm/.*|\.gsutil/.*|\.local/lib/.*|\.local/share/.*|\.tmp/.*|.*/\.gemini/.*|.*/\.cache/.*|.*node_modules/.*|.*venv/.*|.*\.venv/.*|.*__pycache__/.*" \
  /home/workspace gs://jasondel-cloudrun10-workstation-workspace
```

---

## 6. Troubleshooting

### A. `ERROR: (gcloud.alpha.run.start-iap-tunnel) Error while connecting [4003: 'failed to connect to backend'] (Failed to connect to port 22)`
* **Cause:** Cloud Run's SSH proxy (`wss://<region>.ssh.run.app`) rejects tunnel connections until the container finishes S6 initialization (`99-setup-user`) and binds its readiness port (`8000`). Immediately after `create` or `start`, `99-setup-user` spends ~45–90 seconds hydrating `/home/workspace` from `/mnt/gcs-workspace`.
* **Fix:** Check startup progress via `gcloud alpha run instances logs read vs-codium29-instance --region=us-east4 --project=jasondel-cloudrun10 --limit=25` and wait for `[workspace-init] Hydration complete.` and `[ls.io-init] done.` before running `gcloud alpha run instances ssh`.

### B. `Instance [...] could not be started: The service has encountered an internal error. Please try again later` (`ResourcesAvailable=False`)
* **Cause:** Stopped Cloud Run Instances created under older Alpha/Preview backend revisions can occasionally fail in Cloud Run's control plane when resuming cached container resources after backend rollouts.
* **Fix:** Because the root filesystem of a stopped instance is already ephemeral and persistent workspace files live in `gs://jasondel-cloudrun10-workstation-workspace`, safely delete and recreate the instance with the same name and GCS volume mount (Section 2). All workspace data hydrates back automatically and the instance URL remains identical.

### C. `unrecognized arguments: --enable-ssh`
* **Cause:** Starting in Google Cloud SDK `591.0.0+`, Cloud Run Instances sets `run.googleapis.com/ssh-enabled: 'true'` by default and removed the `--enable-ssh` CLI flag.
* **Fix:** Omit `--enable-ssh` from `gcloud alpha run instances create` and `update` commands.
