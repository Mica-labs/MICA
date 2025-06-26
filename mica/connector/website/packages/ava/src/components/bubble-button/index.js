import React from 'react';
import { Box, Zoom } from '@mui/material';
import { styled } from '@mui/material/styles';

import BubbleIcon from '@/assets/bubble';
import CloseIcon from '@/assets/close';
import useChat from '@/store';
import { useChatTheme } from '@/themes';

const Container = styled(Box)`
  height: 60px;
  width: 60px;
  position: absolute;
  bottom: 0;
  right: 0;

  transition: box-shadow 150ms ease-in-out 0s;
  box-shadow: rgb(0 0 0 / 10%) 0px 1px 6px, rgb(0 0 0 / 20%) 0px 2px 24px;

  &:focus,
  &:hover {
    box-shadow: rgb(0 0 0 / 20%) 0px 2px 10px, rgb(0 0 0 / 30%) 0px 4px 28px;
  }
`;

const IconWrapper = styled(Box)`
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  height: 100%;
  width: 100%;
  justify-content: center;
  align-items: center;
`;

const BubbleButton = () => {
  const { visible, toggleVisible } = useChat((s) => ({
    visible: s.visible,
    toggleVisible: s.toggleVisible
  }));
  const theme = useChatTheme();
  if (visible) return null;
  return (
    <Container
      onClick={toggleVisible}
      sx={{ background: theme.primary.background, borderRadius: theme.borderRadius }}
    >
      <Zoom in={visible}>
        <IconWrapper>
          <CloseIcon />
        </IconWrapper>
      </Zoom>
      <Zoom in={!visible}>
        <IconWrapper>
          <BubbleIcon />
        </IconWrapper>
      </Zoom>
    </Container>
  );
};

export default BubbleButton;
