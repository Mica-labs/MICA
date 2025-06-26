import React, { useEffect, useMemo, useRef } from 'react';
import dayjs from 'dayjs';
import SimpleBar from 'simplebar-react';
import { Box, CircularProgress, Link, Typography } from '@mui/material';

import MessageBlock from './message-block';
import { useTranslation } from 'react-i18next';
import ChatInput from '@/components/chat-input/index';
import useChat from '@/store/index';
import { useChatTheme } from '@/themes';

const Conversation = () => {
  const ref = useRef();
  const { t } = useTranslation();
  const { visible, creating, current, conversations, createConversation, createError } = useChat();
  const conversation = useMemo(
    () => conversations.find((o) => o.id === current) || {},
    [current, conversations]
  );
  const { messages = [] } = conversation;
  const isTimeout = dayjs((messages[messages.length - 1] || { date: new Date().getTime() }).date)
    .add(30, 'minute')
    .isBefore(new Date());

  useEffect(() => {
    if (visible && !creating && !current && !createError) {
      createConversation();
    }
  }, [createConversation, createError, current, creating, visible]);

  useEffect(() => {
    if (visible && !creating && conversation) {
      ref.current.getScrollElement().scrollTop = 999999;
    }
  }, [creating, visible, conversation]);
  const theme = useChatTheme();
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: '2px',
        borderRadius: theme.borderRadius
      }}
    >
      {creating && (
        <Box
          sx={{
            flex: 0.8,
            minHeight: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <CircularProgress />
        </Box>
      )}
      {!creating && (
        <>
          <Box sx={{ flex: 1, minHeight: '0px', borderRadius: theme.borderRadius }}>
            <SimpleBar ref={ref} style={{ height: '100%' }}>
              <Box sx={{ padding: 1 }}>
                <MessageBlock conversation={conversation} />
              </Box>
            </SimpleBar>
          </Box>
          <Box
            sx={{
              p: 1,
              mr: -1,
              display: 'flex',
              width: '100%',
              minHeight: 56,
              alignItems: 'center'
            }}
          >
            {isTimeout && (
              <Box sx={{ textAlign: 'center', minWidth: 0, flex: 1 }}>
                <Typography variant="body2" sx={{ color: 'grey.700', lineHeight: '56px' }}>
                  {t`errors.session.prefix`}
                  <Link underline="hover" sx={{ cursor: 'pointer' }} onClick={createConversation}>
                    {t`errors.session.subfix`}
                  </Link>
                </Typography>
              </Box>
            )}
            {!isTimeout && <ChatInput />}
          </Box>
        </>
      )}
    </Box>
  );
};

export default Conversation;
