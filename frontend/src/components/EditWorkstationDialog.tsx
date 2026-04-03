import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Box, Typography, Divider, FormControlLabel, Checkbox } from '@mui/material';

export interface WorkstationConfig {
  name: string;
  ports: number[];
  cpu: string;
  memory: string;
  disk_size: string;
  gpu: string | null;
}

interface EditWorkstationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, ports: number[], cpu: string, memory: string, diskSize: string, gpu: string | null) => void;
  workstation: WorkstationConfig | null;
}

const EditWorkstationDialog: React.FC<EditWorkstationDialogProps> = ({ open, onClose, onConfirm, workstation }) => {
  const [portsStr, setPortsStr] = useState('');
  const [cpu, setCpu] = useState('500m');
  const [memory, setMemory] = useState('2Gi');
  const [diskSize, setDiskSize] = useState('10Gi');
  const [gpuEnabled, setGpuEnabled] = useState(false);

  useEffect(() => {
    if (workstation) {
      setPortsStr(workstation.ports?.join(', ') || '3000');
      setCpu(workstation.cpu || '500m');
      setMemory(workstation.memory || '2Gi');
      setDiskSize(workstation.disk_size || '10Gi');
      setGpuEnabled(!!workstation.gpu);
    }
  }, [workstation]);

  const handleConfirm = () => {
    if (workstation) {
      const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
      onConfirm(
        workstation.name,
        ports.length > 0 ? ports : [3000],
        cpu,
        memory,
        diskSize,
        gpuEnabled ? 'nvidia-l4' : null
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

          <FormControlLabel
            control={<Checkbox checked={gpuEnabled} onChange={(e) => setGpuEnabled(e.target.checked)} />}
            label="Attach NVIDIA L4 GPU"
          />
          {gpuEnabled && (
            <Typography variant="caption" color="text.secondary">
              An NVIDIA L4 GPU will be attached. GKE Autopilot will provision a GPU node automatically (may take several minutes).
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
