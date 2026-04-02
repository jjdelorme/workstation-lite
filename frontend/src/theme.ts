import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  colorSchemes: {
    light: true,
    dark: true,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 20, // M3 pill-shaped
          textTransform: 'none',
        },
      },
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

export default theme;
