import request from './request';
import { decodeAttachmentText } from './attachment';
import { store } from './store';

// 定义URI常量
const _URI_CHAT = '/v1/chat';

export async function sendMessage(authentication, { message, sender }, settings) {
  // 按照你要求的格式创建参数
  const param = new Map();
  param.set('sender', sender);
  param.set('message', message);
  console.log('param', param);
  console.log('settings', settings);

  // 将Map转换为普通对象用于请求
  const requestBody = Object.fromEntries(param);

  const result = request(_URI_CHAT, {
    body: requestBody,
    headers: {
      ...authentication
    },
    method: 'POST'
  });
  if (result.error) {
    return Promise.reject(result.error);
  }

  return result;
}

function transformPrimaryButtonsMap(buttons) {
  if (!buttons) return {};
  return buttons.reduce((p, c) => ({ ...p, [c.id]: c.hidden }), {});
}

export async function evaluateService(data, authentication) {
  const result = request('/chat/api/message/evaluate', {
    body: data,
    headers: authentication,
    method: 'PUT'
  });
  if (result.error) {
    return Promise.reject(result.error);
  }
  return result;
}

export async function uploadFile(file, authentication, chatId) {
  const form = new FormData();
  form.append('file', file);
  form.append('chatId', chatId);
  const response = await fetch('/chat/api/message/file', {
    headers: {
      ...authentication
    },
    method: 'POST',
    body: form
  });
  if (response.status >= 200 && response.status < 300) {
    const {
      dialog: {
        input: { send }
      }
    } = await response.json();
    const data = decodeAttachmentText(send);
    return data;
  }
  const error = new Error(response.statusText);
  error.response = response;
  throw error;
}
