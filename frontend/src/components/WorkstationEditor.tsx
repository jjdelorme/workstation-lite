import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Box, Button, Typography, Paper, Alert, Snackbar, TextField, LinearProgress } from '@mui/material';

export const DEFAULT_DOCKERFILE = `FROM gitpod/openvscode-server:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    wget \\
    zsh \\
    vim \\
    tmux \\
    jq \\
    build-essential \\
    python3 \\
    python3-pip \\
    golang-go \\
    fontconfig

# Install MesloLGS NF Fonts for Powerlevel10k
RUN mkdir -p /usr/share/fonts/truetype/meslo && \\
    wget -P /usr/share/fonts/truetype/meslo https://github.com/romkatv/dotfiles-public/raw/master/.local/share/fonts/NerdFonts/MesloLGS%20NF%20Regular.ttf && \\
    wget -P /usr/share/fonts/truetype/meslo https://github.com/romkatv/dotfiles-public/raw/master/.local/share/fonts/NerdFonts/MesloLGS%20NF%20Bold.ttf && \\
    wget -P /usr/share/fonts/truetype/meslo https://github.com/romkatv/dotfiles-public/raw/master/.local/share/fonts/NerdFonts/MesloLGS%20NF%20Italic.ttf && \\
    wget -P /usr/share/fonts/truetype/meslo https://github.com/romkatv/dotfiles-public/raw/master/.local/share/fonts/NerdFonts/MesloLGS%20NF%20Bold%20Italic.ttf && \\
    fc-cache -fv

# Install Node.js (via NVM)
ENV NVM_DIR /home/workspace/.nvm
RUN mkdir -p $NVM_DIR && \\
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash && \\
    . $NVM_DIR/nvm.sh && \\
    nvm install --lts && \\
    nvm use --lts

# Install Cloud Tools (gcloud SDK via binary to allow components update)
RUN cd /usr/local && \\
    curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz && \\
    tar -xf google-cloud-cli-linux-x86_64.tar.gz && \\
    rm google-cloud-cli-linux-x86_64.tar.gz && \\
    ./google-cloud-sdk/install.sh --quiet
ENV PATH $PATH:/usr/local/google-cloud-sdk/bin

USER openvscode-server

# Install Oh My Zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Install Powerlevel10k
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k

# Configure Zsh and Tmux per TMUX-SSH-OHMYZSH.md
RUN sed -i 's/ZSH_THEME="robbyrussell"/ZSH_THEME="powerlevel10k\\/powerlevel10k"/' ~/.zshrc && \\
    echo '\\n# Tmux/SSH UTF-8 and Color configuration' >> ~/.zshrc && \\
    echo 'export LANG=en_US.UTF-8' >> ~/.zshrc && \\
    echo 'export LC_ALL=en_US.UTF-8' >> ~/.zshrc && \\
    echo '[[ -z "$TMUX" ]] && export TERM=xterm-256color' >> ~/.zshrc && \\
    echo '# Tmux configuration' > ~/.tmux.conf && \\
    echo 'set -g default-terminal "screen-256color"' >> ~/.tmux.conf && \\
    echo 'set -g default-shell /bin/zsh' >> ~/.tmux.conf

# Ensure persistence for /home/workspace is utilized for tools
ENV PYTHONUSERBASE=/home/workspace/.local
`;

interface WorkstationEditorProps {
  initialDockerfile?: string;
  initialName?: string;
  onBuildSuccess?: () => void;
  onBuildStart?: () => void;
  initialBuildId?: string;
  initialBuildStatus?: string;
}

const WorkstationEditor: React.FC<WorkstationEditorProps> = ({ initialDockerfile, initialName, onBuildSuccess, onBuildStart, initialBuildId, initialBuildStatus }) => {
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
  }, [activeBuild?.id, activeBuild?.status]);

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
