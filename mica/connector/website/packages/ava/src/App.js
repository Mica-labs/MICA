import { useEffect } from 'react';
import { css, Global } from '@emotion/react';
import CssBaseline from '@mui/material/CssBaseline';
import { createTheme, ThemeProvider } from '@mui/material/styles';

import Ava from './components/entry';
import ErrorBoundary from './ErrorBoundary';
import { theme as th } from './invoker';
import themes from './themes';

const globalStyles = css`
  :root {
    --app-height: 100%;
  }

  html,
  body {
    height: 100%;
    background: transparent;
    padding: 0;
    margin: 0;
    overflow: hidden;
  }

  #root {
    height: 100%;
  }
`;

const theme = createTheme({
  palette: {
    primary: {
      main: themes[th || 'default'].primary.main
    }
  }
});

function App() {
  useEffect(() => {
    const correctAppHeight = () => {
      const doc = document.documentElement;
      doc.style.setProperty('--app-height', `${window.innerHeight}px`);
    };
    window.addEventListener('resize', correctAppHeight);
    correctAppHeight();
    return () => {
      window.removeEventListener('resize', correctAppHeight);
    };
  }, []);
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Global styles={globalStyles} />
      <ErrorBoundary global>
        <Ava />
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
