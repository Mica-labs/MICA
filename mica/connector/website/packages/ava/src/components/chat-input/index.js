import React, { useEffect, useMemo, useRef } from 'react';
import { useImmer } from 'use-immer';
import ForwardToInboxTwoToneIcon from '@mui/icons-material/ForwardToInboxTwoTone';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { Box, InputBase } from '@mui/material';

import { useTranslation } from 'react-i18next';
import useChat from '@/store';
import { useChatTheme } from '@/themes';

const ChatInput = () => {
  const ref = useRef();
  const { t } = useTranslation();
  const {
    settings,
    sendMessage,
    sending,
    isPreview,
    submitMultipleInputCache,
    current,
    multipleInputCache
  } = useChat();
  const showSubmitMultiple = useMemo(
    () => multipleInputCache[current] && multipleInputCache[current].actived,
    [current, multipleInputCache]
  );
  const [{ text }, setState] = useImmer({ text: '' });
  const onClickHandler = async () => {
    if (sending) return;
    if (text) {
      sendMessage({ text, type: 'text' });
      setState((draft) => void (draft.text = ''));
    }
  };
  const onChangeHandler = (e) => setState((draft) => void (draft.text = e.target.value));
  const onKeyPressHandler = (e) => {
    if (sending) return;
    if (e.charCode === 13 || e.code === 'Enter') {
      onClickHandler();
    }
  };
  useEffect(() => {
    if (!sending) {
      ref.current.focus();
      setTimeout(() => {
        ref.current?.focus();
      }, 0);
    }
  }, [sending]);
  const chatTheme = useChatTheme();
  return (
    <>
      {settings.upload && <UploadInput />}
      <InputBase
        inputRef={ref}
        value={text}
        placeholder={t`send`}
        onChange={onChangeHandler}
        onKeyPress={onKeyPressHandler}
        disabled={sending || isPreview}
        sx={(theme) => ({
          width: '100%',
          fontSize: 14,
          background: theme.palette.grey[200],
          px: 2,
          py: 1,
          borderRadius: chatTheme.borderRadius
        })}
        endAdornment={
          <ForwardToInboxTwoToneIcon
            onClick={onClickHandler}
            sx={(theme) => ({
              cursor: 'pointer',
              color: text ? theme.palette.primary.main : theme.palette.grey[500]
            })}
          />
        }
      ></InputBase>
      {showSubmitMultiple && (
        <Box
          display="flex"
          alignItems="center"
          height="100%"
          marginLeft={1}
          sx={(theme) => ({
            background: theme.palette.grey[200],
            paddingLeft: 1,
            paddingRight: 1,
            cursor: 'pointer',
            borderRadius: chatTheme.borderRadius
          })}
        >
          <CheckBoxIcon
            onClick={submitMultipleInputCache}
            sx={(theme) => ({
              cursor: 'pointer',
              color: theme.palette.success.main
            })}
          />
        </Box>
      )}
    </>
  );
};

const UploadInput = () => {
  const { sendUploadMessage, sending, isPreview } = useChat();
  const onInputChange = (evt) => {
    const file = evt.target.files[0];
    if (file) {
      sendUploadMessage(file);
    }
  };
  const chatTheme = useChatTheme();
  return (
    <Box
      display="flex"
      alignItems="center"
      height="100%"
      marginRight={1}
      sx={(theme) => ({
        background: theme.palette.grey[200],
        paddingLeft: 1,
        paddingRight: 1,
        cursor: 'pointer',
        borderRadius: chatTheme.borderRadius
      })}
    >
      <label htmlFor="user_upload" style={{ display: 'flex', alignItems: 'center' }}>
        <CloudUploadIcon
          sx={(theme) => ({ cursor: 'pointer', color: theme.palette.primary.main })}
        />
      </label>
      <input
        id="user_upload"
        type="file"
        multiple={false}
        style={{ display: 'none' }}
        onChange={onInputChange}
        disabled={sending || isPreview}
      />
    </Box>
  );
};

export default ChatInput;
