/**
 * update a item to array
 * @param {object|(arrayItem) => object} item update item data
 * @param {object[]} array array
 * @param {(item, index) => boolean} condition condition
 */
export function updateItemInArray(item, array, condition) {
  return array.map((a, i) => {
    if (condition(a, i)) {
      if (typeof item === 'function') return item(a);
      return { ...a, ...item };
    }
    return a;
  });
}
/**
 * push item in array
 * @param {object} item
 * @param {object[]} array
 * @param {number} index push index in array
 */
export function pushItemToArray(item, array, index = -1) {
  index = index < 0 ? array.length : index;
  if (index === 0) return [item, ...array];
  if (index === array.length) return [...array, item];
  return [...array.slice(0, index), item, ...array.slice(index, array.length)];
}
/**
 * remove item from Array
 * @param {object[]} array
 * @param {(item, index) => boolean} condition
 */
export function removeItemFromArray(array, condition) {
  const index = array.findIndex((item, i) => condition(item, i));
  if (index === 0) return [index, array.slice(1)];
  if (index > 0)
    return [index, [...array.slice(0, index), ...array.slice(index + 1, array.length)]];
  return array.slice();
}
