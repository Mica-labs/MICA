const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
  app.use(
    createProxyMiddleware('/v1', {
      target: 'http://127.0.0.1:5001', // 修改为正确的目标端口
      changeOrigin: true,
      pathRewrite: {
        '^': ''
      }
    })
  );
  app.use(
    createProxyMiddleware('/chat', {
      target: 'http://127.0.0.1:6666',
      changeOrigin: true,
      pathRewrite: {
        '^': ''
      }
    })
  );
};
