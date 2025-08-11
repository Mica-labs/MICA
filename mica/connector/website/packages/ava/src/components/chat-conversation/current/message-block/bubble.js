import React from 'react';
import { Box } from '@mui/material';
import useChat from '@/store';
import { useChatTheme } from '@/themes';

const Bubble = ({ children, from = 'agent', evaluate, shortId, msgId, helpful }) => {
  const chatTheme = useChatTheme();
  return (
    <Box
      sx={(theme) => ({
        background: from === 'agent' ? theme.palette.grey[200] : chatTheme.primary.background,
        color: from === 'agent' ? theme.palette.text.primary : theme.palette.primary.contrastText,
        padding: 1.2,
        display: 'inline-flex',
        gap: 1,
        borderRadius: chatTheme.borderRadius
      })}
    >
      <Box sx={{ flex: 1 }}>{children}</Box>
    </Box>
  );
};

export default Bubble;
