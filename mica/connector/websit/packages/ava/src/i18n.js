import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import resources from './locale';

import 'dayjs/locale/zh';
import 'dayjs/locale/en';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { DEFAULT_LANG } from './invoker';

dayjs.extend(relativeTime);
i18next.on('languageChanged', (lng) => {
  // change global dayjs locale
  dayjs.locale(lng);
});

i18next.use(initReactI18next).init({
  resources,
  lng: DEFAULT_LANG,
  fallbackLng: DEFAULT_LANG,
  interpolation: {
    escapeValue: false
  }
});
export default i18next;
