import request from './request';
import { decodeAttachmentText } from './attachment';
import { store } from './store';
export async function sendMessage(authentication, { message, sender }, settings) {
  const param = new Map();
  param.set('sender', sender);
  param.set('message', message);
  const requestBody = Object.fromEntries(param);
  const result = request("/v1/chat", {
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

export async function uploadFile(file, authentication, chatId) {
  const form = new FormData();
  form.append('file', file);
  form.append('chatId', chatId);
  const response = await fetch('/deprecated', {
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
