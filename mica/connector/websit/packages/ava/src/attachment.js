export function decodeAttachmentText(value) {
  try {
    return JSON.parse(decodeURIComponent(value));
  } catch (e) {
    //
  }
  return { name: '-', href: '#', type: 'null', version: '0.0.1' };
}
// %7B%22name%22%3A%22trash.png.svg%22%2C%22type%22%3A%22svg%22%2C%22href%22%3A%22%2Fapi%2Fblobs%2Fget%2Fa1_c4fjhb1rer5s%22%2C%22version%22%3A%220.0.1%22%7D
export function isAttachment(value) {
  if (!value) return false;
  if (value.startsWith('%7B%22') && value.endsWith('%22%7D')) return true;
  return false;
}
