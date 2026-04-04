import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Box, Typography, Divider, IconButton, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

export interface ServiceConfig {
  name: string;
  image?: string;
  service_type: string;
  ports: number[];
  cpu: string;
  memory: string;
  disk_size: string;
  env_vars: Record<string, string>;
  data_mount_path: string;
  health_check_command: string[];
}

interface EditServiceDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, ports: number[], cpu: string, memory: string, diskSize: string, envVars: Record<string, string>, dataMountPath: string, healthCheckCommand: string[]) => void;
  service: ServiceConfig | null;
}

const EditServiceDialog: React.FC<EditServiceDialogProps> = ({ open, onClose, onConfirm, service }) => {
  const [portsStr, setPortsStr] = useState('');
  const [cpu, setCpu] = useState('2000m');
  const [memory, setMemory] = useState('8Gi');
  const [diskSize, setDiskSize] = useState('5Gi');
  const [dataMountPath, setDataMountPath] = useState('/data');
  const [healthCheckCmd, setHealthCheckCmd] = useState('');
  const [envEntries, setEnvEntries] = useState<{key: string, value: string}[]>([]);

  useEffect(() => {
    if (service) {
      setPortsStr(service.ports?.join(', ') || '');
      setCpu(service.cpu || '2000m');
      setMemory(service.memory || '8Gi');
      setDiskSize(service.disk_size || '5Gi');
      setDataMountPath(service.data_mount_path || '/data');
      setHealthCheckCmd(service.health_check_command?.join(' ') || '');
      const ev = service.env_vars || {};
      setEnvEntries(Object.entries(ev).map(([key, value]) => ({ key, value })));
    }
  }, [service]);

  const handleConfirm = () => {
    if (!service) return;
    const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
    const envVars: Record<string, string> = {};
    envEntries.forEach(e => { if (e.key.trim()) envVars[e.key.trim()] = e.value; });
    const healthCheck = healthCheckCmd.trim() ? healthCheckCmd.trim().split(/\s+/) : [];
    onConfirm(service.name, ports, cpu, memory, diskSize, envVars, dataMountPath, healthCheck);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Edit Service Configuration</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant="subtitle2">Service: {service?.name}</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
            Image: {service?.image} ({service?.service_type})
          </Typography>

          <Divider />
          <Typography variant="subtitle2" color="text.secondary">Resources</Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField label="CPU" value={cpu} onChange={(e) => setCpu(e.target.value)} helperText="e.g. 250m" sx={{ flex: 1 }} />
            <TextField label="Memory" value={memory} onChange={(e) => setMemory(e.target.value)} helperText="e.g. 512Mi" sx={{ flex: 1 }} />
            <TextField label="Disk" value={diskSize} onChange={(e) => setDiskSize(e.target.value)} helperText="e.g. 5Gi" sx={{ flex: 1 }} />
          </Box>

          <TextField
            label="Ports (comma-separated)"
            fullWidth
            value={portsStr}
            onChange={(e) => setPortsStr(e.target.value)}
          />

          <Divider />
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="subtitle2" color="text.secondary">Environment Variables</Typography>
            <IconButton size="small" onClick={() => setEnvEntries([...envEntries, { key: '', value: '' }])}>
              <AddIcon fontSize="small" />
            </IconButton>
          </Box>
          {envEntries.map((entry, idx) => (
            <Box key={idx} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <TextField label="Name" size="small" value={entry.key} onChange={(e) => { const next = [...envEntries]; next[idx].key = e.target.value; setEnvEntries(next); }} sx={{ flex: 1 }} />
              <TextField label="Value" size="small" value={entry.value} onChange={(e) => { const next = [...envEntries]; next[idx].value = e.target.value; setEnvEntries(next); }} sx={{ flex: 2 }} />
              <IconButton size="small" onClick={() => setEnvEntries(envEntries.filter((_, i) => i !== idx))}>
                <RemoveCircleOutlineIcon fontSize="small" color="error" />
              </IconButton>
            </Box>
          ))}
          {envEntries.length === 0 && (
            <Typography variant="caption" color="text.secondary">No environment variables. Click + to add.</Typography>
          )}

          <Accordion disableGutters elevation={0} sx={{ '&:before': { display: 'none' }, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" color="text.secondary">Advanced Settings</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Data Mount Path"
                  fullWidth
                  value={dataMountPath}
                  onChange={(e) => setDataMountPath(e.target.value)}
                  helperText="Where the persistent volume is mounted inside the container"
                />
                <TextField
                  label="Health Check Command"
                  fullWidth
                  value={healthCheckCmd}
                  onChange={(e) => setHealthCheckCmd(e.target.value)}
                  helperText="Readiness probe command (space-separated)"
                />
              </Box>
            </AccordionDetails>
          </Accordion>

          <Typography variant="body2" color="text.secondary">
            Changes will apply the next time you <b>Start</b> this service.
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleConfirm} variant="contained">Save Configuration</Button>
      </DialogActions>
    </Dialog>
  );
};

export default EditServiceDialog;
