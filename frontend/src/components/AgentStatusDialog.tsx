import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, CircularProgress, Typography, Box, IconButton, Chip, Alert, List, Paper } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

interface PaneSummary {
    pane_id: string;
    window_name: string;
    pane_index?: string | number;
    command: string;
    status: string;
    task_summary: string;
    initial_intent?: string;
    working_directory?: string;
    git_branch?: string;
}

interface AgentStatusDialogProps {
    open: boolean;
    onClose: () => void;
    userNs: string;
    workstationName: string;
}

export default function AgentStatusDialog({ open, onClose, userNs, workstationName }: AgentStatusDialogProps) {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [panes, setPanes] = useState<PaneSummary[]>([]);

    const fetchAgentStatus = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/workstations/${userNs}/agents/${workstationName}`);
            if (response.ok) {
                const data = await response.json();
                setPanes(data.panes || []);
            } else {
                setError(`Failed to communicate with Agent API: HTTP ${response.status}`);
            }
        } catch (err: any) {
            setError(`Failed to communicate with Agent API: ${err.message}`);
        } finally {
            setLoading(false);
        }
    }, [userNs, workstationName]);

    useEffect(() => {
        if (open) {
            fetchAgentStatus();
        } else {
            // Reset state when closed
            setPanes([]);
            setError(null);
            setLoading(true);
        }
    }, [open, fetchAgentStatus]);

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                Agents Activity ({workstationName})
                <IconButton onClick={fetchAgentStatus} disabled={loading} size="small">
                    <RefreshIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent dividers>
                {loading ? (
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
                        <CircularProgress sx={{ mb: 2 }} />
                        <Typography color="text.secondary">Querying agent states... This takes a few seconds to run the AI summarization.</Typography>
                    </Box>
                ) : error ? (
                    <Alert severity="error">{error}</Alert>
                ) : panes.length === 0 ? (
                    <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                        No active tmux panes or agents found.
                    </Typography>
                ) : (
                    <List sx={{ pt: 0 }}>
                        {panes.map((pane) => (
                            <Paper key={pane.pane_id} variant="outlined" sx={{ mb: 2, p: 2 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="subtitle1" fontWeight="bold">
                                        {pane.window_name} 
                                        <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                                            (Pane {pane.pane_index !== undefined ? pane.pane_index : pane.pane_id.replace('%', '')} - {pane.command})
                                        </Typography>
                                    </Typography>
                                    <Chip
                                        label={pane.status}
                                        size="small"
                                        color={pane.status === 'RUNNING' ? 'success' : pane.status === 'WAITING' ? 'warning' : 'default'}
                                    />
                                </Box>
                                
                                {pane.working_directory && (
                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5, fontFamily: 'monospace' }}>
                                        📁 {pane.working_directory} {pane.git_branch && <Chip label={`🌿 ${pane.git_branch}`} size="small" sx={{ ml: 1, height: '20px', fontSize: '0.7rem' }} />}
                                    </Typography>
                                )}
                                
                                {pane.initial_intent && (
                                    <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic', color: 'text.secondary' }}>
                                        Goal: {pane.initial_intent}
                                    </Typography>
                                )}

                                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mt: 1 }}>
                                    <strong>Current Status:</strong> {pane.task_summary}
                                </Typography>
                            </Paper>
                        ))}
                    </List>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
}
