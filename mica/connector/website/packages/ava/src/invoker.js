import QueryString from 'qs';
import * as base64 from 'js-base64';

function transformStringToBoolean(object) {
  return Object.entries(object).reduce((p, c) => {
    const [key, value] = c;
    let val = value;
    if (value === 'true') {
      val = true;
    }
    if (value === 'false') {
      val = false;
    }
    return { ...p, [key]: val };
  }, {});
}

export const qs = (() => {
  if (window.STATIC_MODE && window.CHATBOT_CONFIG) {
    return transformStringToBoolean({
      bot_name: window.CHATBOT_CONFIG.bot_name,
      name: window.CHATBOT_CONFIG.name,
      theme: window.CHATBOT_CONFIG.theme,
      minimize: window.CHATBOT_CONFIG.minimize
    });
  }

  const res = new URLSearchParams(window.location.search);
  const settings = QueryString.parse(base64.decode(res.get('config') || ''));
  if (res.has('origin')) {
    settings['origin'] = res.get('origin');
  }
  return transformStringToBoolean(settings);
})();


export const theme = (() => {
  if (window.STATIC_MODE && window.CHATBOT_THEME) {
    return window.CHATBOT_THEME;
  }

  const res = new URLSearchParams(window.location.search);
  return res.get('theme') || 'default';
})();
const creator = window.top;

export const isPreview = (() => {
  const res = new URLSearchParams(window.location.search);
  return res.has('preview');
})();
export const isOnlyChatbot = (() => {
  const res = new URLSearchParams(window.location.search);
  return res.has('only-chatbot');
})();

export const hideBotName = (() => {
  const res = new URLSearchParams(window.location.search);
  return res.has('hide-bot-name');
})();

export const autoOpen = (() => {
  const res = new URLSearchParams(window.location.search);
  return res.has('auto-open');
})();

export const locale = (() => {
  return new URLSearchParams(window.location.search).get('locale') || 'en';
})();
export const DEFAULT_LANG = locale;
export const isIntegrated = creator && window.top !== window && !isPreview && !isOnlyChatbot;

const invoker = isIntegrated
  ? (value) => creator.postMessage(String(value), qs['origin'])
  : () => void 0;

export default invoker;
