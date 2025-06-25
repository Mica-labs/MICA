import { createWithEqualityFn } from 'zustand/traditional';
import { shallow } from 'zustand/shallow';
import { evaluateService, sendMessage as fetchMessage } from '@/services';
import i18next from '@/i18n';
import invoker, {
  isIntegrated,
  qs,
  isPreview,
  DEFAULT_LANG,
  isOnlyChatbot,
  autoOpen
} from '@/invoker';
import shortUUID from 'short-uuid';
import { pushItemToArray, removeItemFromArray, updateItemInArray } from '@/util';

/**
 * @typedef {Object} OriginMessage
 *
 * @typedef {Object} Message
 *
 * @typedef {Object} Conversation
 *
 * @typedef {string} ConversationId
 *
 * @typedef {Object} MultipleInputCache
 * @property {boolean} actived
 * @property {string[]} values
 *
 * @typedef {Object} ISendMessageParams
 * @property {string} text display label
 * @property {string} content send to origin of payload
 * @property {'text'|'button'|'file'|'link'} type
 * @property {'client'|'agent'} from
 */

class BackendError extends Error {
  constructor(msg, sendParams) {
    super(msg);
    this.sendParams = sendParams;
  }
}

class NetworkError extends Error {
  constructor(msg, sendParams) {
    super(msg);
    this.sendParams = sendParams;
  }
}

/**
 * get Authentication from settings
 * @param {object} settings setting of chatbot
 * @returns Authentication
 */
export const getAuthentication = (settings) => ({
  bot_name: settings.bot_name
});

/**
 * generate uuid
 * @returns string
 */
const generateID = () => shortUUID.generate();

/**
 * normalize the messages from response
 * @param {OriginMessage[]} messages messages from response
 * @param {string} msgId current messages`id from the response
 * @returns {Message[]}
 */
const normalizeMessages = (messages, msgId, canEvaluate = false) => {
  if (!messages || !Array.isArray(messages) || messages.length < 1) return [];
  const mergeCustomProperties = (item, i) => {
    if (messages[i + 1] && messages[i + 1]?.custom) {
      return { ...item, ...messages[i + 1] };
    }
    return item;
  };
  const normalizeMsgItem = (item, i) => {
    const contents = [];
    if (item.custom) return contents;
    const { text, buttons, image, similarQuestions, links, timeout, loading, file, ...extra } =
      mergeCustomProperties(item, i);
    if (typeof text === 'string' && text.trim() !== '') {
      contents.push({ type: 'text', content: text });
    }
    if (Array.isArray(buttons) && buttons.length > 0) {
      contents.push({
        type: 'button',
        content: buttons.map((b) => ({ ...b, primary: b.primary ?? true }))
      });
    }
    if (typeof image === 'string' && image.trim() !== '') {
      contents.push({
        type: 'img',
        content: image
          .split(',')
          .filter(Boolean)
          .map((src) => ({ id: generateID(), src }))
      });
    }
    if (Array.isArray(similarQuestions) && similarQuestions.length > 0) {
      contents.push({ type: 'similarQuestions', content: similarQuestions });
    }
    if (Array.isArray(links) && links.length > 0) {
      contents.push({ type: 'links', content: links });
    }
    if (timeout) {
      contents.push({ type: 'timeout', content: timeout });
    }
    if (file) {
      contents.push({ type: 'file', content: file });
    }
    if (loading) {
      contents.push({ type: 'loading', content: loading });
    }
    return contents.map((m) => ({ ...m, ...extra, helpful: undefined }));
  };
  const date = Date.now();
  const msgs = messages
    .map((msg, i) =>
      normalizeMsgItem(msg, i)
        .filter(Boolean)
        .map((item) => ({
          id: generateID(),
          from: 'agent',
          date,
          msgId,
          delay: item.custom?.delay || '0',
          ...item
        }))
    )
    .flat(1);
  if (msgs.length > 0) {
    msgs[msgs.length - 1].evaluate = canEvaluate;
  }
  return msgs;
};
/**
 * @param {ISendMessageParams} params
 * @param {boolean} loading
 * @returns
 */
const buildMessage = ({ text, content, type, from }, loading = false) => {
  const buildOriginMessage = () => {
    if (type === 'text') return { text };
    if (type === 'button') return { buttons: [{ title: text, payload: content }] };
    if (type === 'file') return { file: content };
    if (type === 'loading') return { loading: text };
    return { text };
  };
  return normalizeMessages([buildOriginMessage()], generateID()).map((m) => ({
    ...m,
    from,
    loading
  }))[0];
};

const localStorageKey = 'chatbot_conversations_v1@';
const defaultState = {
  //非集成 或者 自动打开
  visible: (isIntegrated ? false : true) || autoOpen,
  full: false,
  route: 'conversation',
  settings: {
    name: 'Mica',
    ...qs
  },
  sending: false,
  creating: false,
  createError: '',
  locale: DEFAULT_LANG,
  current: '',
  conversations: []
};
/**
 * init store state from localStore or default
 * @returns state
 */
const initial = () => {
  if (isPreview) {
    const current = generateID();
    return {
      ...defaultState,
      current,
      conversations: [
        {
          id: current,
          messages: [
            {
              id: generateID(),
              evaluate: true,
              date: Date.now(),
              content: defaultState.settings?.welcome || 'Welcome!!!',
              type: 'text',
              from: 'agent'
            },
            {
              id: generateID(),
              evaluate: true,
              date: Date.now(),
              content: [{ payload: '-', primary: true, title: 'Hello' }],
              type: 'button',
              from: 'agent'
            },
            {
              id: generateID(),
              evaluate: true,
              date: Date.now(),
              content: 'Hello',
              type: 'text',
              from: 'client'
            }
          ]
        }
      ]
    };
  }
  if (isOnlyChatbot || autoOpen) {
    return {
      ...defaultState
    };
  }

  try {
    const initialState = JSON.parse(localStorage.getItem(`${localStorageKey}${qs['token']}`));
    initialState.settings = {
      ...initialState.settings
    };

    initialState.visible = isIntegrated ? initialState.visible : true;
    initialState.full = false;
    setTimeout(() => {
      if (initialState.locale === 'en') {
        i18next.changeLanguage(initialState.locale);
      } else {
        i18next.changeLanguage('zh');
      }
    }, 0);
    return initialState;
  } catch {
    return defaultState;
  }
};

const delay = (ms = 2000) => new Promise((resolver) => setTimeout(resolver, ms));

const useChat = createWithEqualityFn(
  (set, get) => ({
    isPreview,
    /**
     * @type {boolean}
     * @description trigger visible
     */
    visible: false,
    /**
     * @type {boolean}
     * @description tigger full-screen
     */
    full: false,
    /**
     * @type {string}
     * @description current conversation id
     */
    current: '',
    /**
     * @type {string}
     * @description current route page
     */
    route: 'conversation',
    /**
     * @type {'zh' | 'en'}
     * @description locale field key
     */
    locale: DEFAULT_LANG,
    /**
     * @type {object}
     * @description the settings of chat
     */
    settings: {},
    /**
     * @type {Conversation[]}
     * @description All of conversation
     */
    conversations: [],
    /**
     * @type {boolean}
     * @description loading of create
     */
    creating: false,
    /**
     * @type {string}
     * @description error of create
     */
    createError: '',
    /**
     * @type {boolean}
     * @description message block have a message loading
     */
    sending: false,

    /**
     * @type {Record<ConversationId, MultipleInputCache>}
     * @description multiple input value for conversation
     */
    multipleInputCache: {},

    /// action of store
    /**
     * initial store function
     */
    initial: () => {
      const initialState = initial();
      set({ ...initialState });
    },
    /**
     * redirect to history page
     * @returns void
     */
    redirectHistory: () => {
      if (isPreview) return;
      set({ route: 'history' });
    },
    /**
     * redirect to conversation page
     * @param {string} conversationId id
     * @returns void
     */
    redirectConversation: (conversationId) => {
      if (isPreview) return;
      set({ route: 'conversation', current: conversationId });
    },
    /**
     * toggle the full boolean
     */
    toggleFull: () => {
      const { full } = get();
      invoker(full ? 'close-full' : 'open-full');
      set({ full: !full });
    },
    /**
     * toggle the visible boolean
     */
    toggleVisible: () => {
      const { visible } = get();
      invoker(!visible);
      if (visible) {
        set({ visible: false, full: false });
      } else {
        set({ visible: true });
      }
    },
    /**
     * change locale language
     * @param {'zh' | 'en'} locale local field key
     */
    changeLanguage: (locale) => {
      i18next.changeLanguage(locale || DEFAULT_LANG);
      set({ locale });
    },
    /**
     * push a new conversation in conversations
     * @param {Conversation} conversation
     */
    addConversation: (conversation) => {
      const newConversations = get().conversations.slice();
      newConversations.push(conversation);
      set({ current: conversation.id, conversations: newConversations });
    },
    /**
     * create a new conversation
     */
    createConversation: async () => {
      if (isPreview) return;
      set({ creating: true });
      try {
        const { addConversation, submitMessage } = get();
        // 生成唯一的对话 ID
        const sessionId = `conversation_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        // 创建空的对话
        addConversation({
          id: sessionId,
          messages: []
        });
        // 切换到对话页面
        set({ route: 'conversation' });
        // 发送 /init 消息
        await submitMessage(
          {
            text: '/init',
            content: '/init',
            type: 'text'
          },
          false
        ); // 设置为 false，不显示给用户
      } catch (error) {
        let createError = error.message || error.data?.message || i18next.t`errors.oops`;
        if (typeof error === 'string') createError = error;
        set({ createError });
      }
      set({ creating: false });
    },
    /**
     * evaluate the bot message
     * @param {'bad' | 'helped'} helpful value of evaluate
     * @param {string} id generate id
     * @param {string} msgId id of response
     */
    evaluateMessage: async (helpful, id, msgId) => {
      if (isPreview) return;
      const { current, settings, conversations } = get();
      try {
        await evaluateService(
          { helpful: helpful === 'bad' ? '2' : '1', chatId: current, messageId: msgId },
          getAuthentication(settings)
        );
        const newConversations = updateItemInArray(
          (item) => ({
            ...item,
            messages: updateItemInArray({ helpful }, item.messages, (m) => m.id === id)
          }),
          conversations,
          (c) => c.id === current
        );
        set({ conversations: newConversations });
      } catch (error) {
        //
      }
    },
    /**
     * append a message to current conversation messages
     * @param {Message} message
     * @param {number} index insert index
     */
    appendMessage: (message, index) => {
      const { current, conversations } = get();
      const newConversations = updateItemInArray(
        (item) => ({ ...item, messages: pushItemToArray(message, item.messages, index) }),
        conversations,
        (c) => c.id === current
      );
      set({ conversations: newConversations });
    },
    removeMessage: (message) => {
      const { current, conversations } = get();
      let removeIndex = -1;
      const newConversations = updateItemInArray(
        (item) => {
          const [rIndex, messages] = removeItemFromArray(
            item.messages,
            (it) => it.id === message.id
          );
          removeIndex = rIndex;
          return { ...item, messages };
        },
        conversations,
        (c) => c.id === current
      );
      set({ conversations: newConversations });
      return removeIndex;
    },
    updateMessage: (message) => {
      const { current, conversations } = get();
      const newConversations = updateItemInArray(
        (item) => ({
          ...item,
          messages: updateItemInArray(message, item.messages, (m) => m.id === message.id)
        }),
        conversations,
        (c) => c.id === current
      );
      set({ conversations: newConversations });
    },
    delayOutputMessage: async (messages) => {
      if (!Array.isArray(messages)) return;
      const { appendMessage, removeMessage } = get();
      await messages
        .map((msg) => async () => {
          const loading = buildMessage(
            { text: i18next.t`bot.loading`, type: 'loading', from: 'agent' },
            true
          );
          appendMessage(loading);
          await delay(Number(msg.delay));
          // replace bot loading item
          removeMessage(loading);
          appendMessage(msg);
        })
        .reduce((p, c) => p.then(() => c()), Promise.resolve())
        .then();
    },
    /**
     * send messgae to origin
     * @param {ISendMessageParams} params params
     * @param {boolean} enableAppendUserMessage need append user message
     */
    sendMessage: async (params, enableAppendUserMessage = true) => {
      if (isPreview) return;
      const { current, multipleInputCache, sendMessageToMultipleInputCache, submitMessage } = get();
      if (multipleInputCache[current] && multipleInputCache[current].actived) {
        // todo: check cache input from 'button' | 'similar'...
        if (params.type !== 'text') return;
        // set cache input
        sendMessageToMultipleInputCache(params);
        return;
      }
      submitMessage(params, enableAppendUserMessage);
    },
    /**
     * send messgae to origin
     * @param {ISendMessageParams} params params
     * @param {boolean} enableAppendUserMessage need append user message
     */
    submitMessage: async (params, enableAppendUserMessage = true) => {
      if (isPreview) return;
      const {
        appendMessage,
        delayOutputMessage,
        removeMessage,
        current,
        settings,
        toggleMultipleInput
      } = get();
      set({ sending: true });
      try {
        if (enableAppendUserMessage) {
          const userMessage = buildMessage({ ...params, from: 'client' });
          appendMessage(userMessage);
        }

        const botMessageLoading = buildMessage(
          { text: i18next.t`bot.loading`, type: 'loading', from: 'agent' },
          true
        );
        appendMessage(botMessageLoading);

        const { data } = await fetchMessage(
          getAuthentication(settings),
          {
            message: params.content || params.text,
            sender: current
          },
          settings
        );

        // request api failed
        if (!data) {
          // remove the loading animation
          removeMessage(botMessageLoading);
          throw new NetworkError(i18next.t`errors.network`, params);
        }

        removeMessage(botMessageLoading);

        // 简化的消息处理：只处理对话内容
        // data格式：[{ "text": "Hello! I'd like to ask..." }, { "text": "Great! Let's get started..." }]
        const receives = normalizeMessages(data, generateID(), false);

        await delayOutputMessage(receives);

        if (receives.some((r) => r.custom?.multiInput)) {
          toggleMultipleInput();
        }
      } catch (error) {
        let errorMessage;
        if (error instanceof BackendError || error instanceof NetworkError) {
          errorMessage = normalizeMessages([
            { timeout: { label: error.message, sendParams: error.sendParams } }
          ]);
        } else {
          errorMessage = normalizeMessages([
            { timeout: { label: i18next.t`errors.unknown`, sendParams: error.sendParams } }
          ]);
        }
        errorMessage.forEach((msg) => appendMessage(msg));
        console.error('send message happened: ', error);
      } finally {
        set({ sending: false });
      }
    },
    /**
     * send uplaod file message loading item
     * @param {File} file
     */
    sendUploadMessage: async (file) => {
      if (isPreview) return;
      const { appendMessage } = get();
      const uploading = buildMessage(
        { text: file.name, content: file, type: 'file', from: 'client' },
        true
      );
      appendMessage(uploading);
    },
    resetFileMessage: (id, status, result) => {
      const { updateMessage } = get();
      updateMessage({ id, type: 'fileDone', loading: false, content: { status, result } });
    },
    clearHistory: () => {
      window.localStorage.removeItem(`${localStorageKey}${qs['token']}`);
      set({ conversations: [], current: '' });
    },

    /// multiple inputs cache

    toggleMultipleInput: () => {
      if (isPreview) return;
      const { current, multipleInputCache } = get();
      const currentCache = multipleInputCache[current] || {};
      currentCache.actived = !currentCache.actived;
      currentCache.values = currentCache.values || [];
      set({ multipleInputCache: { ...multipleInputCache, [current]: currentCache } });
    },
    /**
     * send messgae to origin
     * @param {ISendMessageParams} params params
     */
    sendMessageToMultipleInputCache: (params) => {
      if (isPreview) return;
      const { current, multipleInputCache, appendMessage } = get();
      const currentCache = multipleInputCache[current] || { actived: true, values: [] };
      currentCache.actived = true;
      currentCache.values.push(params.text || params.content);
      set({ multipleInputCache: { ...multipleInputCache, [current]: currentCache } });

      const userMessage = buildMessage({ ...params, from: 'client' });
      appendMessage(userMessage);
    },
    submitMultipleInputCache: async () => {
      if (isPreview) return;
      const { submitMessage, current, multipleInputCache } = get();
      const currentCache = multipleInputCache[current];
      if (!currentCache || !currentCache.actived) return;

      const text = currentCache.values.join('\n');
      await submitMessage({ text, content: text, type: 'text' }, false);
      const newCache = { ...multipleInputCache };
      delete newCache[current];
      set({ multipleInputCache: newCache });
    }
  }),
  shallow
);
useChat.subscribe((state) => {
  if (isPreview) return;
  window.localStorage.setItem(
    `${localStorageKey}${qs['token']}`,
    JSON.stringify({
      ...state,
      current: state.route === 'history' ? '' : state.current,
      createError: '',
      visible: false,
      sending: false
    })
  );
});

export default useChat;
export { useChat as store };
