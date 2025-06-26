import { Box, Typography } from '@mui/material';
import dayjs from 'dayjs';
import React, { useMemo } from 'react';
import EmailIcon from '@mui/icons-material/Email';
import ForwardToInboxIcon from '@mui/icons-material/ForwardToInbox';
import { useTranslation } from 'react-i18next';

const UserTimeBox = ({ date, preDisplay }) => {
  const { i18n } = useTranslation();
  const time = useMemo(
    () => dayjs(date).locale(i18n.language).format('hh:mm A'),
    [date, i18n.language]
  );
  return (
    <Box
      sx={{
        py: 0.5,
        ml: 5,
        pr: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end'
      }}
    >
      <Typography
        variant="body2"
        sx={{ mr: 0.5, whiteSpace: 'nowrap', fontSize: 10, color: 'grey.400' }}
      >
        {time}
      </Typography>
      <Box sx={{ fontSize: 0, lineHeight: 1, mt: '-1px' }}>
        {preDisplay ? (
          <ForwardToInboxIcon sx={{ color: 'grey.400', width: 12, height: 12 }} />
        ) : (
          <EmailIcon sx={{ color: 'success.light', width: 12, height: 12 }} />
        )}
      </Box>
    </Box>
  );
};

export default UserTimeBox;
