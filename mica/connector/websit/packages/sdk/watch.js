const fs = require('node:fs');

fs.watchFile('./build/sdk.js', () => {
  console.log('change');
  fs.cpSync('./build/sdk.js', '../app/views/sdk.js');
});
