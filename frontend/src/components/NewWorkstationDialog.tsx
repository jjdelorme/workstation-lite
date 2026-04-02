import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem, Select, FormControl, InputLabel, Box, Typography, Divider } from '@mui/material';

export interface ImageMetadata {
  uri: string;
  tags: string[];
  update_time: string;
}

interface NewWorkstationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string, imageUri: string, ports: number[]) => void;
  availableImages: ImageMetadata[];
}

const NewWorkstationDialog: React.FC<NewWorkstationDialogProps> = ({ open, onClose, onConfirm, availableImages }) => {
  const [name, setName] = useState('');
  const [selectedImage, setSelectedImage] = useState('');
  const [portsStr, setPortsStr] = useState('3000');

  const handleConfirm = () => {
    if (name && selectedImage) {
      const ports = portsStr.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
      onConfirm(name, selectedImage, ports.length > 0 ? ports : [3000]);
      setName('');
      setSelectedImage('');
      setPortsStr('3000');
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
          <TextField
            label="Ports to Expose (comma-separated)"
            placeholder="e.g. 3000, 8080"
            fullWidth
            value={portsStr}
            onChange={(e) => setPortsStr(e.target.value)}
            helperText="Specify the ports you want to forward when connecting."
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
          
          <Typography variant="body2" color="text.secondary">
            Choosing an image template will pre-configure your workstation environment with the tools and settings defined in that image's Dockerfile.
          </Typography>
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
