import { AppBar, Toolbar, Typography, Container, Button, Box, Paper, Snackbar, Alert, LinearProgress, Chip, CircularProgress, Divider, Card, CardContent, CardActions, IconButton, Tabs, Tab, List, ListItem, ListItemText, Grid, ListItemButton } from '@mui/material';
import { useState, useEffect } from 'react';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import WorkstationEditor from './components/WorkstationEditor';
import ConnectionInstructions from './components/ConnectionInstructions';
import NewWorkstationDialog from './components/NewWorkstationDialog';
import type { ImageMetadata } from './components/NewWorkstationDialog';

interface WorkstationStatus {
  name: string;
  user_ns: string;
  status: string;
  image?: string;
  ports?: number[];
  pod_name?: string;
  pod_ready: boolean;
}

interface WorkstationListResponse {
  workstations: WorkstationStatus[];
  count: number;
}

interface AppConfig {
  project_id: string;
  region: string;
  account: string;
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
  
  // States for viewing/editing existing image Dockerfiles
  const [selectedImageName, setSelectedImageName] = useState<string | undefined>(undefined);
  const [selectedDockerfile, setSelectedDockerfile] = useState<string | undefined>(undefined);

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
      }
    } catch (error) {
      console.error("Failed to fetch workstations:", error);
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
      }
    } catch (error) {
      console.error("Failed to fetch images:", error);
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
        setClusterStatus("UNKNOWN");
      }
    } catch (error) {
      console.error("Failed to fetch cluster status:", error);
      setClusterStatus("OFFLINE");
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
      }
    } catch (error) {
      console.error("Failed to fetch config:", error);
    }
  };

  const fetchAll = () => {
    fetchWorkstations();
    fetchImages();
    fetchClusterStatus();
    fetchConfig();
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => {
      fetchWorkstations();
      fetchClusterStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

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

  const handleCreateWorkstation = async (name: string, imageUri: string, ports: number[]) => {
    setNotification({ type: 'info', msg: `Creating workstation ${name}...` });
    try {
      const saveResponse = await fetch(`/api/workstations/${user_ns}/save-config/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageUri, ports }),
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

          {noCluster && (
            <Alert severity="warning" sx={{ mb: 4 }}>
              No infrastructure detected. Click "Initialize Project" to provision your GKE Autopilot cluster.
            </Alert>
          )}

          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
              <Tab label="Workstations" />
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
                              color={ws.status === 'RUNNING' ? 'success' : ws.status === 'STOPPED' ? 'default' : 'info'} 
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
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontFamily: 'monospace' }}>
                          Image: {ws.image?.split('/').pop()?.split('@')[0]}
                        </Typography>
                        {ws.ports && ws.ports.length > 0 && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontFamily: 'monospace' }}>
                            Ports: {ws.ports.join(', ')}
                          </Typography>
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
                      {availableImages.map((img) => (
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
                              primary={img.tags && img.tags.length > 0 ? img.tags[0] : "Untitled Image"} 
                              secondary={img.uri ? img.uri.split('/').pop()?.split('@')[0] : "Draft Recipe (Unbuilt)"} 
                            />
                          </ListItemButton>
                        </ListItem>
                      ))}
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
                  />
                </Grid>
              </Grid>
            </Box>
          )}

          {tabValue === 2 && (
            <Box>
              <Typography variant="h5" gutterBottom>Infrastructure Management</Typography>
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
