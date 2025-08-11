import React from 'react';
import dayjs from 'dayjs';
import SimpleBar from 'simplebar-react';
import { css } from '@emotion/react';
import { Box, Typography, Button } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';

import { isAttachment } from '@/attachment';
import useChat from '@/store';
import HistoryTimeBox from './components/HistoryTimeBox';
import BotAvatar from '../components/BotAvatar';
import { useTranslation } from 'react-i18next';
import { useChatTheme } from '@/themes';

const History = () => {
  const { t } = useTranslation();
  const {
    fetching,
    settings: { name },
    conversations,
    redirectConversation,
    createConversation
  } = useChat(
    ({ fetching, settings, conversations, redirectConversation, createConversation }) => ({
      fetching,
      settings,
      conversations,
      redirectConversation,
      createConversation
    })
  );
  const theme = useChatTheme();
  return (
    <Box sx={{ height: '100%' }}>
      {conversations.length > 0 && (
        <SimpleBar style={{ height: '100%' }}>
          <Box component="ul" sx={{ p: 0, margin: 0 }}>
            {conversations
              .filter((o) => o.messages.length)
              .map(({ id, messages }) => {
                const ordered = messages.slice(0).reverse();
                const [lastMessage] = ordered;
                let lastTextMessage = ordered.find((o) => o.type === 'text');
                if (isAttachment(lastTextMessage.content)) {
                  lastTextMessage = { content: '...' };
                }
                const isTimeout = dayjs(lastMessage.date).add(30, 'minute').isBefore(new Date());
                return (
                  <Box
                    component="li"
                    key={id}
                    sx={(theme) => css`
                      padding-right: ${theme.spacing(1)};
                      list-style: none;
                      border-bottom: 1px solid ${theme.palette.grey[200]};
                      &:hover {
                        background: ${theme.palette.grey[100]};
                      }
                    `}
                    onClick={() => redirectConversation(id)}
                  >
                    <Box
                      sx={(theme) => ({
                        padding: theme.spacing(1),
                        opacity: isTimeout ? 0.5 : 1,
                        display: 'flex',
                        justifyContent: 'center',
                        cursor: 'pointer'
                      })}
                    >
                      <BotAvatar invisible />
                      <Box sx={{ flex: 1, ml: 1, minWidth: 0 }}>
                        <HistoryTimeBox
                          date={lastMessage.date}
                          from={lastMessage.from}
                          name={name}
                        />
                        <Typography variant="body2" color="grey.700" noWrap>
                          {lastTextMessage.content}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                );
              })}
          </Box>
        </SimpleBar>
      )}
      {conversations.length === 0 && (
        <Box
          sx={{ height: '80%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
        >
          <Button
            variant="contained"
            sx={{ borderRadius: theme.borderRadius }}
            disabled={fetching}
            onClick={createConversation}
          >
            <AddIcon
              sx={(theme) => ({
                opacity: fetching ? 0.6 : 1,
                cursor: fetching ? 'not-allow' : 'pointer'
              })}
            />
            {t`history.createConversation`}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default History;
