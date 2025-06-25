import React from 'react';
import { Box } from '@mui/material';
import ThumbUpOffAltIcon from '@mui/icons-material/ThumbUpOffAlt';
import ThumbDownOffAltIcon from '@mui/icons-material/ThumbDownOffAlt';
import useChat from '@/store';
import { useChatTheme } from '@/themes';

const Bubble = ({ children, from = 'agent', evaluate, shortId, msgId, helpful }) => {
  const { settings, evaluateMessage } = useChat();
  const handleClick = (payload) => {
    // api
    evaluateMessage(payload, shortId, msgId);
  };
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
      {settings.survey && from === 'agent' && evaluate && (
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            alignItems: 'center',
            height: 'max-content',
            fontSize: 12
          }}
        >
          {!helpful && (
            <>
              <ThumbDownOffAltIcon
                sx={{ width: 16, height: 16, cursor: 'pointer' }}
                onClick={() => handleClick('bad')}
              />
              <ThumbUpOffAltIcon
                sx={{ width: 16, height: 16, cursor: 'pointer' }}
                onClick={() => handleClick('helped')}
              />
            </>
          )}
          {helpful === 'helped' && (
            <ThumbUpOffAltIcon
              sx={(theme) => ({
                width: 16,
                height: 16,
                background: theme.palette.grey[50],
                borderRadius: '2px'
              })}
            />
          )}
          {helpful === 'bad' && (
            <ThumbDownOffAltIcon
              sx={(theme) => ({
                width: 16,
                height: 16,
                background: theme.palette.grey[50],
                borderRadius: '2px'
              })}
            />
          )}
        </Box>
      )}
    </Box>
  );
};

export default Bubble;
