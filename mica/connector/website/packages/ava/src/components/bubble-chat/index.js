import React, { useMemo } from 'react';
import { css } from '@emotion/react';
import {
  Add as AddIcon,
  ArrowBackIosNew as ArrowBackIosNewIcon,
  Close as CloseIcon,
  Fullscreen as FullscreenIcon,
  FullscreenExit as FullscreenExitIcon,
  AutoDelete as AutoDeleteIcon
} from '@mui/icons-material';

import { Box, Collapse, IconButton, Typography } from '@mui/material';

import BubbleIcon from '@/assets/bubble';
import CommonError from '@/error';
import ErrorBoundary from '@/ErrorBoundary';

import CurrentConversation from '../chat-conversation/current';
import History from '../chat-conversation/history';
import useChat from '@/store/index';
import { autoOpen, isIntegrated, isOnlyChatbot } from '@/invoker';
import { useChatTheme } from '@/themes';

const LinkBack = () => {
  const { route, redirectHistory } = useChat((s) => ({
    route: s.route,
    redirectHistory: s.redirectHistory
  }));
  return (
    <Collapse in={route === 'conversation'} orientation="horizontal">
      <IconButton onClick={redirectHistory}>
        <ArrowBackIosNewIcon
          sx={(theme) => ({
            color: theme.palette.primary.contrastText
          })}
        />
      </IconButton>
    </Collapse>
  );
};
const ClearHistory = () => {
  const { route, clearHistory } = useChat((s) => ({
    route: s.route,
    clearHistory: s.clearHistory
  }));
  return (
    <Collapse in={route === 'history'} orientation="horizontal">
      <IconButton onClick={clearHistory}>
        <AutoDeleteIcon sx={(theme) => ({ color: theme.palette.primary.contrastText })} />
      </IconButton>
    </Collapse>
  );
};
const Creator = () => {
  const { fetching, create } = useChat((s) => ({
    fetching: s.creating,
    create: s.createConversation
  }));
  return (
    <IconButton size="large" disabled={fetching} onClick={create}>
      <AddIcon
        sx={(theme) => ({
          opacity: fetching ? 0.6 : 1,
          color: theme.palette.primary.contrastText
        })}
      />
    </IconButton>
  );
};
const FullscreenTrigger = () => {
  const { full, toggleFull } = useChat((s) => ({ full: s.full, toggleFull: s.toggleFull }));
  return (
    <IconButton size="large" onClick={toggleFull}>
      {full ? (
        <FullscreenExitIcon
          sx={(theme) => ({
            color: theme.palette.primary.contrastText
          })}
        />
      ) : (
        <FullscreenIcon
          sx={(theme) => ({
            color: theme.palette.primary.contrastText
          })}
        />
      )}
    </IconButton>
  );
};
const CloseTrigger = () => {
  const toggleVisible = useChat((s) => s.toggleVisible);
  return (
    <IconButton size="large" onClick={toggleVisible}>
      <CloseIcon
        sx={(theme) => ({
          color: theme.palette.primary.contrastText
        })}
      />
    </IconButton>
  );
};
const BubbleChat = () => {
  const {
    full,
    route,
    settings: { name },
    createError
  } = useChat();
  const theme = useChatTheme();

  const containerSx = useMemo(() => {
    if (isIntegrated) {
      if (full) {
        return css`
          overflow: hidden;
          position: absolute;
          right: 0px;
          top: 0px;
          z-index: 0;
          width: 100%;
          height: 100%;
          background: white;
          box-shadow: rgb(0 0 0 / 10%) 0px 1px 6px, rgb(0 0 0 / 10%) 0px 2px 24px;
          transition: top 0.25s ease-in-out 0s;
          display: flex;
          flex-direction: column;
        `;
      }
      return css`
        overflow: hidden;
        width: 100%;
        height: var(--app-height);
        background: white;
        box-shadow: rgb(0 0 0 / 10%) 0px 1px 6px, rgb(0 0 0 / 10%) 0px 2px 24px;
        transition: top 0.25s ease-in-out 0s;
        display: flex;
        flex-direction: column;
        border-left: 1px solid #1b62e8;
        border-bottom: 1px solid #08abf7;
        border-right: 1px solid #08abf7;
        border-radius: ${theme.borderRadius};
      `;
    }
    return css`
      height: 100%;
      height: calc(var(--app-height));
      width: 100%;
      display: flex;
      flex-direction: column;
      border-radius: ${theme.borderRadius};
    `;
  }, [full, theme]);
  return (
    <Box sx={containerSx}>
      <Box
        sx={css`
          background: ${theme.primary.background};
          height: 56px;
          display: flex;
          padding: 16px 8px 16px 16px;
          align-items: center;
          border-top-right-radius: ${isIntegrated ? theme.borderRadius : '0px'};
          border-top-left-radius: ${isIntegrated ? theme.borderRadius : '0px'};
        `}
      >
        {!isOnlyChatbot && <LinkBack />}
        <Box sx={{ mx: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <BubbleIcon />
        </Box>
        <Typography variant="h6" sx={{ flex: 1, ml: 1 }} color="primary.contrastText">
          {name}
        </Typography>
        <ClearHistory />
        {(!isOnlyChatbot || autoOpen) && <Creator />}
        {isIntegrated && (
          <>
            <FullscreenTrigger />
            <CloseTrigger />
          </>
        )}
      </Box>
      <ErrorBoundary>
        <Box sx={{ flex: 1, minHeight: 0, borderRadius: theme.borderRadius }}>
          {createError ? (
            <CommonError error={createError} />
          ) : (
            <>
              {route === 'conversation' && <CurrentConversation />}
              {route === 'history' && <History />}
            </>
          )}
        </Box>
      </ErrorBoundary>
    </Box>
  );
};

const BubbleTransform = () => {
  const theme = useChatTheme();
  const visible = useChat((s) => s.visible);
  if (!visible) return null;
  return (
    <Box sx={{ height: '100%', borderRadius: theme.borderRadius }}>
      <Box
        sx={{
          height: '100%',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          borderRadius: theme.borderRadius
        }}
      >
        <BubbleChat />
      </Box>
    </Box>
  );
};

export default BubbleTransform;
