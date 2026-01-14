// ============================================
// GOAT PREDICTION ULTIMATE - ESLINT CONFIGURATION
// ============================================
// Configuration complète de linting pour TypeScript/React/Next.js
// ============================================

/** @type {import('eslint').Linter.Config} */
const config = {
  // ============================================
  // ROOT CONFIGURATION
  // ============================================
  
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
    jest: true,
  },
  reportUnusedDisableDirectives: true,
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
    project: [
      './frontend/web-app/tsconfig.json',
      './backend/**/tsconfig.json',
      './**/tsconfig.json',
    ],
    tsconfigRootDir: __dirname,
  },
  ignorePatterns: [
    // Patterns globaux à ignorer
    '!.prettierrc.js',
    '!.eslintrc.js',
    '!.storybook/**',
    '**/dist/**',
    '**/build/**',
    '**/.next/**',
    '**/node_modules/**',
    '**/coverage/**',
    '**/public/**',
    '**/*.d.ts',
    '**/.cache/**',
    '**/tmp/**',
    '**/logs/**',
    '**/*.min.js',
    '**/generated/**',
    '**/__generated__/**',
  ],

  // ============================================
  // EXTENDS & PLUGINS
  // ============================================
  
  extends: [
    // Base configurations
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    
    // Next.js specific
    'next/core-web-vitals',
    'plugin:@next/next/recommended',
    
    // Accessibility
    'plugin:jsx-a11y/recommended',
    
    // Testing
    'plugin:jest/recommended',
    'plugin:testing-library/react',
    
    // Security
    'plugin:security/recommended',
    
    // Import sorting
    'plugin:import/recommended',
    'plugin:import/typescript',
    
    // Performance
    'plugin:unicorn/recommended',
    
    // Code quality
    'plugin:sonarjs/recommended',
    
    // Prettier integration (DOIT être en dernier)
    'prettier',
  ],
  
  plugins: [
    '@typescript-eslint',
    'react',
    'react-hooks',
    'jsx-a11y',
    'jest',
    'testing-library',
    'security',
    'import',
    'unicorn',
    'sonarjs',
    'tailwindcss',
    'simple-import-sort',
    'promise',
    'prettier',
  ],

  // ============================================
  // RULES CONFIGURATION
  // ============================================
  
  rules: {
    // ============================================
    // PRETTIER INTEGRATION
    // ============================================
    
    'prettier/prettier': [
      'error',
      {
        printWidth: 100,
        tabWidth: 2,
        useTabs: false,
        semi: true,
        singleQuote: true,
        trailingComma: 'es5',
        bracketSpacing: true,
        bracketSameLine: false,
        arrowParens: 'always',
        endOfLine: 'lf',
      },
    ],

    // ============================================
    // TYPESCRIPT RULES
    // ============================================
    
    '@typescript-eslint/ban-ts-comment': [
      'error',
      {
        'ts-expect-error': 'allow-with-description',
        'ts-ignore': true,
        'ts-nocheck': true,
        'ts-check': false,
        minimumDescriptionLength: 3,
      },
    ],
    
    '@typescript-eslint/consistent-type-imports': [
      'error',
      {
        prefer: 'type-imports',
        fixStyle: 'separate-type-imports',
      },
    ],
    
    '@typescript-eslint/explicit-function-return-type': [
      'error',
      {
        allowExpressions: true,
        allowTypedFunctionExpressions: true,
        allowHigherOrderFunctions: true,
        allowDirectConstAssertionInArrowFunctions: true,
      },
    ],
    
    '@typescript-eslint/explicit-module-boundary-types': 'error',
    
    '@typescript-eslint/no-explicit-any': 'error',
    
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        ignoreRestSiblings: true,
      },
    ],
    
    '@typescript-eslint/no-unsafe-assignment': 'error',
    '@typescript-eslint/no-unsafe-call': 'error',
    '@typescript-eslint/no-unsafe-member-access': 'error',
    '@typescript-eslint/no-unsafe-return': 'error',
    
    '@typescript-eslint/no-shadow': [
      'error',
      {
        ignoreTypeValueShadow: true,
        ignoreFunctionTypeParameterNameValueShadow: true,
      },
    ],
    
    '@typescript-eslint/require-await': 'error',
    '@typescript-eslint/await-thenable': 'error',
    
    '@typescript-eslint/no-floating-promises': [
      'error',
      {
        ignoreVoid: true,
        ignoreIIFE: false,
      },
    ],
    
    '@typescript-eslint/no-misused-promises': [
      'error',
      {
        checksVoidReturn: {
          attributes: false,
        },
      },
    ],
    
    '@typescript-eslint/prefer-optional-chain': 'error',
    '@typescript-eslint/prefer-nullish-coalescing': 'error',
    
    '@typescript-eslint/naming-convention': [
      'error',
      {
        selector: 'default',
        format: ['camelCase'],
        leadingUnderscore: 'allow',
        trailingUnderscore: 'forbid',
      },
      {
        selector: 'variable',
        format: ['camelCase', 'UPPER_CASE', 'PascalCase'],
        leadingUnderscore: 'allow',
      },
      {
        selector: 'typeLike',
        format: ['PascalCase'],
      },
      {
        selector: 'enumMember',
        format: ['UPPER_CASE'],
      },
      {
        selector: 'objectLiteralProperty',
        format: null, // Allow any format for object properties
      },
      {
        selector: 'parameter',
        format: ['camelCase'],
        leadingUnderscore: 'allow',
      },
    ],

    // ============================================
    // REACT RULES
    // ============================================
    
    'react/react-in-jsx-scope': 'off', // Not needed in Next.js
    'react/prop-types': 'off', // Using TypeScript instead
    
    'react/display-name': 'error',
    'react/no-array-index-key': 'warn',
    'react/no-danger': 'error',
    'react/no-unused-prop-types': 'error',
    'react/no-unused-state': 'error',
    
    'react/jsx-boolean-value': ['error', 'never'],
    'react/jsx-curly-brace-presence': [
      'error',
      {
        props: 'never',
        children: 'never',
      },
    ],
    'react/jsx-fragments': ['error', 'syntax'],
    'react/jsx-no-useless-fragment': 'error',
    'react/jsx-pascal-case': 'error',
    'react/jsx-props-no-spreading': 'off', // Allow spreading for HOCs
    
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',

    // ============================================
    // IMPORT/EXPORT RULES
    // ============================================
    
    'import/no-unresolved': 'error',
    'import/named': 'error',
    'import/default': 'error',
    'import/namespace': 'error',
    'import/no-absolute-path': 'error',
    'import/no-dynamic-require': 'error',
    'import/no-webpack-loader-syntax': 'error',
    'import/no-self-import': 'error',
    'import/no-cycle': 'error',
    'import/no-useless-path-segments': 'error',
    'import/no-relative-parent-imports': 'error',
    'import/no-unused-modules': 'error',
    'import/no-anonymous-default-export': 'error',
    'import/exports-last': 'error',
    
    'simple-import-sort/imports': [
      'error',
      {
        groups: [
          // React and related packages
          ['^react', '^next', '^@?\\w'],
          // Absolute imports
          ['^@/'],
          // Parent imports
          ['^\\.\\.(?!/?$)', '^\\.\\./?$'],
          // Same folder imports
          ['^\\./(?=.*/)(?!/?$)', '^\\.(?!/?$)', '^\\./?$'],
          // Style imports
          ['^.+\\.s?css$'],
          // Type imports
          ['^@?\\w.*\\u0000$', '^[^.].*\\u0000$', '^\\..*\\u0000$'],
        ],
      },
    ],
    
    'simple-import-sort/exports': 'error',

    // ============================================
    // SECURITY RULES
    // ============================================
    
    'security/detect-object-injection': 'off', // Too many false positives
    'security/detect-non-literal-regexp': 'error',
    'security/detect-non-literal-fs-filename': 'error',
    'security/detect-eval-with-expression': 'error',
    'security/detect-pseudoRandomBytes': 'error',
    'security/detect-possible-timing-attacks': 'error',
    'security/detect-no-csrf-before-method-override': 'error',
    'security/detect-buffer-noassert': 'error',
    'security/detect-child-process': 'error',
    'security/detect-disable-mustache-escape': 'error',
    'security/detect-new-buffer': 'error',

    // ============================================
    // UNICORN RULES
    // ============================================
    
    'unicorn/prevent-abbreviations': [
      'error',
      {
        replacements: {
          props: false,
          ref: false,
          params: false,
          args: false,
          err: false,
          req: false,
          res: false,
          env: false,
        },
        ignore: ['e2e', 'i18n', 'auth', 'api', 'db', 'ml'],
      },
    ],
    
    'unicorn/filename-case': [
      'error',
      {
        cases: {
          kebabCase: true,
          pascalCase: true,
        },
        ignore: [
          'README.md',
          'next-env.d.ts',
          '^\\[.*\\]\\..*$', // Next.js dynamic routes
        ],
      },
    ],
    
    'unicorn/no-null': 'off', // Null is used in TypeScript
    'unicorn/no-array-reduce': 'off', // Reduce is sometimes necessary
    'unicorn/prefer-module': 'off', // ESM not fully supported
    'unicorn/prefer-node-protocol': 'off', // Node protocol not always available

    // ============================================
    // SONARJS RULES
    // ============================================
    
    'sonarjs/cognitive-complexity': ['error', 15],
    'sonarjs/no-duplicate-string': ['error', { threshold: 3 }],
    'sonarjs/no-identical-functions': 'error',
    'sonarjs/no-all-duplicated-branches': 'error',
    'sonarjs/no-collapsible-if': 'error',
    'sonarjs/no-collection-size-mischeck': 'error',
    'sonarjs/no-empty-collection': 'error',
    'sonarjs/no-identical-expressions': 'error',
    'sonarjs/no-inverted-boolean-check': 'error',
    'sonarjs/no-redundant-boolean': 'error',
    'sonarjs/no-unused-collection': 'error',
    'sonarjs/no-useless-catch': 'error',
    'sonarjs/prefer-immediate-return': 'error',
    'sonarjs/prefer-object-literal': 'error',
    'sonarjs/prefer-single-boolean-return': 'error',

    // ============================================
    // JSX-A11Y RULES
    // ============================================
    
    'jsx-a11y/anchor-is-valid': [
      'error',
      {
        components: ['Link'],
        specialLink: ['hrefLeft', 'hrefRight'],
        aspects: ['invalidHref', 'preferButton'],
      },
    ],
    
    'jsx-a11y/alt-text': 'error',
    'jsx-a11y/aria-props': 'error',
    'jsx-a11y/aria-proptypes': 'error',
    'jsx-a11y/aria-unsupported-elements': 'error',
    'jsx-a11y/heading-has-content': 'error',
    'jsx-a11y/html-has-lang': 'error',
    'jsx-a11y/iframe-has-title': 'error',
    'jsx-a11y/img-redundant-alt': 'error',
    'jsx-a11y/interactive-supports-focus': 'error',
    'jsx-a11y/label-has-associated-control': 'error',
    'jsx-a11y/media-has-caption': 'error',
    'jsx-a11y/mouse-events-have-key-events': 'error',
    'jsx-a11y/no-access-key': 'error',
    'jsx-a11y/no-autofocus': 'error',
    'jsx-a11y/no-distracting-elements': 'error',
    'jsx-a11y/no-noninteractive-element-interactions': 'error',
    'jsx-a11y/no-noninteractive-tabindex': 'error',
    'jsx-a11y/no-redundant-roles': 'error',
    'jsx-a11y/role-has-required-aria-props': 'error',
    'jsx-a11y/role-supports-aria-props': 'error',
    'jsx-a11y/tabindex-no-positive': 'error',

    // ============================================
    // JAVASCRIPT RULES
    // ============================================
    
    'no-console': [
      'error',
      {
        allow: ['warn', 'error', 'info', 'table', 'time', 'timeEnd'],
      },
    ],
    
    'no-debugger': 'error',
    'no-alert': 'error',
    
    'no-unused-vars': 'off', // Using TypeScript version
    '@typescript-eslint/no-unused-vars': 'error',
    
    'no-shadow': 'off', // Using TypeScript version
    '@typescript-eslint/no-shadow': 'error',
    
    'no-await-in-loop': 'error',
    'no-promise-executor-return': 'error',
    'require-atomic-updates': 'error',
    'max-depth': ['error', 4],
    'max-nested-callbacks': ['error', 3],
    'max-params': ['error', 4],
    'max-lines-per-function': [
      'error',
      {
        max: 100,
        skipBlankLines: true,
        skipComments: true,
      },
    ],
    
    'complexity': ['error', 20],
    'curly': ['error', 'all'],
    'default-case': 'error',
    'default-case-last': 'error',
    'eqeqeq': ['error', 'always'],
    'no-else-return': ['error', { allowElseIf: false }],
    'no-implicit-coercion': 'error',
    'no-lonely-if': 'error',
    'no-nested-ternary': 'error',
    'no-unneeded-ternary': 'error',
    'one-var': ['error', 'never'],
    'operator-assignment': ['error', 'always'],
    'prefer-const': 'error',
    'prefer-destructuring': [
      'error',
      {
        array: true,
        object: true,
      },
    ],
    'prefer-exponentiation-operator': 'error',
    'prefer-template': 'error',
    'yoda': 'error',

    // ============================================
    // PROMISE RULES
    // ============================================
    
    'promise/catch-or-return': 'error',
    'promise/no-return-wrap': 'error',
    'promise/param-names': 'error',
    'promise/no-native': 'off',
    'promise/no-nesting': 'warn',
    'promise/no-promise-in-callback': 'warn',
    'promise/no-callback-in-promise': 'warn',
    'promise/avoid-new': 'off',
    'promise/no-new-statics': 'error',
    'promise/valid-params': 'error',

    // ============================================
    // TAILWINDCSS RULES
    // ============================================
    
    'tailwindcss/classnames-order': 'error',
    'tailwindcss/no-custom-classname': 'off',
    'tailwindcss/no-contradicting-classname': 'error',

    // ============================================
    // TESTING RULES
    // ============================================
    
    'jest/no-disabled-tests': 'warn',
    'jest/no-focused-tests': 'error',
    'jest/no-identical-title': 'error',
    'jest/prefer-to-have-length': 'warn',
    'jest/valid-expect': 'error',
    
    'testing-library/await-async-queries': 'error',
    'testing-library/await-async-utils': 'error',
    'testing-library/no-await-sync-queries': 'error',
    'testing-library/no-container': 'error',
    'testing-library/no-debugging-utils': 'error',
    'testing-library/no-dom-import': 'error',
    'testing-library/no-node-access': 'error',
    'testing-library/no-promise-in-fire-event': 'error',
    'testing-library/no-render-in-setup': 'error',
    'testing-library/no-unnecessary-act': 'error',
    'testing-library/no-wait-for-empty-callback': 'error',
    'testing-library/no-wait-for-multiple-assertions': 'error',
    'testing-library/no-wait-for-side-effects': 'error',
    'testing-library/no-wait-for-snapshot': 'error',
    'testing-library/prefer-find-by': 'error',
    'testing-library/prefer-presence-queries': 'error',
    'testing-library/prefer-query-by-disappearance': 'error',
    'testing-library/prefer-screen-queries': 'error',
    'testing-library/render-result-naming-convention': 'error',
  },

  // ============================================
  // OVERRIDES FOR SPECIFIC FILES/FOLDERS
  // ============================================
  
  overrides: [
    // ============================================
    // JAVASCRIPT FILES (NON-TYPESCRIPT)
    // ============================================
    
    {
      files: ['*.js', '*.cjs', '*.mjs'],
      parser: 'espree',
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
      rules: {
        '@typescript-eslint/no-var-requires': 'off',
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/explicit-module-boundary-types': 'off',
      },
    },

    // ============================================
    // CONFIGURATION FILES
    // ============================================
    
    {
      files: [
        '*.config.js',
        '*.config.ts',
        '.eslintrc.js',
        '.prettierrc.js',
        'tailwind.config.js',
        'next.config.js',
        'jest.config.js',
        'webpack.config.js',
      ],
      rules: {
        'import/no-default-export': 'off',
        '@typescript-eslint/no-var-requires': 'off',
        'unicorn/filename-case': 'off',
        'no-console': 'off',
        '@typescript-eslint/no-unsafe-assignment': 'off',
        '@typescript-eslint/no-unsafe-member-access': 'off',
      },
    },

    // ============================================
    // TEST FILES
    // ============================================
    
    {
      files: [
        '**/__tests__/**/*',
        '**/*.test.*',
        '**/*.spec.*',
      ],
      env: {
        jest: true,
        'jest/globals': true,
      },
      rules: {
        '@typescript-eslint/no-unsafe-assignment': 'off',
        '@typescript-eslint/no-unsafe-member-access': 'off',
        '@typescript-eslint/no-unsafe-call': 'off',
        '@typescript-eslint/no-unsafe-return': 'off',
        '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/unbound-method': 'off',
        '@typescript-eslint/require-await': 'off',
        '@typescript-eslint/no-floating-promises': 'off',
        '@typescript-eslint/no-non-null-assertion': 'off',
        'max-lines-per-function': 'off',
        'max-depth': 'off',
        'complexity': 'off',
        'sonarjs/no-duplicate-string': 'off',
        'security/detect-non-literal-fs-filename': 'off',
      },
    },

    // ============================================
    // STORYBOOK FILES
    // ============================================
    
    {
      files: ['**/*.stories.*'],
      rules: {
        'import/no-default-export': 'off',
        'react/prop-types': 'off',
        '@typescript-eslint/no-unsafe-assignment': 'off',
        '@typescript-eslint/no-unsafe-member-access': 'off',
      },
    },

    // ============================================
    // NEXT.JS SPECIFIC FILES
    // ============================================
    
    {
      files: [
        '**/pages/**/*',
        '**/app/**/*',
        '**/src/pages/**/*',
      ],
      rules: {
        'import/no-default-export': 'off',
        'react/react-in-jsx-scope': 'off',
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/explicit-module-boundary-types': 'off',
      },
    },

    // ============================================
    // API ROUTE FILES
    // ============================================
    
    {
      files: [
        '**/pages/api/**/*',
        '**/src/pages/api/**/*',
        '**/app/api/**/*',
      ],
      rules: {
        'import/no-default-export': 'off',
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/explicit-module-boundary-types': 'off',
        '@typescript-eslint/no-misused-promises': 'off',
        'no-console': 'off',
      },
    },

    // ============================================
    // BACKEND FILES
    // ============================================
    
    {
      files: [
        'backend/**/*.ts',
        'backend/**/*.tsx',
        'backend/**/*.js',
        'backend/**/*.jsx',
      ],
      rules: {
        'react/react-in-jsx-scope': 'off',
        'jsx-a11y/*': 'off',
        'tailwindcss/*': 'off',
      },
    },

    // ============================================
    // MACHINE LEARNING FILES
    // ============================================
    
    {
      files: [
        'backend/prediction-engine/**/*.py',
        'mlops/**/*.py',
      ],
      // Python files are handled by Black/Flake8, not ESLint
      excludedFiles: ['*.ts', '*.tsx', '*.js', '*.jsx'],
    },

    // ============================================
    // SCRIPTS & UTILITIES
    // ============================================
    
    {
      files: [
        'scripts/**/*',
        '**/scripts/**/*',
      ],
      rules: {
        'no-console': 'off',
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/explicit-module-boundary-types': 'off',
        'import/no-default-export': 'off',
        'unicorn/filename-case': 'off',
      },
    },

    // ============================================
    // MIGRATION FILES
    // ============================================
    
    {
      files: ['**/migrations/**/*'],
      rules: {
        '@typescript-eslint/explicit-function-return-type': 'off',
        'unicorn/filename-case': 'off',
      },
    },

    // ============================================
    // TYPE DEFINITION FILES
    // ============================================
    
    {
      files: ['*.d.ts'],
      rules: {
        '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/no-unused-vars': 'off',
        'import/no-default-export': 'off',
      },
    },
  ],

  // ============================================
  // SETTINGS
  // ============================================
  
  settings: {
    react: {
      version: 'detect',
    },
    'import/parsers': {
      '@typescript-eslint/parser': ['.ts', '.tsx', '.d.ts'],
    },
    'import/resolver': {
      typescript: {
        alwaysTryTypes: true,
        project: [
          './frontend/web-app/tsconfig.json',
          './backend/**/tsconfig.json',
          './**/tsconfig.json',
        ],
      },
      node: {
        extensions: ['.js', '.jsx', '.ts', '.tsx'],
      },
    },
    tailwindcss: {
      callees: ['classnames', 'clsx', 'ctl', 'cn'],
      config: 'tailwind.config.js',
      cssFiles: [
        '**/*.css',
        '**/*.scss',
        '**/*.sass',
        '!**/node_modules',
        '!**/.*',
      ],
      cssFilesRefreshRate: 5000,
      removeDuplicates: true,
      skipClassAttribute: false,
      whitelist: [],
    },
  },

  // ============================================
  // GLOBALS
  // ============================================
  
  globals: {
    React: 'writable',
    JSX: 'readonly',
    NodeJS: 'readonly',
    globalThis: 'readonly',
  },
};

module.exports = config;
