import 'babel-polyfill';
import './assets/simplebar.min.css';

import React from 'react';
import ReactDOM from 'react-dom/client';
import './i18n';

import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
