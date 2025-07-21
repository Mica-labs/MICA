export function decodeAttachmentText(value) {
  try {
    return JSON.parse(decodeURIComponent(value));
  } catch (e) {
    //
  }
  return { name: '-', href: '#', type: 'null', version: '0.0.1' };
}
export function isAttachment(value) {
  if (!value) return false;
  if (value.startsWith('%7B%22') && value.endsWith('%22%7D')) return true;
  return false;
}
