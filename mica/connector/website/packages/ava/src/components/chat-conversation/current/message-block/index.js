import React from 'react';
import dayjs from 'dayjs';
import { css } from '@emotion/react';
import { Grid } from '@mui/material';

import Message from './message';

const MessageBlock = ({ conversation }) => {
  const { messages = [] } = conversation;
  return (
    <Grid
      container
      wrap="nowrap"
      spacing={1}
      direction="column"
      sx={css`
        .from-client + .from-client .client-title {
          display: none;
        }
        .from-agent + .from-agent .agent-title {
          display: none;
        }
      `}
    >
      {messages.map((message, index, { length }) => {
        const next = messages[index + 1];
        const isGroupBoundary =
          index + 1 >= length ||
          message.from !== next.from ||
          dayjs(message.date).add('1', 'minute').isBefore(next.date);

        return (
          <Grid
            className={isGroupBoundary ? `from-${message.from} boundary` : `from-${message.from}`}
            key={message.id}
            item
            xs
          >
            <Message message={message} isGroupBoundary={isGroupBoundary} />
          </Grid>
        );
      })}
    </Grid>
  );
};

export default MessageBlock;
