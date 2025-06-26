import { useMemo } from 'react';
import { theme } from './invoker';

const themes = {
  default: {
    primary: {
      main: '#0041ff',
      background: '#0041ff'
    },
    borderRadius: '2px'
  },
  'linear-sky': {
    primary: {
      main: '#1b62e8',
      background: 'linear-gradient(90deg, #1b62e8,#08abf7)'
    },
    borderRadius: '12px'
  }
};

export function useChatTheme() {
  return useMemo(() => themes[theme || 'default'], []);
}

export default themes;
