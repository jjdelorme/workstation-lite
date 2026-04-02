import React from 'react';
import { Box, Typography, Paper, IconButton, Tooltip } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

interface ConnectionInstructionsProps {
  userNs: string;
  workstationName: string;
  ports?: number[];
}

const ConnectionInstructions: React.FC<ConnectionInstructionsProps> = ({ userNs, workstationName, ports }) => {
  const currentHost = window.location.host;
  const protocol = window.location.protocol;
  const connectUrl = `${protocol}//${currentHost}/api/workstations/${userNs}/connect/${workstationName}`;
  const magicCmd = `/bin/bash -c "$(curl -fsSL ${connectUrl})"`;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };
  
  const portsLabel = ports && ports.length > 0 ? ports.join(', ') : '3000';

  return (
    <Paper sx={{ p: 2, mt: 2, bgcolor: '#f5f5f5' }} elevation={1}>
      <Typography variant="subtitle2" gutterBottom color="text.secondary">
        Connect to your workstation:
      </Typography>
      
      <Box sx={{ position: 'relative' }}>
        <Typography variant="caption">Terminal One-Liner (Web IDE + CLI)</Typography>
        <Box sx={{ 
          p: 1, 
          bgcolor: '#2d2d2d', 
          color: '#fff', 
          fontFamily: 'monospace', 
          borderRadius: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mt: 0.5
        }}>
          <code style={{ wordBreak: 'break-all', fontSize: '0.8rem' }}>{magicCmd}</code>
          <Tooltip title="Copy">
            <IconButton size="small" onClick={() => copyToClipboard(magicCmd)} sx={{ color: '#fff', ml: 1 }}>
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Typography variant="caption" sx={{ mt: 1, display: 'block', color: 'text.secondary', fontStyle: 'italic' }}>
          This will forward port(s) {portsLabel} and launch a secure shell session.
        </Typography>
      </Box>
    </Paper>
  );
};

export default ConnectionInstructions;
