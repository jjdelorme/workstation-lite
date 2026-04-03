import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem, Select, FormControl, InputLabel, Box, Typography, Divider, FormControlLabel, Checkbox } from '@mui/material';

export interface ImageMetadata {
  uri: string;
  tags: string[];
  update_time: string;
}

interface NewWorkstationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, imageUri: string, ports: number[], cpu: string, memory: string, diskSize: string, gpu: string | null) => void;
  availableImages: ImageMetadata[];
}

const NewWorkstationDialog: React.FC<NewWorkstationDialogProps> = ({ open, onClose, onConfirm, availableImages }) => {
  const [name, setName] = useState('');
  const [selectedImage, setSelectedImage] = useState('');
  const [portsStr, setPortsStr] = useState('3000');
  const [cpu, setCpu] = useState('500m');
  const [memory, setMemory] = useState('2Gi');
  const [diskSize, setDiskSize] = useState('10Gi');
  const [gpuEnabled, setGpuEnabled] = useState(false);

  const handleConfirm = () => {
    if (name && selectedImage) {
      const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
      onConfirm(
        name,
        selectedImage,
        ports.length > 0 ? ports : [3000],
        cpu,
        memory,
        diskSize,
        gpuEnabled ? 'nvidia-l4' : null
      );
      setName('');
      setSelectedImage('');
      setPortsStr('3000');
      setCpu('500m');
      setMemory('2Gi');
      setDiskSize('10Gi');
      setGpuEnabled(false);
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

          <FormControlLabel
            control={<Checkbox checked={gpuEnabled} onChange={(e) => setGpuEnabled(e.target.checked)} />}
            label="Attach NVIDIA L4 GPU"
          />
          {gpuEnabled && (
            <Typography variant="caption" color="text.secondary">
              An NVIDIA L4 GPU will be attached. GKE Autopilot will provision a GPU node automatically (may take several minutes).
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
