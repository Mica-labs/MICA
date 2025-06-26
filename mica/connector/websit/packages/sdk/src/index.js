import * as qs from 'qs';
import * as base64 from 'js-base64';

function injectInnerSystemVariables() {
  // _sys__host
  const sys_host = { key: '_sys__host', value: window.location.host };
  return [sys_host];
}

function processVars(varArrayObject) {
  return Object.values(varArrayObject)
    .map(({ id, key, type, body }) => {
      if (type === 'set') {
        return { key: id || key, value: body };
      }
      if (type === 'localStore') {
        return { key: id || key, value: window.localStorage.getItem(body) };
      }
      if (type === 'sessionStore') {
        return { key: id || key, value: window.sessionStorage.getItem(body) };
      }
      if (type === 'custom') {
        // eslint-disable-next-line no-new-func
        const func = new Function(body);
        try {
          return { key: id || key, value: func() };
        } catch (error) {
          console.error('function is error', func);
          return undefined;
        }
      }
      return undefined;
    })
    .filter(Boolean);
}
function Chatbot(settings, theme) {
  this.state = {
    status: 'close',
    defaultCloseMaxHeight: '60px',
    defaultCloseMinHeight: '60px',
    defaultCloseWidth: '60px',
    default: {
      defaultOpenMaxHeight: '600px',
      defaultOpenMinHeight: '400px',
      defaultOpenWidth: '460px'
    },
    full: {
      defaultOpenMaxHeight: '100%',
      defaultOpenMinHeight: '100%',
      defaultOpenWidth: '100%'
    }
  };
  console.log(JSON.stringify(settings));
  const server = settings.server.replace(/\/$/, '');
  const iframe = (this.iframe = document.createElement('iframe'));
  // 确保chatbot路径以/开头，避免重定向
  iframe.src = server + 
    `/chatbot/?${new URLSearchParams({
      config: settings.config,
      // extra
      origin: window.location.origin,
      theme,
    }).toString()}`;

  const container = document.createElement('div');
  container.className = 'chatbot';
  this.container = container;

  // 只有当settings中有tooltip内容时才创建tooltip元素
  const tooltipContent = settings.tooltip || settings.config?.tooltip;
  if (tooltipContent) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    const tooltipText = document.createElement('span');
    tooltipText.innerText = tooltipContent;

    tooltip.appendChild(tooltipText);
    this.tooltip = tooltip;
  } else {
    this.tooltip = null;
  }

  const close = document.createElement('div');
  close.className = 'close';
  this.close = close;

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  svg.setAttribute('width', '10');
  svg.setAttribute('height', '10');
  svg.setAttribute('viewBox', '0 0 1024 1024');
  svg.setAttribute('fill', '#333');
  // svg draw a close icon
  svg.setAttributeNS(
    'http://www.w3.org/2000/xmlns/',
    'xmlns:xlink',
    'http://www.w3.org/1999/xlink'
  );
  path.setAttribute(
    'd',
    'M557.312 513.248l265.28-263.904c12.544-12.48 12.608-32.704 0.128-45.248-12.512-12.576-32.704-12.608-45.248-0.128l-265.344 263.936-263.04-263.84C236.64 191.584 216.384 191.52 203.84 204 191.328 216.48 191.296 236.736 203.776 249.28l262.976 263.776L201.6 776.8c-12.544 12.48-12.608 32.704-0.128 45.248 6.24 6.272 14.464 9.44 22.688 9.44 8.16 0 16.32-3.104 22.56-9.312l265.216-263.808 265.44 266.24c6.24 6.272 14.432 9.408 22.656 9.408 8.192 0 16.352-3.136 22.592-9.344 12.512-12.48 12.544-32.704 0.064-45.248L557.312 513.248z'
  );
  svg.appendChild(path);
  close.appendChild(svg);

  const style = (this.style = document.createElement('style'));

  const css = `
		.chatbot.chatbot {
			z-index: 2147483647;
			position: fixed !important;
			bottom: 20px !important;
			right: 20px !important;
      height: calc(var(--app-height));
      max-height: ${this.state.defaultCloseMaxHeight};
      min-height: ${this.state.defaultCloseMinHeight};
      width: ${this.state.defaultCloseWidth};
		}
    
		.chatbot.chatbot iframe {
			display: initial!important;
			width: 100% !important;
			height: 100% !important;
			border: none !important;
			position: absolute !important;
			bottom: 0 !important;
			right: 0 !important;
			background: transparent !important;
			max-width: 100%;
      box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
		}

    .chatbot.chatbot .close {
      height: 10px;
      width: 10px;
      position: absolute;
      right: -5px;
      top: -5px;
      box-shadow: 0 0 4px rgba(0 0 0 / 0.8);
      background: white;
      border-radius: 50%;
      font-size: 0;
    }


    .chatbot.chatbot.minimize {
      width: 15px !important;
      right: 0px !important;
      padding: 2px;
      background: #0041ff;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
      text-transform: uppercase;
      font-size: 11px;
    }

    .chatbot.chatbot.minimize::after {
      display: inline-block;
      content: "chat bot";
      writing-mode: tb;
      transform: rotate(180deg);
      color: white;
    }

    .chatbot.chatbot.minimize iframe {
      display: none !important;
    }

    .chatbot.chatbot.minimize .close, .chatbot.chatbot.open .close {
      display: none;
    }

    .chatbot .tooltip {
      position: absolute;
      white-space: nowrap;
      left: -10px;
      transform: translate(-100%, 0%);
      top: 0;
      background: white;
      border: 1px solid #ccc;
      display: flex;
      padding: 4px 8px;
      border-radius: 5px;
    }

    .chatbot .tooltip:before {
      content: "";
      position: absolute;
      border: 5px solid transparent;
      border-width: 5px 0 5px 8px;
      border-left-color: white;
      right: -6px;
      top: 20%;
      z-index: 1;
    }

    .chatbot .tooltip:after {
      content: "";
      position: absolute;
      border: 5px solid transparent;
      border-width: 5px 0 5px 8px;
      border-left-color: #ccc;
      right: -8px;
      top: 20%;
    }

    .chatbot .tooltip.closed {
      display: none;
    }
		`;

  try {
    style.appendChild(document.createTextNode(css));
  } catch (ex) {
    style.styleSheet.cssText = css; //针对IE
  }

  const head = document.getElementsByTagName('head')[0];

  head.appendChild(style);

  document.body.appendChild(container);
  container.appendChild(iframe);

  container.appendChild(close);
  // 只有当tooltip存在时才添加到容器中
  if (this.tooltip) {
    container.appendChild(this.tooltip);
  }
  this.correctAppHeight();

  window.addEventListener('resize', this.correctAppHeight, false);
  window.addEventListener('resize', this.resize.bind(this), false);
  window.addEventListener('message', this.receiveMessage.bind(this), false);

  let toggle = this.onMinNormalToggle.bind(this);
  // 默认最小化
  if (settings.minimize) {
    toggle(null, true);
  }
  close.addEventListener('click', toggle, false);
  // 只有当tooltip存在时才添加事件监听器
  if (this.tooltip) {
    this.tooltip.addEventListener(
      'click',
      (e) => {
        e.stopPropagation();
        if (!this.tooltip.classList.contains('closed')) {
          this.tooltip.classList.add('closed');
        }
      },
      false
    );
  }
  container.addEventListener('click', toggle, false);
}

Chatbot.initialize = function (settings, theme = 'default') {
  // preprocess get value of slot and variables
  const initial = () => new Chatbot(settings, theme);
  if (
    document.readyState === 'complete' ||
    document.readyState === 'loaded' ||
    document.readyState === 'interactive'
  ) {
    initial();
  } else {
    document.addEventListener('DOMContentLoaded', initial);
  }
};

Chatbot.prototype.onMinNormalToggle = function (e, ignoreTooltip = false) {
  // 手动触发时没有event对象
  if (e) {
    e.stopPropagation();
  }
  // 只有当tooltip存在且不忽略tooltip时才处理
  if (!ignoreTooltip && this.tooltip && !this.tooltip.classList.contains('closed')) {
    this.tooltip.classList.add('closed');
  }
  this.container.classList.toggle('minimize');
  this.resize();
};

Chatbot.prototype.resize = function () {
  const type = document.documentElement.offsetWidth <= 640 ? 'full' : 'default';
  switch (this.state.status) {
    case 'open':
      this.container.style = `
      max-height: ${this.state[type].defaultOpenMaxHeight};
      min-height: ${this.state[type].defaultOpenMinHeight};
      width: ${this.state[type].defaultOpenWidth}
    `;
      if (!this.container.classList.contains('open')) {
        this.container.classList.add('open');
      }
      // 只有当tooltip存在时才操作其classList
      if (this.tooltip && !this.tooltip.classList.contains('closed')) {
        this.tooltip.classList.add('closed');
      }
      break;
    case 'open-full':
      this.container.style = `
      max-height: ${this.state.full.defaultOpenMaxHeight};
      min-height: ${this.state.full.defaultOpenMinHeight};
      width: ${this.state.full.defaultOpenWidth};
      bottom: 0px !important;
      right: 0px !important;
    `;
      if (!this.container.classList.contains('open')) {
        this.container.classList.add('open');
      }
      break;
    case 'close-full':
      this.container.style = `
      max-height: ${this.state[type].defaultOpenMaxHeight};
      min-height: ${this.state[type].defaultOpenMinHeight};
      width: ${this.state[type].defaultOpenWidth};
      bottom: 20px !important;
      right: 20px !important;
    `;
      if (this.container.classList.contains('open')) {
        this.container.classList.remove('open');
      }
      break;
    case 'close':
      this.container.style = `
      max-height: ${this.state.defaultCloseMaxHeight};
      min-height: ${this.state.defaultCloseMinHeight};
      width: ${this.state.defaultCloseWidth}
    `;
      if (this.container.classList.contains('open')) {
        this.container.classList.remove('open');
      }
      break;

    default:
      this.container.style = `display:none !important;`;
  }
};

Chatbot.prototype.receiveMessage = function (mes) {
  if (mes.data && mes.data.indexOf) {
    if (mes.data.indexOf('true') > -1) {
      this.state.status = 'open';
    }
    if (mes.data.indexOf('false') > -1) {
      this.state.status = 'close';
    }
    if (mes.data.indexOf('open-full') > -1) {
      this.state.status = 'open-full';
    }
    if (mes.data.indexOf('close-full') > -1) {
      this.state.status = 'close-full';
    }
    if (mes.data.indexOf('fail') > -1) {
      this.state.status = 'fail';
    }
  }

  this.resize();
};

Chatbot.prototype.correctAppHeight = function () {
  const doc = document.documentElement;
  doc.style.setProperty('--app-height', `${window.innerHeight}px`);
};

Chatbot.prototype.destroy = function () {
  window.removeEventListener('message', this.receiveMessage);
  document.body.removeChild(this.container);
  document.getElementsByTagName('head')[0].removeChild(this.style);
  this.iframe = null;
  this.container = null;
  const script = Array.form(document.querySelectorAll('script')).find((s) =>
    /\/chatbot/.test(s.src)
  );
  if (script) {
    document.removeChild(script);
  }
};

export default Chatbot;
