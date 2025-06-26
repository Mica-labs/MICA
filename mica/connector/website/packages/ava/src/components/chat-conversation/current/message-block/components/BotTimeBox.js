import { Box, Typography } from '@mui/material';
import dayjs from 'dayjs';
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

const BotTimeBox = ({ date }) => {
  const { i18n } = useTranslation();
  const time = useMemo(
    () => dayjs(date).locale(i18n.language).format('hh:mm A'),
    [date, i18n.language]
  );
  return (
    <Box sx={{ my: 0.5, ml: 5 }}>
      <Typography
        variant="body2"
        sx={{ ml: 1, whiteSpace: 'nowrap', fontSize: 10, color: 'grey.400' }}
      >
        {time}
      </Typography>
    </Box>
  );
};
export default BotTimeBox;
