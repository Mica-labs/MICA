import { Box, Typography } from '@mui/material';
import dayjs from 'dayjs';
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

const HistoryTimeBox = ({ date, from, name }) => {
  const { i18n } = useTranslation();
  const time = useMemo(() => dayjs(date).locale(i18n.language).fromNow(), [date, i18n.language]);
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-end' }}>
      <Typography
        variant="subtitle2"
        sx={{
          flex: 1,
          minWidth: 0,
          fontWeight: 700,
          color: 'grey.700'
        }}
      >
        {from === 'agent' ? name : 'Me'}
      </Typography>
      <Typography color="grey.500" variant="body2">
        {time}
      </Typography>
    </Box>
  );
};

export default HistoryTimeBox;
