import { AppBar, Toolbar, Typography, Container, Button, Box, Paper, Snackbar, Alert, LinearProgress, Chip, CircularProgress, Divider, Card, CardContent, CardActions, IconButton, Tabs, Tab, List, ListItem, ListItemText, Grid, ListItemButton, TextField, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import { useState, useEffect } from 'react';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WorkstationEditor from './components/WorkstationEditor';
import ConnectionInstructions from './components/ConnectionInstructions';
import NewWorkstationDialog from './components/NewWorkstationDialog';
import EditWorkstationDialog from './components/EditWorkstationDialog';
import NewServiceDialog from './components/NewServiceDialog';
import EditServiceDialog from './components/EditServiceDialog';
import type { ImageMetadata } from './components/NewWorkstationDialog';
import type { WorkstationConfig } from './components/EditWorkstationDialog';
import type { CatalogEntry } from './components/NewServiceDialog';
import type { ServiceConfig } from './components/EditServiceDialog';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

interface WorkstationStatus {
  name: string;
  user_ns: string;
  status: string;
  image?: string;
  ports?: number[];
  cpu?: string;
  memory?: string;
  disk_size?: string;
  gpu?: string | null;
  env_vars?: Record<string, string>;
  pod_name?: string;
  pod_ready: boolean;
  message?: string;
}

interface WorkstationListResponse {
  workstations: WorkstationStatus[];
  count: number;
}

interface ServiceStatusInfo {
  name: string;
  user_ns: string;
  status: string;
  image?: string;
  service_type?: string;
  ports?: number[];
  cpu?: string;
  memory?: string;
  disk_size?: string;
  env_vars?: Record<string, string>;
  data_mount_path?: string;
  health_check_command?: string[];
  pod_name?: string;
  pod_ready: boolean;
  message?: string;
  connect_hint?: string;
}

interface ServiceListResponse {
  services: ServiceStatusInfo[];
  count: number;
}

interface AppConfig {
  project_id: string;
  region: string;
  account: string;
}

interface ClusterNode {
  name: string;
  machine_type: string;
  zone: string;
  cpu: string;
  memory: string;
  gpu: string;
  ready: boolean;
}

function App() {
  const [workstations, setWorkstations] = useState<WorkstationStatus[]>([]);
  const [availableImages, setAvailableImages] = useState<ImageMetadata[]>([]);
  const [clusterStatus, setClusterStatus] = useState<string | null>(null);
  const [clusterMessage, setClusterMessage] = useState<string | null>(null);
  const [appConfig, setAppConfig] = useState<AppConfig | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info', msg: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [isNewDialogOpen, setIsNewDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingWorkstation, setEditingWorkstation] = useState<WorkstationConfig | null>(null);

  // Service state
  const [services, setServices] = useState<ServiceStatusInfo[]>([]);
  const [serviceCatalog, setServiceCatalog] = useState<CatalogEntry[]>([]);
  const [isNewServiceDialogOpen, setIsNewServiceDialogOpen] = useState(false);
  const [isEditServiceDialogOpen, setIsEditServiceDialogOpen] = useState(false);
  const [editingService, setEditingService] = useState<ServiceConfig | null>(null);

  // States for viewing/editing existing image Dockerfiles
  const [selectedImageName, setSelectedImageName] = useState<string | undefined>(undefined);
  const [selectedDockerfile, setSelectedDockerfile] = useState<string | undefined>(undefined);

  // Infrastructure tab state
  const [clusterNodes, setClusterNodes] = useState<ClusterNode[]>([]);
  const [adcExists, setAdcExists] = useState(false);
  const [adcJson, setAdcJson] = useState('');

  const user_ns = "user-1";

  const fetchWorkstations = async () => {
    try {
      const response = await fetch(`/api/workstations/${user_ns}/list`, {
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' },
        cache: 'no-store'
      });
      if (response.ok) {
        const data: WorkstationListResponse = await response.json();
        setWorkstations(data.workstations);
      } else {
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        setNotification({ type: 'error', msg: `Failed to fetch workstations: ${data.detail || response.statusText}` });
      }
    } catch (error) {
      console.error("Failed to fetch workstations:", error);
      setNotification({ type: 'error', msg: `Failed to connect to backend: ${error}` });
    }
  };

  const fetchImages = async () => {
    try {
      const response = await fetch('/api/workstations/images', {
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' },
        cache: 'no-store'
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableImages(data);
      } else {
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        setNotification({ type: 'error', msg: `Failed to fetch images: ${data.detail || response.statusText}` });
      }
    } catch (error) {
      console.error("Failed to fetch images:", error);
      setNotification({ type: 'error', msg: `Failed to connect to backend: ${error}` });
    }
  };

  const fetchClusterStatus = async () => {
    try {
      const response = await fetch('/api/workstations/cluster-status', {
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' },
        cache: 'no-store'
      });
      if (response.ok) {
        const data = await response.json();
        setClusterStatus(data.status);
        setClusterMessage(data.message || null);
      } else {
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        setClusterStatus("ERROR");
        setClusterMessage(data.detail || `HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error("Failed to fetch cluster status:", error);
      setClusterStatus("OFFLINE");
      setClusterMessage(`Failed to connect to backend: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/workstations/config', {
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' },
        cache: 'no-store'
      });
      if (response.ok) {
        const data = await response.json();
        setAppConfig(data);
      } else {
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        setNotification({ type: 'error', msg: `Failed to fetch config: ${data.detail || response.statusText}` });
      }
    } catch (error) {
      console.error("Failed to fetch config:", error);
      setNotification({ type: 'error', msg: `Failed to connect to backend: ${error}` });
    }
  };

  const fetchNodes = async () => {
    try {
      const response = await fetch('/api/workstations/nodes', {
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' },
        cache: 'no-store'
      });
      if (response.ok) {
        const data = await response.json();
        setClusterNodes(data.nodes || []);
      } else {
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        setNotification({ type: 'error', msg: `Failed to fetch nodes: ${data.detail || response.statusText}` });
      }
    } catch (error) {
      console.error("Failed to fetch nodes:", error);
      setNotification({ type: 'error', msg: `Failed to connect to backend: ${error}` });
    }
  };

  const fetchAdcStatus = async () => {
    try {
      const response = await fetch(`/api/workstations/${user_ns}/adc-secret`);
      if (response.ok) {
        const data = await response.json();
        setAdcExists(data.exists);
      } else {
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        setNotification({ type: 'error', msg: `Failed to fetch ADC status: ${data.detail || response.statusText}` });
      }
    } catch (error) {
      console.error("Failed to fetch ADC status:", error);
      setNotification({ type: 'error', msg: `Failed to connect to backend: ${error}` });
    }
  };

  const fetchServices = async () => {
    try {
      const response = await fetch(`/api/services/${user_ns}/list`, {
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' },
        cache: 'no-store'
      });
      if (response.ok) {
        const data: ServiceListResponse = await response.json();
        setServices(data.services);
      }
    } catch (error) {
      console.error("Failed to fetch services:", error);
    }
  };

  const fetchServiceCatalog = async () => {
    try {
      const response = await fetch('/api/services/catalog');
      if (response.ok) {
        const data = await response.json();
        setServiceCatalog(data);
      }
    } catch (error) {
      console.error("Failed to fetch service catalog:", error);
    }
  };

  const fetchAll = () => {
    fetchWorkstations();
    fetchImages();
    fetchClusterStatus();
    fetchConfig();
    fetchNodes();
    fetchAdcStatus();
    fetchServices();
    fetchServiceCatalog();
  };

  const TERMINAL_BUILD_STATUSES = ['SUCCESS', 'FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'];

  const hasActiveBuilds = availableImages.some(
    img => img.build_status && !TERMINAL_BUILD_STATUSES.includes(img.build_status)
  );

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => {
      fetchWorkstations();
      fetchServices();
      fetchClusterStatus();
      fetchNodes();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll images when there are active builds
  useEffect(() => {
    if (!hasActiveBuilds) return;
    const interval = setInterval(() => {
      fetchImages();
    }, 5000);
    return () => clearInterval(interval);
  }, [hasActiveBuilds]);

  const handleAction = async (action: 'start' | 'stop' | 'init' | 'snapshot' | 'enable-gke' | 'delete' | 'delete-infrastructure' | 'stop-all', name: string) => {
    let url = `/api/workstations/${user_ns}/${action}/${name}`;
    if (action === 'init') url = '/api/workstations/init';
    if (action === 'enable-gke') url = '/api/workstations/enable-gke';
    if (action === 'delete-infrastructure') url = '/api/workstations/delete-infrastructure';
    if (action === 'stop-all') url = '/api/workstations/stop-all';

    setNotification({ type: 'info', msg: `${action.replace('-', ' ').toUpperCase()} initiated...` });
    try {
      const options: RequestInit = { method: 'POST' };
      const response = await fetch(url, options);
      const data = await response.json();
      if (response.ok) {
        setNotification({ type: 'success', msg: data.message || 'Action successful' });
      } else {
        setNotification({ type: 'error', msg: `Failed: ${data.detail || data.message}` });
      }
      fetchWorkstations();
      fetchClusterStatus();
    } catch (error) {
      console.error(`Failed to ${action}:`, error);
      setNotification({ type: 'error', msg: `Error: ${error}` });
    }
  };

  const handleCreateWorkstation = async (name: string, imageUri: string, ports: number[], cpu: string, memory: string, diskSize: string, gpu: string | null, envVars: Record<string, string> = {}) => {
    setNotification({ type: 'info', msg: `Creating workstation ${name}...` });
    try {
      const saveResponse = await fetch(`/api/workstations/${user_ns}/save-config/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageUri, ports, cpu, memory, disk_size: diskSize, gpu, env_vars: envVars }),
      });

      if (saveResponse.ok) {
        handleAction('start', name);
      } else {
        const data = await saveResponse.json();
        setNotification({ type: 'error', msg: `Failed to save config: ${data.detail}` });
      }
    } catch (error) {
      setNotification({ type: 'error', msg: `Error creating workstation: ${error}` });
    }
  };

  const handleUpdateWorkstation = async (name: string, ports: number[], cpu: string, memory: string, diskSize: string, gpu: string | null, envVars: Record<string, string> = {}, image?: string) => {
    setNotification({ type: 'info', msg: `Updating configuration for ${name}...` });
    try {
      const body: Record<string, unknown> = { ports, cpu, memory, disk_size: diskSize, gpu, env_vars: envVars };
      if (image) body.image = image;
      const response = await fetch(`/api/workstations/${user_ns}/save-config/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (response.ok) {
        setNotification({ type: 'success', msg: `Configuration for ${name} updated.` });
        fetchWorkstations();
      } else {
        const data = await response.json();
        setNotification({ type: 'error', msg: `Failed to update config: ${data.detail}` });
      }
    } catch (error) {
      setNotification({ type: 'error', msg: `Error updating workstation: ${error}` });
    }
  };

  const handleSaveAdc = async () => {
    if (!adcJson.trim()) {
      setNotification({ type: 'error', msg: 'Please paste your ADC JSON credentials.' });
      return;
    }
    setNotification({ type: 'info', msg: 'Saving GCP credentials...' });
    try {
      const response = await fetch(`/api/workstations/${user_ns}/adc-secret`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ adc_json: adcJson }),
      });
      if (response.ok) {
        setNotification({ type: 'success', msg: 'GCP credentials saved successfully.' });
        setAdcExists(true);
        setAdcJson('');
      } else {
        const data = await response.json();
        setNotification({ type: 'error', msg: `Failed to save credentials: ${data.detail}` });
      }
    } catch (error) {
      setNotification({ type: 'error', msg: `Error saving credentials: ${error}` });
    }
  };

  // ── Service handlers ──────────────────────────────────────────────────

  const handleCreateService = async (name: string, serviceType: string, image: string, ports: number[], cpu: string, memory: string, diskSize: string, envVars: Record<string, string>, dataMountPath: string = '/data', healthCheckCommand: string[] = []) => {
    setNotification({ type: 'info', msg: `Creating service ${name}...` });
    try {
      const saveResponse = await fetch(`/api/services/${user_ns}/save-config/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image, service_type: serviceType, ports, cpu, memory, disk_size: diskSize, env_vars: envVars, data_mount_path: dataMountPath, health_check_command: healthCheckCommand }),
      });
      if (saveResponse.ok) {
        const startResponse = await fetch(`/api/services/${user_ns}/start/${name}`, { method: 'POST' });
        const data = await startResponse.json();
        if (startResponse.ok) {
          setNotification({ type: 'success', msg: data.message || `Service ${name} started` });
        } else {
          setNotification({ type: 'error', msg: `Failed to start: ${data.detail}` });
        }
        fetchServices();
      } else {
        const data = await saveResponse.json();
        setNotification({ type: 'error', msg: `Failed to save config: ${data.detail}` });
      }
    } catch (error) {
      setNotification({ type: 'error', msg: `Error creating service: ${error}` });
    }
  };

  const handleServiceAction = async (action: 'start' | 'stop' | 'delete', name: string) => {
    const url = `/api/services/${user_ns}/${action}/${name}`;
    setNotification({ type: 'info', msg: `${action.toUpperCase()} service ${name}...` });
    try {
      const response = await fetch(url, { method: 'POST' });
      const data = await response.json();
      if (response.ok) {
        setNotification({ type: 'success', msg: data.message || 'Action successful' });
      } else {
        setNotification({ type: 'error', msg: `Failed: ${data.detail || data.message}` });
      }
      fetchServices();
    } catch (error) {
      setNotification({ type: 'error', msg: `Error: ${error}` });
    }
  };

  const handleUpdateService = async (name: string, ports: number[], cpu: string, memory: string, diskSize: string, envVars: Record<string, string>, dataMountPath: string = '/data', healthCheckCommand: string[] = []) => {
    setNotification({ type: 'info', msg: `Updating service ${name}...` });
    try {
      // Get existing config to preserve service_type and image
      const existingSvc = services.find(s => s.name === name);
      const response = await fetch(`/api/services/${user_ns}/save-config/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: existingSvc?.image,
          service_type: existingSvc?.service_type || 'custom',
          ports, cpu, memory, disk_size: diskSize, env_vars: envVars,
          data_mount_path: dataMountPath, health_check_command: healthCheckCommand,
        }),
      });
      if (response.ok) {
        setNotification({ type: 'success', msg: `Service ${name} config updated.` });
        fetchServices();
      } else {
        const data = await response.json();
        setNotification({ type: 'error', msg: `Failed: ${data.detail}` });
      }
    } catch (error) {
      setNotification({ type: 'error', msg: `Error: ${error}` });
    }
  };

  const handleDeleteImage = async (e: React.MouseEvent, img: ImageMetadata) => {
    e.stopPropagation(); // prevent row click from opening dockerfile
    const name = img.tags && img.tags.length > 0 ? img.tags[0] : img.uri.split('/').pop()?.split('@')[0];
    if (!name) return;

    if (!window.confirm(`Are you sure you want to delete the image '${name}' and its configuration?`)) {
      return;
    }

    setNotification({ type: 'info', msg: `Deleting image ${name}...` });
    try {
      const response = await fetch(`/api/workstations/${user_ns}/images/${name}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        setNotification({ type: 'success', msg: `Image ${name} deleted successfully.` });
        if (selectedImageName === name) {
          setSelectedImageName(undefined);
          setSelectedDockerfile(undefined);
        }
        fetchImages();
      } else {
        const data = await response.json();
        setNotification({ type: 'error', msg: `Failed to delete image: ${data.detail || data.message}` });
      }
    } catch (error) {
      console.error('Failed to delete image:', error);
      setNotification({ type: 'error', msg: 'Failed to delete image.' });
    }
  };

  const handleImageClick = async (img: ImageMetadata) => {
    // Extract name from URI or tags
    const name = img.tags && img.tags.length > 0 ? img.tags[0] : img.uri.split('/').pop()?.split('@')[0];
    if (!name) return;

    setNotification({ type: 'info', msg: `Loading Dockerfile for ${name}...` });
    try {
      const response = await fetch(`/api/workstations/${user_ns}/images/${name}/dockerfile`);
      if (response.ok) {
        const data = await response.json();
        setSelectedImageName(name);
        setSelectedDockerfile(data.dockerfile);
        setNotification({ type: 'success', msg: 'Dockerfile loaded into builder.' });
      } else {
        const data = await response.json();
        setNotification({ type: 'error', msg: `Failed to load: ${data.detail}` });
      }
    } catch (error) {
      setNotification({ type: 'error', msg: `Error fetching dockerfile: ${error}` });
    }
  };

  const isClusterReady = clusterStatus === 'RUNNING';
  const isClusterProvisioning = clusterStatus === 'PROVISIONING' || clusterStatus === 'RECONCILING';
  const noCluster = clusterStatus === 'NOT_FOUND';
  const hasError = clusterStatus === 'ERROR';
  const isOffline = clusterStatus === 'OFFLINE' || clusterStatus === 'UNKNOWN';

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <AppBar position="static" color="primary" elevation={0}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Workstation Lite
          </Typography>
          {appConfig && (
            <Box sx={{ textAlign: 'right', mr: 2 }}>
              <Typography variant="caption" display="block" sx={{ opacity: 0.8 }}>
                Project: {appConfig.project_id}
              </Typography>
              <Typography variant="caption" display="block" sx={{ opacity: 0.8 }}>
                Account: {appConfig.account}
              </Typography>
            </Box>
          )}
          <IconButton color="inherit" onClick={fetchAll}>
            <RefreshIcon />
          </IconButton>
          <Button color="inherit">Login</Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl">
        <Box sx={{ mt: 2 }}>
          {isClusterProvisioning && (
            <Box sx={{ mb: 4 }}>
              <Alert severity="info" variant="filled" sx={{ mb: 1 }}>
                GKE Cluster is currently **{clusterStatus}**. This process usually takes 8-10 minutes.
                Please wait until the cluster is RUNNING to start your workstation.
              </Alert>
              <LinearProgress color="info" />
            </Box>
          )}

          {hasError && (
            <Alert
              severity="error"
              variant="filled"
              sx={{ mb: 4 }}
              action={
                <Button color="inherit" size="small" onClick={() => handleAction('enable-gke', '')}>
                  Enable GKE API
                </Button>
              }
            >
              {clusterMessage || "GKE API or Cluster error detected."}
            </Alert>
          )}

          {isOffline && (
            <Alert severity="error" variant="filled" sx={{ mb: 4 }}>
              Unable to connect to backend or cluster. {clusterMessage || 'Check that the backend server is running and your GCP credentials are valid.'}
            </Alert>
          )}

          {noCluster && (
            <Alert severity="warning" sx={{ mb: 4 }}>
              No infrastructure detected. Click "Initialize Project" to provision your GKE Autopilot cluster.
            </Alert>
          )}

          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
              <Tab label="Workstations" />
              <Tab label="Services" />
              <Tab label="Image Templates" />
              <Tab label="Infrastructure" />
            </Tabs>
          </Box>

          {tabValue === 0 && (
            <Box>
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h5">Active Workstations ({workstations.length})</Typography>
                <Button
                  variant="contained"
                  onClick={() => setIsNewDialogOpen(true)}
                  disabled={!isClusterReady}
                >
                  New Workstation
                </Button>
              </Box>

              <Grid container spacing={2}>
                {workstations.length === 0 && !loading && (
                  <Grid size={12}>
                    <Paper sx={{ p: 4, textAlign: 'center', border: '2px dashed #ccc', bgcolor: 'transparent' }}>
                      <Typography color="text.secondary">No workstations created yet.</Typography>
                    </Paper>
                  </Grid>
                )}
                {workstations.map((ws) => (
                  <Grid size={{ xs: 12, md: 6, lg: 4 }} key={ws.name}>
                    <Card elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                      <CardContent sx={{ flexGrow: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="h6" component="div">{ws.name}</Typography>
                          <Box>
                            <Chip
                              label={ws.status}
                              size="small"
                              color={
                                ws.status === 'RUNNING' ? 'success' :
                                ws.status === 'ERROR' ? 'error' :
                                ws.status === 'STOPPED' ? 'default' : 'info'
                              }
                              sx={{ mr: 1 }}
                            />
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                if (window.confirm(`DANGER: Are you sure you want to delete workstation "${ws.name}"? This will permanently destroy the environment and ALL DATA stored in its home directory.`)) {
                                  handleAction('delete', ws.name);
                                }
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        </Box>

                        {ws.status === 'PROVISIONING' && (
                          <LinearProgress sx={{ mb: 1 }} />
                        )}

                        {ws.status === 'ERROR' && ws.message && (
                          <Alert severity="error" sx={{ mb: 1, fontSize: '0.75rem' }}>
                            {ws.message}
                          </Alert>
                        )}

                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontFamily: 'monospace' }}>
                          Image: {ws.image?.split('/').pop()?.split('@')[0]}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontFamily: 'monospace' }}>
                          CPU: {ws.cpu || '500m'} | Mem: {ws.memory || '2Gi'} | Disk: {ws.disk_size || '10Gi'}
                        </Typography>
                        {ws.gpu && (
                          <Chip label={`GPU: ${ws.gpu.toUpperCase()}`} size="small" color="secondary" sx={{ mb: 0.5 }} />
                        )}
                        {ws.ports && ws.ports.length > 0 && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontFamily: 'monospace' }}>
                            Ports: {ws.ports.join(', ')}
                          </Typography>
                        )}
                        {ws.env_vars && Object.keys(ws.env_vars).length > 0 && (
                          <Accordion disableGutters elevation={0} sx={{ mt: 1, '&:before': { display: 'none' }, bgcolor: 'transparent' }}>
                            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ p: 0, minHeight: 'auto', '& .MuiAccordionSummary-content': { m: 0 } }}>
                              <Typography variant="caption" color="text.secondary">
                                Environment Variables ({Object.keys(ws.env_vars).length})
                              </Typography>
                            </AccordionSummary>
                            <AccordionDetails sx={{ p: 0, pt: 0.5 }}>
                              {Object.entries(ws.env_vars).map(([key, value]) => (
                                <Typography key={key} variant="caption" color="text.secondary" sx={{ display: 'block', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                                  {key}={value}
                                </Typography>
                              ))}
                            </AccordionDetails>
                          </Accordion>
                        )}
                        {ws.pod_name && (
                          <Chip label={`Pod: ${ws.pod_name}`} size="small" variant="outlined" sx={{ mt: 1 }} color={ws.pod_ready ? "success" : "warning"} />
                        )}

                        {ws.status === 'RUNNING' && (
                          <ConnectionInstructions userNs={ws.user_ns} workstationName={ws.name} ports={ws.ports} />
                        )}
                      </CardContent>
                      <Divider />
                      <CardActions sx={{ justifyContent: 'flex-end', p: 2 }}>
                        {ws.status === 'STOPPED' && (
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => {
                              setEditingWorkstation({
                                name: ws.name,
                                image: ws.image,
                                ports: ws.ports || [],
                                cpu: ws.cpu || '500m',
                                memory: ws.memory || '2Gi',
                                disk_size: ws.disk_size || '10Gi',
                                gpu: ws.gpu || null,
                                env_vars: ws.env_vars || {},
                              });
                              setIsEditDialogOpen(true);
                            }}
                          >
                            Edit Config
                          </Button>
                        )}
                        <Button
                          size="small"
                          variant="outlined"
                          color="error"
                          onClick={() => handleAction('stop', ws.name)}
                          disabled={ws.status === 'STOPPED'}
                        >
                          Stop
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => handleAction('start', ws.name)}
                          disabled={ws.status === 'RUNNING' || ws.status === 'PROVISIONING'}
                        >
                          Start
                        </Button>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          {tabValue === 1 && (
            <Box>
              <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h5">Services ({services.length})</Typography>
                <Button
                  variant="contained"
                  onClick={() => setIsNewServiceDialogOpen(true)}
                  disabled={!isClusterReady}
                >
                  New Service
                </Button>
              </Box>

              <Grid container spacing={2}>
                {services.length === 0 && !loading && (
                  <Grid size={12}>
                    <Paper sx={{ p: 4, textAlign: 'center', border: '2px dashed #ccc', bgcolor: 'transparent' }}>
                      <Typography color="text.secondary">No services created yet. Add a database, cache, or queue.</Typography>
                    </Paper>
                  </Grid>
                )}
                {services.map((svc) => {
                  const k8sName = `svc-${svc.name}`;
                  const connectStr = svc.ports && svc.ports.length > 0
                    ? `${k8sName}:${svc.ports[0]}`
                    : null;
                  const currentHost = window.location.host;
                  const protocol = window.location.protocol;
                  const connectUrl = `${protocol}//${currentHost}/api/services/${user_ns}/connect/${svc.name}`;
                  const execUrl = `${protocol}//${currentHost}/api/services/${user_ns}/exec/${svc.name}`;

                  return (
                    <Grid size={{ xs: 12, md: 6, lg: 4 }} key={svc.name}>
                      <Card elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                        <CardContent sx={{ flexGrow: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="h6">{svc.name}</Typography>
                            <Box>
                              <Chip
                                label={svc.status}
                                size="small"
                                color={
                                  svc.status === 'RUNNING' ? 'success' :
                                  svc.status === 'ERROR' ? 'error' :
                                  svc.status === 'STOPPED' ? 'default' : 'info'
                                }
                                sx={{ mr: 1 }}
                              />
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => {
                                  if (window.confirm(`Delete service "${svc.name}"? This will destroy all data.`)) {
                                    handleServiceAction('delete', svc.name);
                                  }
                                }}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </Box>

                          {svc.status === 'PROVISIONING' && <LinearProgress sx={{ mb: 1 }} />}

                          {svc.status === 'ERROR' && svc.message && (
                            <Alert severity="error" sx={{ mb: 1, fontSize: '0.75rem' }}>{svc.message}</Alert>
                          )}

                          <Chip label={svc.service_type || 'custom'} size="small" variant="outlined" sx={{ mb: 1 }} />

                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontFamily: 'monospace' }}>
                            Image: {svc.image}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontFamily: 'monospace' }}>
                            CPU: {svc.cpu || '250m'} | Mem: {svc.memory || '512Mi'} | Disk: {svc.disk_size || '5Gi'}
                          </Typography>

                          {connectStr && svc.status === 'RUNNING' && (
                            <Paper sx={{ p: 1.5, mt: 1, bgcolor: '#f5f5f5' }} elevation={1}>
                              <Typography variant="caption" color="text.secondary">Connect from workstation:</Typography>
                              <Box sx={{ p: 1, bgcolor: '#2d2d2d', color: '#fff', fontFamily: 'monospace', borderRadius: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 0.5 }}>
                                <code style={{ fontSize: '0.8rem' }}>{connectStr}</code>
                                <Tooltip title="Copy">
                                  <IconButton size="small" onClick={() => navigator.clipboard.writeText(connectStr)} sx={{ color: '#fff', ml: 1 }}>
                                    <ContentCopyIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </Box>
                            </Paper>
                          )}

                          {svc.env_vars && Object.keys(svc.env_vars).length > 0 && (
                            <Accordion disableGutters elevation={0} sx={{ mt: 1, '&:before': { display: 'none' }, bgcolor: 'transparent' }}>
                              <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ p: 0, minHeight: 'auto', '& .MuiAccordionSummary-content': { m: 0 } }}>
                                <Typography variant="caption" color="text.secondary">
                                  Environment Variables ({Object.keys(svc.env_vars).length})
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails sx={{ p: 0, pt: 0.5 }}>
                                {Object.entries(svc.env_vars).map(([key, value]) => (
                                  <Typography key={key} variant="caption" color="text.secondary" sx={{ display: 'block', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                                    {key}={value}
                                  </Typography>
                                ))}
                              </AccordionDetails>
                            </Accordion>
                          )}

                          {svc.status === 'RUNNING' && (
                            <Accordion disableGutters elevation={0} sx={{ mt: 1, '&:before': { display: 'none' }, bgcolor: 'transparent' }}>
                              <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ p: 0, minHeight: 'auto', '& .MuiAccordionSummary-content': { m: 0 } }}>
                                <Typography variant="caption" color="text.secondary">Debug Connection (one-liner)</Typography>
                              </AccordionSummary>
                              <AccordionDetails sx={{ p: 0, pt: 0.5 }}>
                                <Typography variant="caption" color="text.secondary">Port-forward:</Typography>
                                <Box sx={{ p: 0.5, bgcolor: '#2d2d2d', color: '#fff', fontFamily: 'monospace', borderRadius: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 0.5, mb: 1 }}>
                                  <code style={{ fontSize: '0.7rem', wordBreak: 'break-all' }}>/bin/bash -c "$(curl -fsSL {connectUrl})"</code>
                                  <Tooltip title="Copy">
                                    <IconButton size="small" onClick={() => navigator.clipboard.writeText(`/bin/bash -c "$(curl -fsSL ${connectUrl})"`)} sx={{ color: '#fff', ml: 1 }}>
                                      <ContentCopyIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Box>
                                <Typography variant="caption" color="text.secondary">Debug shell:</Typography>
                                <Box sx={{ p: 0.5, bgcolor: '#2d2d2d', color: '#fff', fontFamily: 'monospace', borderRadius: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 0.5 }}>
                                  <code style={{ fontSize: '0.7rem', wordBreak: 'break-all' }}>/bin/bash -c "$(curl -fsSL {execUrl})"</code>
                                  <Tooltip title="Copy">
                                    <IconButton size="small" onClick={() => navigator.clipboard.writeText(`/bin/bash -c "$(curl -fsSL ${execUrl})"`)} sx={{ color: '#fff', ml: 1 }}>
                                      <ContentCopyIcon fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Box>
                              </AccordionDetails>
                            </Accordion>
                          )}
                        </CardContent>
                        <Divider />
                        <CardActions sx={{ justifyContent: 'flex-end', p: 2 }}>
                          {svc.status === 'STOPPED' && (
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => {
                                setEditingService({
                                  name: svc.name,
                                  image: svc.image,
                                  service_type: svc.service_type || 'custom',
                                  ports: svc.ports || [],
                                  cpu: svc.cpu || '250m',
                                  memory: svc.memory || '512Mi',
                                  disk_size: svc.disk_size || '5Gi',
                                  env_vars: svc.env_vars || {},
                                  data_mount_path: svc.data_mount_path || '/data',
                                  health_check_command: svc.health_check_command || [],
                                });
                                setIsEditServiceDialogOpen(true);
                              }}
                            >
                              Edit Config
                            </Button>
                          )}
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            onClick={() => handleServiceAction('stop', svc.name)}
                            disabled={svc.status === 'STOPPED'}
                          >
                            Stop
                          </Button>
                          <Button
                            size="small"
                            variant="contained"
                            onClick={() => handleServiceAction('start', svc.name)}
                            disabled={svc.status === 'RUNNING' || svc.status === 'PROVISIONING'}
                          >
                            Start
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            </Box>
          )}

          {tabValue === 2 && (
            <Box>
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, lg: 4 }}>
                  <Typography variant="h5" gutterBottom>
                    Built Images
                  </Typography>
                  <Paper sx={{ p: 0 }}>
                    <List>
                      {availableImages.length === 0 && (
                        <ListItem>
                          <ListItemText primary="No images built yet." secondary="Build your first image configuration below." />
                        </ListItem>
                      )}
                      {availableImages.map((img) => {
                        const isBuilding = img.build_status && !TERMINAL_BUILD_STATUSES.includes(img.build_status);
                        const isBuildFailed = img.build_status && ['FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'].includes(img.build_status);

                        return (
                          <ListItem
                            key={img.tags?.[0] || img.uri || Math.random().toString()}
                            disablePadding
                            secondaryAction={
                              <IconButton edge="end" aria-label="delete" onClick={(e) => handleDeleteImage(e, img)}>
                                <DeleteIcon />
                              </IconButton>
                            }
                          >
                            <ListItemButton divider onClick={() => handleImageClick(img)}>
                              <ListItemText
                                primary={
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <span>{img.tags && img.tags.length > 0 ? img.tags[0] : "Untitled Image"}</span>
                                    {isBuilding && (
                                      <Tooltip title={`Building... (${img.build_status})`}>
                                        <Chip
                                          icon={<CircularProgress size={12} />}
                                          label={img.build_status}
                                          size="small"
                                          color="info"
                                          variant="outlined"
                                          sx={{ height: 22, '& .MuiChip-label': { px: 0.5, fontSize: '0.7rem' } }}
                                        />
                                      </Tooltip>
                                    )}
                                    {isBuildFailed && (
                                      <Tooltip title={`Build failed: ${img.build_status}`}>
                                        <Chip
                                          icon={<ErrorOutlineIcon sx={{ fontSize: 14 }} />}
                                          label="FAILED"
                                          size="small"
                                          color="error"
                                          variant="outlined"
                                          sx={{ height: 22, '& .MuiChip-label': { px: 0.5, fontSize: '0.7rem' } }}
                                        />
                                      </Tooltip>
                                    )}
                                  </Box>
                                }
                                secondary={img.uri ? img.uri.split('/').pop()?.split('@')[0] : "Draft Recipe (Unbuilt)"}
                              />
                            </ListItemButton>
                          </ListItem>
                        );
                      })}
                    </List>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, lg: 8 }}>
                  <Typography variant="h5" gutterBottom>
                    Image Builder
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Define a custom Dockerfile to create a reusable environment template. Click a built image to view its source.
                  </Typography>
                  <WorkstationEditor
                    initialDockerfile={selectedDockerfile}
                    initialName={selectedImageName}
                    onBuildSuccess={fetchImages}
                    onBuildStart={fetchImages}
                    initialBuildId={
                      selectedImageName
                        ? availableImages.find(img => img.tags?.[0] === selectedImageName)?.build_id ?? undefined
                        : undefined
                    }
                    initialBuildStatus={
                      selectedImageName
                        ? availableImages.find(img => img.tags?.[0] === selectedImageName)?.build_status ?? undefined
                        : undefined
                    }
                  />
                </Grid>
              </Grid>
            </Box>
          )}

          {tabValue === 3 && (
            <Box>
              <Typography variant="h5" gutterBottom>Infrastructure Management</Typography>

              {/* Cluster Status */}
              <Paper sx={{ p: 3, mt: 2 }}>
                <Grid container spacing={3} alignItems="center">
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Typography variant="subtitle1" gutterBottom>Cluster Status</Typography>
                    <Chip
                      label={clusterStatus || 'OFFLINE'}
                      color={isClusterReady ? 'success' : isClusterProvisioning ? 'info' : 'default'}
                    />
                    <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                      Region: {appConfig?.region || 'Unknown'}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }} sx={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: 1, alignItems: 'flex-end' }}>
                    <Button
                      variant="contained"
                      onClick={() => handleAction('init', '')}
                      disabled={isClusterReady || isClusterProvisioning}
                      fullWidth
                      sx={{ maxWidth: 300 }}
                    >
                      {isClusterProvisioning ? 'Provisioning...' : 'Initialize Infrastructure'}
                    </Button>
                    <Button
                      variant="outlined"
                      color="warning"
                      onClick={() => {
                        if (window.confirm('Are you sure you want to stop all active workstations?')) {
                          handleAction('stop-all', '');
                        }
                      }}
                      disabled={!isClusterReady}
                      fullWidth
                      sx={{ maxWidth: 300 }}
                    >
                      Stop All Workstations
                    </Button>
                    <Button
                      variant="outlined"
                      color="error"
                      onClick={() => {
                        if (window.confirm('WARNING: This will permanently delete your GKE Autopilot cluster and all data not backed up. Are you sure?')) {
                          handleAction('delete-infrastructure', '');
                        }
                      }}
                      disabled={clusterStatus === 'NOT_FOUND' || clusterStatus === 'DELETING'}
                      fullWidth
                      sx={{ maxWidth: 300 }}
                    >
                      {clusterStatus === 'DELETING' ? 'Deleting...' : 'Delete GKE Infrastructure'}
                    </Button>
                  </Grid>
                </Grid>
              </Paper>

              {/* GCP Credentials */}
              <Paper sx={{ p: 3, mt: 3 }}>
                <Typography variant="subtitle1" gutterBottom>GCP Credentials (ADC)</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Upload Application Default Credentials JSON to inject into workstation pods. This sets GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT automatically.
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Typography variant="body2">Status:</Typography>
                  <Chip
                    label={adcExists ? 'Configured' : 'Not Configured'}
                    color={adcExists ? 'success' : 'default'}
                    size="small"
                  />
                </Box>
                <TextField
                  label="ADC JSON"
                  placeholder='Paste your application_default_credentials.json contents here'
                  multiline
                  rows={4}
                  fullWidth
                  value={adcJson}
                  onChange={(e) => setAdcJson(e.target.value)}
                  sx={{ mb: 2, fontFamily: 'monospace' }}
                />
                <Button variant="contained" onClick={handleSaveAdc} disabled={!adcJson.trim()}>
                  Save Credentials
                </Button>
              </Paper>

              {/* Cluster Nodes */}
              {isClusterReady && (
                <Paper sx={{ p: 3, mt: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>Cluster Nodes ({clusterNodes.length})</Typography>
                  {clusterNodes.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No nodes currently active. Nodes are provisioned automatically by GKE Autopilot when workstations start.
                    </Typography>
                  ) : (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Machine Type</TableCell>
                            <TableCell>Zone</TableCell>
                            <TableCell>CPU</TableCell>
                            <TableCell>Memory</TableCell>
                            <TableCell>GPU</TableCell>
                            <TableCell>Status</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {clusterNodes.map((node) => (
                            <TableRow key={node.name}>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{node.name}</TableCell>
                              <TableCell>{node.machine_type}</TableCell>
                              <TableCell>{node.zone}</TableCell>
                              <TableCell>{node.cpu}</TableCell>
                              <TableCell>{node.memory}</TableCell>
                              <TableCell>{node.gpu !== '0' ? node.gpu : '-'}</TableCell>
                              <TableCell>
                                <Chip label={node.ready ? 'Ready' : 'Not Ready'} size="small" color={node.ready ? 'success' : 'warning'} />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </Paper>
              )}
            </Box>
          )}
        </Box>
      </Container>

      <NewWorkstationDialog
        open={isNewDialogOpen}
        onClose={() => setIsNewDialogOpen(false)}
        onConfirm={handleCreateWorkstation}
        availableImages={availableImages}
      />

      <EditWorkstationDialog
        open={isEditDialogOpen}
        onClose={() => {
          setIsEditDialogOpen(false);
          setEditingWorkstation(null);
        }}
        onConfirm={handleUpdateWorkstation}
        workstation={editingWorkstation}
        availableImages={availableImages}
      />

      <NewServiceDialog
        open={isNewServiceDialogOpen}
        onClose={() => setIsNewServiceDialogOpen(false)}
        onConfirm={handleCreateService}
        catalog={serviceCatalog}
      />

      <EditServiceDialog
        open={isEditServiceDialogOpen}
        onClose={() => {
          setIsEditServiceDialogOpen(false);
          setEditingService(null);
        }}
        onConfirm={handleUpdateService}
        service={editingService}
      />

      {notification && (
        <Snackbar
          open={!!notification}
          autoHideDuration={6000}
          onClose={() => setNotification(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert severity={notification.type} onClose={() => setNotification(null)}>
            {notification.msg}
          </Alert>
        </Snackbar>
      )}
    </>
  );
}

export default App;
