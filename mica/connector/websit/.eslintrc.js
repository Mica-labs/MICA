module.exports = {
  env: {
    es6: true,
    browser: true,
    amd: true,
    node: true
  },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module'
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'react-app',
    'react-app/jest',
    'plugin:jsx-a11y/recommended'
  ],
  plugins: ['simple-import-sort'],
  rules: {
    'react/prop-types': 'off',
    'react/react-in-jsx-scope': 'off',
    // 'simple-import-sort/imports': [
    //   'warn',
    //   {
    //     groups: [
    //       // Side effect imports.
    //       ['^\\u0000'],
    //       // React first
    //       // Packages.
    //       // Things that start with a letter (or digit or underscore), or `@` followed by a letter.
    //       ['^react$', '^prop-types$', '^\\w', '^@'],
    //       // Absolute imports and other imports such as Vue-style `@/foo`.
    //       // Anything not matched in another group.
    //       // Custom alias
    //       [
    //         '^(?:(assets)|(pages)|(components)|(utils)|(hooks)|(models)|(layouts)|(wrappers)|(themes)|(routes)|(services)|(test))'
    //       ],
    //       ['^'],
    //       // Relative imports.
    //       // Anything that starts with a dot.
    //       ['^\\.']
    //     ]
    //   }
    // ],
    // 'simple-import-sort/exports': 'error',
    'no-debugger': 'off',
    'jsx-a11y/anchor-is-valid': 'off'
  },
  settings: {
    react: {
      version: 'detect' // "detect" automatically picks the version you have installed.
    },
    'import/resolver': {
      node: {
        paths: ['src'],
        extensions: ['.js', '.jsx', '.ts', '.tsx']
      }
    }
  }
};
