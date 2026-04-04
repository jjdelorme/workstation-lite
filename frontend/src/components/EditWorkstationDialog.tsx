import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Box, Typography, Divider, FormControlLabel, Checkbox, IconButton, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import type { ImageMetadata } from './NewWorkstationDialog';

export interface WorkstationConfig {
  name: string;
  image?: string;
  ports: number[];
  cpu: string;
  memory: string;
  disk_size: string;
  gpu: string | null;
  use_spot: boolean;
  run_as_root: boolean;
  env_vars: Record<string, string>;
}

interface EditWorkstationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, ports: number[], cpu: string, memory: string, diskSize: string, gpu: string | null, useSpot: boolean, envVars: Record<string, string>, runAsRoot: boolean, image?: string) => void;
  workstation: WorkstationConfig | null;
  availableImages: ImageMetadata[];
}

const EditWorkstationDialog: React.FC<EditWorkstationDialogProps> = ({ open, onClose, onConfirm, workstation, availableImages }) => {
  const [selectedImage, setSelectedImage] = useState(workstation?.image || '');
  const [portsStr, setPortsStr] = useState(workstation?.ports?.join(', ') || '');
  const [cpu, setCpu] = useState(workstation?.cpu || '500m');
  const [memory, setMemory] = useState(workstation?.memory || '2Gi');
  const [diskSize, setDiskSize] = useState(workstation?.disk_size || '10Gi');
  const [gpuEnabled, setGpuEnabled] = useState(!!workstation?.gpu);
  const [useSpot, setUseSpot] = useState(workstation?.use_spot || false);
  const [runAsRoot, setRunAsRoot] = useState(workstation?.run_as_root || false);
  const [envEntries, setEnvEntries] = useState<{key: string, value: string}[]>(() => {
    const ev = workstation?.env_vars || {};
    return Object.entries(ev).map(([key, value]) => ({ key, value }));
  });

  const handleConfirm = () => {
    if (workstation) {
      const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
      const envVars: Record<string, string> = {};
      envEntries.forEach(e => { if (e.key.trim()) envVars[e.key.trim()] = e.value; });
      const imageChanged = selectedImage && selectedImage !== workstation.image;
      onConfirm(
        workstation.name,
        ports,
        cpu,
        memory,
        diskSize,
        gpuEnabled ? 'nvidia-l4' : null,
        useSpot,
        envVars,
        runAsRoot,
        imageChanged ? selectedImage : undefined
      );
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Edit Workstation Configuration</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant="subtitle2">Workstation: {workstation?.name}</Typography>

          <FormControl fullWidth>
            <InputLabel>Image Template</InputLabel>
            <Select
              value={selectedImage}
              label="Image Template"
              onChange={(e) => setSelectedImage(e.target.value)}
            >
              {workstation?.image && (
                <MenuItem value={workstation.image}>
                  <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="body2">
                      Current: {workstation.image.split('/').pop()?.split('@')[0]}
                    </Typography>
                  </Box>
                </MenuItem>
              )}
              {availableImages.filter(img => img.uri && img.uri !== workstation?.image).map((img) => (
                <MenuItem key={img.tags?.[0] || img.uri} value={img.uri}>
                  <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="body2">
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
          {selectedImage && workstation?.image && selectedImage !== workstation.image && (
            <Typography variant="caption" color="warning.main">
              Changing the image template will use a new container image while preserving your /home/workspace data.
            </Typography>
          )}

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

          <Divider />

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
              control={<Checkbox checked={useSpot} onChange={(e) => setUseSpot(e.target.checked)} />}
              label="Use Spot Instance (80% cheaper)"
            />
            {useSpot && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 4, mb: 1 }}>
                Spot instances are significantly cheaper but can be reclaimed by Google Cloud if capacity is needed elsewhere. vLLM will restart automatically.
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

          <Typography variant="body2" color="text.secondary">
            Changes will be saved and applied the next time you <b>Start</b> this workstation.
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleConfirm} variant="contained" color="primary">
          Save Configuration
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EditWorkstationDialog;
