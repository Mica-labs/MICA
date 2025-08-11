import fetch from 'cross-fetch';

const parseResponse = (data) => ({ data });

const parseBody = async (response) => {
  try {
    return await response.json();
  } catch (e) {
    if (process.env.NODE_ENV === 'development') {
      console.log(e);
    }
    return {};
  }
};

export function request(url, { headers, ...opt }) {
  return fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...headers
    },
    credentials: 'include',
    ...opt,
    body: opt?.body ? JSON.stringify(opt.body) : void 0
  })
    .then((response) => {
      if (response.status >= 200 && response.status < 300) {
        return response;
      }
      const error = new Error(response.statusText);
      error.response = response;
      throw error;
    })
    .then(parseBody)
    .then(parseResponse)
    .catch(async (error) => {
      const { response } = error;

      const data = await parseBody(response);
      const errorText = data?.error || data?.message || error.message || response.statusText;

      if (process.env.NODE_ENV === 'development') {
        console.error(`Request failed: ${url}`, errorText);
      }

      return {
        error: errorText,
        response: {
          data,
          ...response
        }
      };
    });
}

export default request;
