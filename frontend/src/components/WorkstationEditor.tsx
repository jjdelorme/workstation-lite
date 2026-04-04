import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Box, Button, Typography, Paper, Alert, Snackbar, TextField, LinearProgress } from '@mui/material';
import DEFAULT_DOCKERFILE from '@root/templates/Dockerfile.template?raw';

interface WorkstationEditorProps {
  initialDockerfile?: string;
  initialName?: string;
  onBuildSuccess?: () => void;
  onBuildStart?: () => void;
  onReset?: () => void;
  initialBuildId?: string;
  initialBuildStatus?: string;
}

const WorkstationEditor: React.FC<WorkstationEditorProps> = ({ initialDockerfile, initialName, onBuildSuccess, onBuildStart, onReset, initialBuildId, initialBuildStatus }) => {
  const [dockerfile, setDockerfile] = useState(initialDockerfile || DEFAULT_DOCKERFILE);
  const [name, setName] = useState(initialName || 'workstation');
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info', msg: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeBuild, setActiveBuild] = useState<{id: string, status: string} | null>(null);

  // Sync with props when they change
  useEffect(() => {
    if (initialDockerfile) setDockerfile(initialDockerfile);
    if (initialName) setName(initialName);
  }, [initialDockerfile, initialName]);

  // Restore active build from parent-provided props (e.g. after navigating back)
  useEffect(() => {
    if (initialBuildId && initialBuildStatus) {
      setActiveBuild({ id: initialBuildId, status: initialBuildStatus });
    } else {
      setActiveBuild(null);
    }
  }, [initialBuildId, initialBuildStatus]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    if (activeBuild && !['SUCCESS', 'FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'].includes(activeBuild.status)) {
      interval = setInterval(async () => {
        try {
          const response = await fetch(`/api/workstations/user-1/builds/${activeBuild.id}`, {
            headers: {
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache',
              'Expires': '0'
            },
            cache: 'no-store'
          });
          
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            console.error("Backend error polling build:", data);
            return;
          }

          const data = await response.json();
          setActiveBuild((prev) => prev ? { ...prev, status: data.status } : null);

          if (data.status === 'SUCCESS') {
            setStatus({ type: 'success', msg: 'Build completed successfully! Your new workstation card is available.' });
            if (onBuildSuccess) onBuildSuccess();
          } else if (['FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'].includes(data.status)) {
            setStatus({ type: 'error', msg: `Build failed with status: ${data.status}. Check Cloud Build logs.` });
          }
        } catch (error) {
          console.error('Error polling build status:', error);
        }
      }, 5000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [activeBuild, onBuildSuccess]);

  const handleBuild = async () => {
    if (!name.trim()) {
      setStatus({ type: 'error', msg: 'Please enter a workstation name' });
      return;
    }
    setLoading(true);
    setStatus({ type: 'info', msg: `Triggering build for ${name}...` });
    try {
      const response = await fetch(`/api/workstations/user-1/build/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dockerfile }),
      });
      const data = await response.json();
      if (response.ok) {
        setStatus({ type: 'success', msg: 'Build triggered successfully! Monitoring progress...' });
        setActiveBuild({ id: data.build_id, status: 'QUEUED' });
        if (onBuildStart) onBuildStart();
      } else {
        setStatus({ type: 'error', msg: `Build failed: ${data.detail || data.message}` });
      }
    } catch (error) {
      setStatus({ type: 'error', msg: `Error: ${error}` });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setDockerfile(DEFAULT_DOCKERFILE);
    setName('workstation');
    if (onReset) onReset();
  };

  return (
    <Paper sx={{ p: 2, mt: 3 }} elevation={2}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Custom Workstation Image (Dockerfile)
        </Typography>
        <Button size="small" onClick={handleReset}>Clear / New Template</Button>
      </Box>
      
      {activeBuild && (
        <Alert 
          severity={
            activeBuild.status === 'SUCCESS' ? 'success' : 
            ['FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'].includes(activeBuild.status) ? 'error' : 'info'
          } 
          sx={{ mb: 2 }}
          onClose={() => setActiveBuild(null)}
        >
          {['SUCCESS', 'FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'].includes(activeBuild.status) ? 'Build finished' : 'Build in progress'}: <strong>{activeBuild.status}</strong> (ID: {activeBuild.id})
          {!['SUCCESS', 'FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'].includes(activeBuild.status) && (
            <LinearProgress sx={{ mt: 1 }} />
          )}
        </Alert>
      )}

      <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'flex-end' }}>
        <TextField 
          label="Workstation Name" 
          variant="standard" 
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. workstation, python-dev"
          sx={{ width: 300 }}
        />
        <Button 
          variant="contained" 
          color="secondary" 
          onClick={handleBuild}
          disabled={loading}
        >
          {loading ? 'Building...' : 'Save & Build Image'}
        </Button>
      </Box>
      <Box sx={{ border: '1px solid #ccc', borderRadius: 1, overflow: 'hidden', mb: 2 }}>
        <Editor
          height="400px"
          defaultLanguage="dockerfile"
          value={dockerfile}
          onChange={(value) => setDockerfile(value || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
          }}
        />
      </Box>

      {status && (
        <Snackbar 
          open={!!status} 
          autoHideDuration={6000} 
          onClose={() => setStatus(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert severity={status.type} onClose={() => setStatus(null)}>
            {status.msg}
          </Alert>
        </Snackbar>
      )}
    </Paper>
  );
};

export default WorkstationEditor;
