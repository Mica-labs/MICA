import terser from '@rollup/plugin-terser';
import { babel } from '@rollup/plugin-babel';
import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import nodePlyfills from 'rollup-plugin-polyfill-node';

const config = {
  input: './src/index.js',
  output: {
    file: './build/sdk.js',
    format: 'umd',
    name: 'Chatbot'
  },
  plugins: [
    nodePlyfills(),
    nodeResolve(),
    commonjs(),
    babel({
      babelHelpers: 'bundled'
    }),
    terser()
  ]
};
export default config;
