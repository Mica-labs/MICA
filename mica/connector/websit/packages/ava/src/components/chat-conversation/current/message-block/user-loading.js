import React, { useEffect } from 'react';
import { Box, Button, CircularProgress, LinearProgress, Typography } from '@mui/material';
import { uploadFile } from '@/services';
import useChat, { getAuthentication } from '@/store';
import { useTranslation } from 'react-i18next';
import ArticleIcon from '@mui/icons-material/Article';
import Bubble from './bubble';
import { useChatTheme } from '@/themes';

export const UserNormalLoading = () => {
  return <CircularProgress size="16px" />;
};
export const UploadLoading = ({ id, initialFile }) => {
  if (initialFile instanceof File) return <UploadFile id={id} initialFile={initialFile} />;
  return <ReUpload />;
};
const UploadFile = ({ id, initialFile }) => {
  const { t } = useTranslation();
  const { settings, current, resetFileMessage } = useChat();
  useEffect(() => {
    if (initialFile instanceof File) {
      uploadFile(initialFile, getAuthentication(settings), current)
        .then((data) => {
          resetFileMessage(id, 'success', data);
        })
        .catch((e) =>
          resetFileMessage(id, 'error', e.message || e.data?.message || t`errors.unknown`)
        );
    }
  }, [current, initialFile, settings, resetFileMessage, id, t]);
  return (
    <Bubble>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <ArticleIcon sx={{ width: 16, height: 16 }} />
        <Typography variant="body2">{initialFile.name}</Typography>
      </Box>
      <LinearProgress />
    </Bubble>
  );
};

const imageTypes = ['png', 'avg', 'jpg', 'jpeg', 'gif', 'webp'];
export const UploadDone = ({ content }) => {
  return (
    <Bubble>
      {content.status === 'success' && imageTypes.includes(content.result.type) && (
        <img
          alt="upload"
          src={content.result.href}
          width="100%"
          height={200}
          style={{ objectFit: 'cover', background: 'white' }}
        />
      )}
      <Box display="flex" alignItems="center" gap={1}>
        <ArticleIcon sx={{ width: 16, height: 16 }} />
        <Typography
          component="a"
          target="_blank"
          href={content.result.href}
          variant="body2"
          sx={(theme) => ({
            width: 'fit-content',
            maxWidth: '280px',
            display: 'inline-block',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            cursor: 'pointer',
            color: theme.palette.primary.main,
            ':hover': {
              textDecoration: 'underline'
            }
          })}
        >
          {content.result.name}
        </Typography>
      </Box>
      {content.status === 'error' && <ReUpload />}
    </Bubble>
  );
};
const ReUpload = () => {
  const { t } = useTranslation();
  const { sendUploadMessage, sending } = useChat();
  const onInputChange = (evt) => {
    const file = evt.target.files[0];
    console.log(evt.target);
    if (file) {
      sendUploadMessage(file);
    }
  };
  const theme = useChatTheme();
  return (
    <Button color="secondary" sx={{ borderRadius: theme.borderRadius }}>
      <label htmlFor="user_upload" style={{ display: 'flex', alignItems: 'center' }}>
        {t`retry`}
      </label>
      <input
        id="user_upload"
        type="file"
        multiple={false}
        style={{ display: 'none' }}
        onChange={onInputChange}
        disabled={sending}
      />
    </Button>
  );
};
