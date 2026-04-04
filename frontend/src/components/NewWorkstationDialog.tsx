import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem, Select, FormControl, InputLabel, Box, Typography, Divider, FormControlLabel, Checkbox, IconButton } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';

export interface ImageMetadata {
  uri: string;
  tags: string[];
  update_time: string;
  build_id?: string | null;
  build_status?: string | null;
  build_log_url?: string | null;
}

interface NewWorkstationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, imageUri: string, ports: number[], cpu: string, memory: string, diskSize: string, gpu: string | null, envVars: Record<string, string>, runAsRoot: boolean) => void;
  availableImages: ImageMetadata[];
}

const NewWorkstationDialog: React.FC<NewWorkstationDialogProps> = ({ open, onClose, onConfirm, availableImages }) => {
  const [name, setName] = useState('');
  const [selectedImage, setSelectedImage] = useState('');
  const [portsStr, setPortsStr] = useState('');
  const [cpu, setCpu] = useState('500m');
  const [memory, setMemory] = useState('2Gi');
  const [diskSize, setDiskSize] = useState('10Gi');
  const [gpuEnabled, setGpuEnabled] = useState(false);
  const [runAsRoot, setRunAsRoot] = useState(false);
  const [envEntries, setEnvEntries] = useState<{key: string, value: string}[]>([]);

  const handleConfirm = () => {
    if (name && selectedImage) {
      const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
      const envVars: Record<string, string> = {};
      envEntries.forEach(e => { if (e.key.trim()) envVars[e.key.trim()] = e.value; });
      onConfirm(
        name,
        selectedImage,
        ports,
        cpu,
        memory,
        diskSize,
        gpuEnabled ? 'nvidia-l4' : null,
        envVars,
        runAsRoot
      );
      setName('');
      setSelectedImage('');
      setPortsStr('');
      setCpu('500m');
      setMemory('2Gi');
      setDiskSize('10Gi');
      setGpuEnabled(false);
      setRunAsRoot(false);
      setEnvEntries([]);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Create New Workstation Instance</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Workstation Name"
            placeholder="e.g. my-python-project"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <FormControl fullWidth>
            <InputLabel>Select Image Configuration</InputLabel>
            <Select
              value={selectedImage}
              label="Select Image Configuration"
              onChange={(e) => setSelectedImage(e.target.value)}
            >
              {availableImages.filter(img => img.uri).length === 0 && (
                <MenuItem disabled value="">
                  No custom images found. Build one in the "Images" tab!
                </MenuItem>
              )}
              {availableImages.filter(img => img.uri).map((img) => (
                <MenuItem key={img.tags?.[0] || img.uri} value={img.uri}>
                  <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="body1">
                      {img.tags && img.tags.length > 0 ? img.tags[0] : img.uri.split('/').pop()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {img.uri.split('/').pop()?.split('@')[0]}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
              <Divider />
              <MenuItem value="gitpod/openvscode-server:latest">
                <em>Default: OpenVSCode Server (Latest)</em>
              </MenuItem>
            </Select>
          </FormControl>

          <Divider />
          <Typography variant="subtitle2" color="text.secondary">Resources</Typography>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              label="CPU"
              placeholder="e.g. 500m, 1, 2"
              value={cpu}
              onChange={(e) => setCpu(e.target.value)}
              helperText="Cores (e.g. 500m = 0.5 cores)"
              sx={{ flex: 1 }}
            />
            <TextField
              label="Memory"
              placeholder="e.g. 2Gi, 4Gi"
              value={memory}
              onChange={(e) => setMemory(e.target.value)}
              helperText="RAM allocation"
              sx={{ flex: 1 }}
            />
            <TextField
              label="Disk Size"
              placeholder="e.g. 10Gi, 50Gi"
              value={diskSize}
              onChange={(e) => setDiskSize(e.target.value)}
              helperText="Persistent volume"
              sx={{ flex: 1 }}
            />
          </Box>

          <TextField
            label="Ports to Expose (comma-separated)"
            placeholder="e.g. 3000, 8080"
            fullWidth
            value={portsStr}
            onChange={(e) => setPortsStr(e.target.value)}
            helperText="Specify the ports you want to forward when connecting."
          />

          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <FormControlLabel
              control={<Checkbox checked={gpuEnabled} onChange={(e) => setGpuEnabled(e.target.checked)} />}
              label="Attach NVIDIA L4 GPU"
            />
            {gpuEnabled && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 4, mb: 1 }}>
                An NVIDIA L4 GPU will be attached. GKE Autopilot will provision a GPU node automatically (may take several minutes).
              </Typography>
            )}

            <FormControlLabel
              control={<Checkbox checked={runAsRoot} onChange={(e) => setRunAsRoot(e.target.checked)} />}
              label="Run as Root"
            />
            {runAsRoot && (
              <Typography variant="caption" color="warning.main" sx={{ ml: 4, mb: 1 }}>
                Warning: Running as root is less secure and only recommended for specific troubleshooting or legacy images.
              </Typography>
            )}
          </Box>

          <Divider />
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="subtitle2" color="text.secondary">Environment Variables</Typography>
            <IconButton size="small" onClick={() => setEnvEntries([...envEntries, { key: '', value: '' }])}>
              <AddIcon fontSize="small" />
            </IconButton>
          </Box>
          {envEntries.map((entry, idx) => (
            <Box key={idx} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <TextField
                label="Name"
                size="small"
                value={entry.key}
                onChange={(e) => { const next = [...envEntries]; next[idx].key = e.target.value; setEnvEntries(next); }}
                sx={{ flex: 1 }}
                placeholder="MY_VAR"
              />
              <TextField
                label="Value"
                size="small"
                value={entry.value}
                onChange={(e) => { const next = [...envEntries]; next[idx].value = e.target.value; setEnvEntries(next); }}
                sx={{ flex: 2 }}
                placeholder="some-value"
              />
              <IconButton size="small" onClick={() => setEnvEntries(envEntries.filter((_, i) => i !== idx))}>
                <RemoveCircleOutlineIcon fontSize="small" color="error" />
              </IconButton>
            </Box>
          ))}
          {envEntries.length === 0 && (
            <Typography variant="caption" color="text.secondary">
              No environment variables configured. Click + to add one.
            </Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleConfirm} variant="contained" disabled={!name || !selectedImage}>
          Create & Start
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default NewWorkstationDialog;
