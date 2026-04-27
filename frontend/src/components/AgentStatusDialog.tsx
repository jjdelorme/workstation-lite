import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, CircularProgress, Typography, Box, IconButton, Chip, Alert, List, Paper } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

interface PaneLayout {
    top: number;
    left: number;
    width: number;
    height: number;
}

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
    layout?: PaneLayout;
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

    // Calculate overall container size based on max bottom/right bounds of panes
    const maxLayout = panes.reduce(
        (acc, pane) => {
            if (!pane.layout) return acc;
            return {
                width: Math.max(acc.width, pane.layout.left + pane.layout.width),
                height: Math.max(acc.height, pane.layout.top + pane.layout.height),
            };
        },
        { width: 0, height: 0 }
    );

    const hasLayouts = maxLayout.width > 0 && maxLayout.height > 0;

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xl" fullWidth>
            <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                Agents Activity ({workstationName})
                <IconButton onClick={fetchAgentStatus} disabled={loading} size="small">
                    <RefreshIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent dividers sx={{ backgroundColor: hasLayouts ? '#f5f5f5' : 'inherit' }}>
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
                ) : hasLayouts ? (
                    <Box sx={{ position: 'relative', width: '100%', minHeight: '600px', p: 2 }}>
                        {panes.map((pane) => {
                            if (!pane.layout) return null;
                            const leftPct = (pane.layout.left / maxLayout.width) * 100;
                            const topPct = (pane.layout.top / maxLayout.height) * 100;
                            const widthPct = (pane.layout.width / maxLayout.width) * 100;
                            const heightPct = (pane.layout.height / maxLayout.height) * 100;

                            return (
                                <Paper
                                    key={pane.pane_id}
                                    variant="elevation"
                                    elevation={2}
                                    sx={{
                                        position: 'absolute',
                                        left: `calc(${leftPct}% + 16px)`,
                                        top: `calc(${topPct}% + 16px)`,
                                        width: `calc(${widthPct}% - 8px)`,
                                        height: `calc(${heightPct}% - 8px)`,
                                        overflowY: 'auto',
                                        p: 2,
                                        display: 'flex',
                                        flexDirection: 'column',
                                        backgroundColor: '#ffffff',
                                        border: '1px solid #e0e0e0',
                                        transition: 'all 0.2s ease-in-out',
                                        '&:hover': {
                                            boxShadow: 4,
                                            zIndex: 10
                                        }
                                    }}
                                >
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, borderBottom: '1px solid #eee', pb: 1 }}>
                                        <Typography variant="subtitle2" fontWeight="bold">
                                            {pane.window_name} 
                                            <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                                (Pane {pane.pane_index !== undefined ? pane.pane_index : pane.pane_id.replace('%', '')})
                                            </Typography>
                                        </Typography>
                                        <Chip
                                            label={pane.status}
                                            size="small"
                                            color={pane.status === 'RUNNING' ? 'success' : pane.status === 'WAITING' ? 'warning' : 'default'}
                                        />
                                    </Box>
                                    
                                    {pane.working_directory && (
                                        <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, fontFamily: 'monospace', display: 'block' }}>
                                            📁 {pane.working_directory.split('/').slice(-2).join('/')} {pane.git_branch && <Chip label={`🌿 ${pane.git_branch}`} size="small" sx={{ ml: 1, height: '16px', fontSize: '0.6rem' }} />}
                                        </Typography>
                                    )}
                                    
                                    {pane.initial_intent && (
                                        <Typography variant="caption" sx={{ mb: 1, fontStyle: 'italic', color: 'text.secondary', display: 'block' }}>
                                            Goal: {pane.initial_intent}
                                        </Typography>
                                    )}

                                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mt: 1, flexGrow: 1 }}>
                                        <strong>Status:</strong> {pane.task_summary}
                                    </Typography>
                                </Paper>
                            );
                        })}
                    </Box>
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
