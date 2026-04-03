import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Box, Typography, Divider, IconButton, Card, CardActionArea, CardContent } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

export interface CatalogEntry {
  service_type: string;
  label: string;
  image: string;
  ports: number[];
  data_mount_path: string;
  health_check_command: string[];
}

interface NewServiceDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, serviceType: string, image: string, ports: number[], cpu: string, memory: string, diskSize: string, envVars: Record<string, string>) => void;
  catalog: CatalogEntry[];
}

const NewServiceDialog: React.FC<NewServiceDialogProps> = ({ open, onClose, onConfirm, catalog }) => {
  const [name, setName] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [customImage, setCustomImage] = useState('');
  const [portsStr, setPortsStr] = useState('');
  const [cpu, setCpu] = useState('250m');
  const [memory, setMemory] = useState('512Mi');
  const [diskSize, setDiskSize] = useState('5Gi');
  const [envEntries, setEnvEntries] = useState<{key: string, value: string}[]>([]);

  const selectedCatalog = catalog.find(c => c.service_type === selectedType);
  const isCustom = selectedType === 'custom';

  const handleSelectType = (type: string) => {
    setSelectedType(type);
    const entry = catalog.find(c => c.service_type === type);
    if (entry) {
      setPortsStr(entry.ports.join(', '));
    } else {
      setPortsStr('');
    }
  };

  const handleConfirm = () => {
    if (!name || (!selectedCatalog && !isCustom)) return;
    const image = isCustom ? customImage : selectedCatalog!.image;
    if (!image) return;
    const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
    const envVars: Record<string, string> = {};
    envEntries.forEach(e => { if (e.key.trim()) envVars[e.key.trim()] = e.value; });
    onConfirm(name, selectedType, image, ports, cpu, memory, diskSize, envVars);
    // Reset
    setName('');
    setSelectedType('');
    setCustomImage('');
    setPortsStr('');
    setCpu('250m');
    setMemory('512Mi');
    setDiskSize('5Gi');
    setEnvEntries([]);
    onClose();
  };

  const canConfirm = name && selectedType && (isCustom ? customImage : true);

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

          {isCustom && (
            <>
              <TextField
                label="Docker Image"
                placeholder="e.g. postgres:16"
                fullWidth
                value={customImage}
                onChange={(e) => setCustomImage(e.target.value)}
              />
              <TextField
                label="Ports (comma-separated)"
                placeholder="e.g. 5432"
                fullWidth
                value={portsStr}
                onChange={(e) => setPortsStr(e.target.value)}
              />
            </>
          )}

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
