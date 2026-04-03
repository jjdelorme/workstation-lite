import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Box, Typography, Divider, IconButton, Card, CardActionArea, CardContent, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

export interface CatalogEntry {
  service_type: string;
  label: string;
  image: string;
  ports: number[];
  data_mount_path: string;
  health_check_command: string[];
  required_env_vars?: Record<string, string>;
}

interface NewServiceDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, serviceType: string, image: string, ports: number[], cpu: string, memory: string, diskSize: string, envVars: Record<string, string>, dataMountPath: string, healthCheckCommand: string[]) => void;
  catalog: CatalogEntry[];
}

const NewServiceDialog: React.FC<NewServiceDialogProps> = ({ open, onClose, onConfirm, catalog }) => {
  const [name, setName] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [image, setImage] = useState('');
  const [portsStr, setPortsStr] = useState('');
  const [cpu, setCpu] = useState('250m');
  const [memory, setMemory] = useState('512Mi');
  const [diskSize, setDiskSize] = useState('5Gi');
  const [dataMountPath, setDataMountPath] = useState('/data');
  const [healthCheckCmd, setHealthCheckCmd] = useState('');
  const [envEntries, setEnvEntries] = useState<{key: string, value: string}[]>([]);

  const handleSelectType = (type: string) => {
    setSelectedType(type);
    if (type === 'custom') {
      setImage('');
      setPortsStr('');
      setDataMountPath('/data');
      setHealthCheckCmd('');
      setEnvEntries([]);
      return;
    }
    const entry = catalog.find(c => c.service_type === type);
    if (entry) {
      setImage(entry.image);
      setPortsStr(entry.ports.join(', '));
      setDataMountPath(entry.data_mount_path);
      setHealthCheckCmd(entry.health_check_command.join(' '));
      // Pre-populate required env vars
      const envs: {key: string, value: string}[] = [];
      if (entry.required_env_vars) {
        Object.entries(entry.required_env_vars).forEach(([key, value]) => {
          envs.push({ key, value });
        });
      }
      setEnvEntries(envs);
    }
  };

  const handleConfirm = () => {
    if (!name || !selectedType || !image) return;
    const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
    const envVars: Record<string, string> = {};
    envEntries.forEach(e => { if (e.key.trim()) envVars[e.key.trim()] = e.value; });
    const healthCheck = healthCheckCmd.trim() ? healthCheckCmd.trim().split(/\s+/) : [];
    onConfirm(name, selectedType, image, ports, cpu, memory, diskSize, envVars, dataMountPath, healthCheck);
    // Reset
    setName('');
    setSelectedType('');
    setImage('');
    setPortsStr('');
    setCpu('250m');
    setMemory('512Mi');
    setDiskSize('5Gi');
    setDataMountPath('/data');
    setHealthCheckCmd('');
    setEnvEntries([]);
    onClose();
  };

  const canConfirm = name && selectedType && image;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Create Service</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Service Name"
            placeholder="e.g. my-postgres"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <Typography variant="subtitle2" color="text.secondary">Template</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {catalog.map((entry) => (
              <Card
                key={entry.service_type}
                variant={selectedType === entry.service_type ? 'elevation' : 'outlined'}
                sx={{
                  width: 110,
                  border: selectedType === entry.service_type ? '2px solid' : undefined,
                  borderColor: selectedType === entry.service_type ? 'primary.main' : undefined,
                }}
              >
                <CardActionArea onClick={() => handleSelectType(entry.service_type)}>
                  <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 }, textAlign: 'center' }}>
                    <Typography variant="body2" fontWeight={selectedType === entry.service_type ? 'bold' : 'normal'}>
                      {entry.label}
                    </Typography>
                    {selectedType === entry.service_type && (
                      <CheckCircleIcon color="primary" sx={{ fontSize: 16, mt: 0.5 }} />
                    )}
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
            <Card
              variant={selectedType === 'custom' ? 'elevation' : 'outlined'}
              sx={{
                width: 110,
                border: selectedType === 'custom' ? '2px solid' : undefined,
                borderColor: selectedType === 'custom' ? 'primary.main' : undefined,
              }}
            >
              <CardActionArea onClick={() => handleSelectType('custom')}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 }, textAlign: 'center' }}>
                  <Typography variant="body2" fontWeight={selectedType === 'custom' ? 'bold' : 'normal'}>
                    Custom
                  </Typography>
                  {selectedType === 'custom' && (
                    <CheckCircleIcon color="primary" sx={{ fontSize: 16, mt: 0.5 }} />
                  )}
                </CardContent>
              </CardActionArea>
            </Card>
          </Box>

          {selectedType && (
            <>
              <TextField
                label="Docker Image"
                placeholder="e.g. postgres:16"
                fullWidth
                value={image}
                onChange={(e) => setImage(e.target.value)}
              />
              <TextField
                label="Ports (comma-separated)"
                placeholder="e.g. 5432"
                fullWidth
                value={portsStr}
                onChange={(e) => setPortsStr(e.target.value)}
              />

              <Divider />
              <Typography variant="subtitle2" color="text.secondary">Resources</Typography>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField label="CPU" value={cpu} onChange={(e) => setCpu(e.target.value)} helperText="e.g. 250m" sx={{ flex: 1 }} />
                <TextField label="Memory" value={memory} onChange={(e) => setMemory(e.target.value)} helperText="e.g. 512Mi" sx={{ flex: 1 }} />
                <TextField label="Disk" value={diskSize} onChange={(e) => setDiskSize(e.target.value)} helperText="e.g. 5Gi" sx={{ flex: 1 }} />
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
                  <TextField label="Name" size="small" value={entry.key} onChange={(e) => { const next = [...envEntries]; next[idx].key = e.target.value; setEnvEntries(next); }} sx={{ flex: 1 }} placeholder="MY_VAR" />
                  <TextField label="Value" size="small" value={entry.value} onChange={(e) => { const next = [...envEntries]; next[idx].value = e.target.value; setEnvEntries(next); }} sx={{ flex: 2 }} placeholder="some-value" />
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
                      helperText="Readiness probe command (space-separated, e.g. 'pg_isready')"
                    />
                  </Box>
                </AccordionDetails>
              </Accordion>
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleConfirm} variant="contained" disabled={!canConfirm}>Create & Start</Button>
      </DialogActions>
    </Dialog>
  );
};

export default NewServiceDialog;
