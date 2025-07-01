import { Avatar, Badge, styled } from '@mui/material';
import useChat from '@/store';
import Robot from '@/assets/robot';

const StyledBadge = styled(Badge)(({ theme }) => ({
  '& .MuiBadge-badge': {
    backgroundColor: '#44b700',
    color: '#44b700',
    boxShadow: `0 0 0 2px ${theme.palette.background.paper}`,
    '&::after': {
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      borderRadius: '50%',
      animation: 'ripple 1.2s infinite ease-in-out',
      border: '1px solid currentColor',
      content: '""'
    }
  },
  '@keyframes ripple': {
    '0%': {
      transform: 'scale(.8)',
      opacity: 1
    },
    '100%': {
      transform: 'scale(2.4)',
      opacity: 0
    }
  }
}));

const BotAvatar = (props) => {
  const { settings } = useChat();
  return (
    <StyledBadge
      overlap="circular"
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      variant="dot"
      {...props}
    >
      {!settings.icon?.bot && (
        <Avatar
          sx={(theme) => ({ p: 0.8, background: theme.palette.grey[200] })}
          imgProps={{ style: { borderRadius: '50%' } }}
        >
          <Robot sx={{ fill: 'currentColor', color: 'primary.light' }} />
        </Avatar>
      )}
      {settings.icon?.bot && (
        <Avatar
          sx={(theme) => ({ p: 0.8, background: theme.palette.grey[200] })}
          src={settings.icon.bot}
          alt="bot_avatar"
          imgProps={{ style: { borderRadius: '50%' } }}
        />
      )}
    </StyledBadge>
  );
};

export default BotAvatar;
