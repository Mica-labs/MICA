import React from 'react';
import { Box, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';

const CommonError = ({ error }) => {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        height: '70%',
        textAlign: 'center',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'column'
      }}
    >
      <Typography
        component="b"
        variant="h1"
        sx={{
          fontSize: 70,
          color: 'text.primary'
        }}
      >
        {t`errors.oops`}
      </Typography>
      <Typography
        variant="subtitle1"
        sx={{
          fontSize: 20,
          color: 'text.disabled',
          opacity: 0.5
        }}
      >
        {t`errors.wrong`}
      </Typography>
      {process.env.NODE_ENV !== 'production' && error && <Typography>{String(error)}</Typography>}
    </Box>
  );
};

export default CommonError;
