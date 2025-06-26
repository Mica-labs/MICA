import React, { useState } from 'react';
import { useMemo } from 'react';
import { css } from '@emotion/react';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';
import { Box, Button, Grid, Link, Typography } from '@mui/material';

import { decodeAttachmentText, isAttachment } from '@/attachment';
import Bubble from './bubble';
import { useTranslation } from 'react-i18next';
import useChat from '@/store';
import { UploadDone, UploadLoading, UserNormalLoading } from './user-loading';
import BotTimeBox from './components/BotTimeBox';
import UserTimeBox from './components/UserTimeBox';
import BotAvatar from '../../components/BotAvatar';
import { useChatTheme } from '@/themes';
import { hideBotName } from '@/invoker';

const DotLoading = ({ size = 20 }) => {
  return (
    <Box
      sx={css`
        font-size: 0;
        .dots .dot1 {
          animation: load 1s infinite;
        }

        .dots .dot2 {
          animation: load 1s infinite;
          animation-delay: 0.2s;
        }

        .dots .dot3 {
          animation: load 1s infinite;
          animation-delay: 0.4s;
        }

        @keyframes load {
          0% {
            opacity: 0;
          }
          50% {
            opacity: 1;
          }
          100% {
            opacity: 0;
          }
        }
      `}
    >
      <svg
        id="dots"
        height={`${20}px`}
        viewBox="0 0 132 58"
        version="1.1"
        xmlns="http://www.w3.org/2000/svg"
        xmlnsXlink="http://www.w3.org/1999/xlink"
      >
        <g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
          <g className="dots" fill="#A3A3A3">
            <circle className="dot1" cx="25" cy="30" r="10"></circle>
            <circle className="dot2" cx="65" cy="30" r="10"></circle>
            <circle className="dot3" cx="105" cy="30" r="10"></circle>
          </g>
        </g>
      </svg>
    </Box>
  );
};

const PrimaryButton = ({ title, payload, disabled = false }) => {
  const sendMessage = useChat((s) => s.sendMessage);
  const theme = useChatTheme();
  return (
    <Box sx={{ float: 'left', mb: 1, mr: 1 }}>
      <Button
        size="small"
        sx={{ borderRadius: theme.borderRadius }}
        disableFocusRipple
        disableElevation
        variant="outlined"
        onClick={
          disabled
            ? () => void 0
            : () => sendMessage({ text: title, content: payload, type: 'button' })
        }
      >
        {title}
      </Button>
    </Box>
  );
};
const Buttons = ({ buttons }) => {
  const [more, setMore] = useState(false);
  const primaries = useMemo(
    () =>
      buttons
        .filter((b) => b.primary)
        .map((b, index) => <PrimaryButton key={b.payload + index} {...b} />),
    [buttons]
  );
  const secondaries = useMemo(
    () =>
      buttons
        .filter((b) => !b.primary)
        .map((b, index) => <PrimaryButton key={b.payload + index} {...b} />),
    [buttons]
  );
  const chatTheme = useChatTheme();
  const showMore = useMemo(() => buttons.some((b) => b.primary === false), [buttons]);
  return (
    <Box
      sx={(theme) => css`
        overflow: hidden;
        margin-bottom: ${theme.spacing(-1)};
      `}
    >
      {primaries}
      {!more && showMore && (
        <Box sx={{ float: 'left', mb: 1, mr: 1 }}>
          <Button
            size="small"
            sx={{ borderRadius: chatTheme.borderRadius }}
            disableFocusRipple
            disableElevation
            variant="outlined"
            onClick={() => setMore(true)}
          >
            更多...
          </Button>
        </Box>
      )}
      {more && secondaries}
    </Box>
  );
};
const Attachment = ({ name, href }) => {
  return (
    <Bubble>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <TextSnippetIcon sx={{ color: 'info.light' }} />
        <Typography variant="body2">
          <Link href={`${href}`}>{name}</Link>
        </Typography>
      </Box>
    </Bubble>
  );
};

const SimilarQuestions = ({ similarQuestions }) => {
  const { t } = useTranslation();
  const sendMessage = useChat((s) => s.sendMessage);
  const onClickItem = (item) => {
    sendMessage({ text: item.query, content: item.id, type: 'link' });
  };
  return (
    <Box display="flex" flexDirection="column">
      <Typography variant="body2">{t`relation`}</Typography>
      {similarQuestions.map((item, index) => (
        <Box
          component="span"
          display="block"
          overflow="hidden"
          textOverflow="ellipsis"
          whiteSpace="nowrap"
          sx={(theme) => ({
            ':hover': {
              color: theme.palette.primary.main,
              textDecoration: 'underline'
            },
            color: theme.palette.primary.main,
            cursor: 'pointer',
            fontSize: '14px'
          })}
          key={item.id}
          onClick={() => onClickItem(item)}
          title={item.query}
        >
          {index + 1}.{item.query}
        </Box>
      ))}
    </Box>
  );
};
const Links = ({ links }) => {
  const { t } = useTranslation();
  return (
    <Box display="flex" flexDirection="column">
      <Typography variant="body2">{t`links`}</Typography>
      {links.map((link) => (
        <Box
          key={link.url}
          component="a"
          display="block"
          overflow="hidden"
          textOverflow="ellipsis"
          whiteSpace="nowrap"
          sx={(theme) => ({
            ':hover': {
              textDecoration: 'underline'
            },
            color: theme.palette.primary.main,
            cursor: 'pointer',
            fontSize: '14px'
          })}
          href={link.url}
          target="_blank"
        >
          {link.url}
        </Box>
      ))}
    </Box>
  );
};
const Timeout = ({ id, content }) => {
  const { t } = useTranslation();
  const sendMessage = useChat((s) => s.sendMessage);
  const onClick = () => {
    sendMessage(content.sendParams);
  };
  const theme = useChatTheme();

  return (
    <>
      <Bubble>
        <Typography variant="body2">{content.label}</Typography>
      </Bubble>
      <Box mt={1}>
        <Button
          sx={{ borderRadius: theme.borderRadius }}
          variant="outlined"
          size="small"
          onClick={onClick}
        >
          {t`retry`}
        </Button>
      </Box>
    </>
  );
};
const Network = ({ content }) => {
  return <Bubble>{content}</Bubble>;
};

function renderMessage({ id, type, content, evaluate, msgId, helpful }) {
  switch (type) {
    case 'loading':
      return (
        <Box sx={{ display: 'flex', alignItems: 'flex-end' }}>
          <Bubble>
            <DotLoading />
          </Bubble>
        </Box>
      );
    case 'text':
      if (isAttachment(content)) {
        const props = decodeAttachmentText(content);
        return <Attachment {...props} />;
      }
      return (
        <Box sx={{ display: 'flex', alignItems: 'flex-end' }}>
          <Bubble evaluate={evaluate} shortId={id} msgId={msgId} helpful={helpful}>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-line', wordBreak: 'break-word' }}>
              {content}
            </Typography>
          </Bubble>
        </Box>
      );
    case 'img':
      return (
        <Grid container direction="column" wrap="nowrap" spacing={1}>
          {content.map((image) => (
            <Grid item xs key={image.id}>
              <Bubble sx={{ fontSize: 0 }}>
                <img
                  src={image.src}
                  alt="#"
                  width="100%"
                  height={200}
                  style={{ objectFit: 'cover' }}
                />
              </Bubble>
            </Grid>
          ))}
        </Grid>
      );
    case 'button':
      return <Buttons buttons={content} />;
    case 'similarQuestions':
      return <SimilarQuestions similarQuestions={content} />;
    case 'links':
      return <Links links={content} />;
    case 'timeout':
      return <Timeout id={id} content={content} />;
    case 'network':
      return <Network content={content} />;
    default:
      return null;
  }
}

const Message = ({ message, isGroupBoundary }) => {
  const {
    settings: { name }
  } = useChat();
  const components = useMemo(() => {
    const { id, from, type, date, content, evaluate, msgId, helpful, loading } = message;
    if (from === 'agent') {
      return (
        <Grid item xs key={id}>
          <Box sx={{ display: 'flex', alignItems: 'flex-end' }}>
            <BotAvatar
              sx={{
                mr: 1,
                opacity: isGroupBoundary ? 1 : 0
              }}
            />
            <Box
              sx={{ mr: type !== 'evaluate' ? 7 : 2, flex: 1, minWidth: 0, alignSelf: 'center' }}
            >
              <Typography
                className="agent-title"
                variant="subtitle2"
                sx={{ color: 'grey.700', mb: 0.5 }}
              >
                {/* hidden bot name*/}
                {!hideBotName && name}
              </Typography>
              {renderMessage({
                id,
                type,
                content,
                date,
                evaluate,
                msgId,
                helpful
              })}
            </Box>
          </Box>
          {isGroupBoundary && <BotTimeBox date={date} />}
        </Grid>
      );
    } else {
      return (
        <Grid item xs key={id}>
          <Box
            sx={{
              ml: 10,
              flex: 1,
              minWidth: 0,
              display: 'flex',
              alignItems: 'flex-end',
              flexDirection: 'column',
              pr: 1
            }}
          >
            <Typography
              className="client-title"
              variant="subtitle2"
              sx={{ color: 'grey.700', mb: 0.5 }}
            >
              Me
            </Typography>
            {loading && type !== 'file' && <UserNormalLoading />}
            {loading && type === 'file' && <UploadLoading id={id} initialFile={content} />}
            {!loading && type === 'text' && (
              <Bubble from="client">
                <Typography variant="body2">{content}</Typography>
              </Bubble>
            )}
            {!loading &&
              type === 'button' &&
              content.map((item) => <PrimaryButton key={item.payload} {...item} disabled />)}
            {!loading && type === 'fileDone' && <UploadDone content={content} />}
          </Box>
          {isGroupBoundary && <UserTimeBox date={date} preDisplay={message.preDisplay} />}
        </Grid>
      );
    }
  }, [isGroupBoundary, message, name]);

  return (
    <Grid container wrap="nowrap" spacing={1} direction="column">
      {components}
    </Grid>
  );
};

export default Message;
