import React, { useEffect } from 'react';
import { Box } from '@mui/material';
import { css } from '@mui/material/styles';

import { isIntegrated } from '@/invoker';
import BubbleButton from '../bubble-button';
import BubbleChat from '../bubble-chat';
import { store } from '@/store';
import { useChatTheme } from '@/themes';

const Ava = () => {
  useEffect(() => {
    store.getState().initial();
  }, []);
  const theme = useChatTheme();
  return (
    <Box
      sx={css`
        height: 100%;
        height: calc(var(--app-height));
        width: 100vw;
        position: relative;
        border-radius: ${theme.borderRadius};
      `}
    >
      <BubbleChat />
      {isIntegrated && <BubbleButton />}
    </Box>
  );
};

export default Ava;
