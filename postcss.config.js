/** @type {import('postcss').Postcss} */
module.exports = {
  // Plugins PostCSS
  plugins: {
    // Import automatique de Tailwind CSS
    'tailwindcss/nesting': {},
    'tailwindcss': {},
    
    // Autoprefixer pour les préfixes navigateurs
    'autoprefixer': {
      flexbox: 'no-2009',
      grid: 'autoplace',
      overrideBrowserslist: [
        'last 2 versions',
        '> 1%',
        'iOS >= 12',
        'Safari >= 12',
        'not dead'
      ]
    },
    
    // PostCSS Preset Env pour les fonctionnalités CSS futures
    'postcss-preset-env': {
      stage: 3,
      features: {
        'custom-properties': true,
        'nesting-rules': true,
        'custom-media-queries': true,
        'media-query-ranges': true,
        'custom-selectors': true,
        'color-function': true,
        'color-mix': true,
        'oklab-function': true,
        'lab-function': true,
        'font-format-keywords': true,
        'double-position-gradients': true,
        'logical-properties-and-values': true,
        'hexadecimal-alpha-notation': true,
        'system-ui-font-family': true,
        'cascade-layers': false
      },
      preserve: false,
      minimumVendorImplementations: 2
    },
    
    // CSS Nano pour la minification en production
    'cssnano': process.env.NODE_ENV === 'production' ? {
      preset: ['advanced', {
        cssDeclarationSorter: false,
        discardComments: {
          removeAll: true
        },
        normalizeCharset: {
          add: true
        },
        colormin: true,
        convertValues: true,
        discardEmpty: true,
        discardDuplicates: true,
        discardOverridden: true,
        mergeLonghand: true,
        mergeRules: true,
        minifyFontValues: true,
        minifyGradients: true,
        minifyParams: true,
        minifySelectors: true,
        normalizeDisplayValues: true,
        normalizePositions: true,
        normalizeRepeatStyle: true,
        normalizeString: true,
        normalizeTimingFunctions: true,
        normalizeUnicode: true,
        normalizeUrl: true,
        normalizeWhitespace: true,
        orderedValues: true,
        reduceInitial: true,
        reduceTransforms: true,
        svgo: true,
        uniqueSelectors: true,
        zindex: true
      }]
    } : false,
    
    // PostCSS Import pour gérer les imports CSS
    'postcss-import': {
      path: ['frontend/web-app/src/styles'],
      filter: (path) => {
        // Ignorer les imports de node_modules sauf ceux spécifiques
        return !path.includes('node_modules') || 
               path.includes('@fontsource') ||
               path.includes('tailwindcss')
      }
    },
    
    // PostCSS Nested pour le nesting CSS
    'postcss-nested': {},
    
    // PostCSS Custom Properties pour les variables CSS
    'postcss-custom-properties': {
      preserve: false,
      importFrom: [
        'frontend/web-app/src/styles/theme.css'
      ]
    },
    
    // PostCSS Flexbugs Fixes pour corriger les bugs flexbox
    'postcss-flexbugs-fixes': {},
    
    // PostCSS Viewport Height Correction pour mobile
    'postcss-viewport-height-correction': {},
    
    // PostCSS 100vh Fix pour iOS
    'postcss-100vh-fix': {},
    
    // PostCSS Font Smoothing
    'postcss-font-smoothing': {},
    
    // PostCSS Focus Visible pour l'accessibilité
    'postcss-focus-visible': {},
    
    // PostCSS Focus Within pour l'accessibilité
    'postcss-focus-within': {},
    
    // PostCSS Object Fit Images pour le support IE
    'postcss-object-fit-images': {},
    
    // PostCSS Page Break pour l'impression
    'postcss-page-break': {},
    
    // PostCSS Normalize pour reset CSS
    'postcss-normalize': {
      forceImport: true,
      allowDuplicates: false
    },
    
    // PostCSS Sorting pour organiser les propriétés CSS
    'postcss-sorting': process.env.NODE_ENV === 'development' ? {
      order: [
        'custom-properties',
        'dollar-variables',
        'declarations',
        'at-rules',
        'rules'
      ],
      'properties-order': 'alphabetical',
      'unspecified-properties-position': 'bottom'
    } : false,
    
    // PostCSS Reporter pour les warnings
    'postcss-reporter': {
      clearReportedMessages: true,
      throwError: false
    },
    
    // PostCSS Browser Reporter pour le développement
    'postcss-browser-reporter': process.env.NODE_ENV === 'development' ? {} : false,
    
    // PostCSS URL pour optimiser les URLs
    'postcss-url': {
      url: 'inline',
      maxSize: 10,
      fallback: 'copy'
    },
    
    // PostCSS Assets pour gérer les assets
    'postcss-assets': {
      loadPaths: [
        'frontend/web-app/public/images',
        'frontend/web-app/public/icons'
      ],
      basePath: 'frontend/web-app',
      cachebuster: true
    },
    
    // PostCSS Inline SVG pour les SVGs inline
    'postcss-inline-svg': {
      paths: ['frontend/web-app/public/icons']
    },
    
    // PostCSS Responsive Type pour la typographie responsive
    'postcss-responsive-type': {},
    
    // PostCSS Will Change pour les performances
    'postcss-will-change': {},
    
    // PostCSS Opacity pour le support IE
    'postcss-opacity': {},
    
    // PostCSS Pseudoelements pour les pseudo-éléments
    'postcss-pseudoelements': {},
    
    // PostCSS Triangle pour créer des triangles CSS
    'postcss-triangle': {},
    
    // PostCSS Circle pour créer des cercles CSS
    'postcss-circle': {},
    
    // PostCSS Placeholder pour les placeholders
    'postcss-placeholder': {},
    
    // PostCSS Color RGBA Fallback pour IE8
    'postcss-color-rgba-fallback': {},
    
    // PostCSS Color RGB Fallback pour IE8
    'postcss-color-rgb-fallback': {},
    
    // PostCSS Gradient Fixer pour les gradients
    'postcss-gradientfixer': {},
    
    // PostCSS Oldie pour le support vieux navigateurs
    'postcss-oldie': process.env.NODE_ENV === 'production' ? {
      browsers: ['ie >= 9', 'ie_mob >= 10']
    } : false,
    
    // PostCSS RTLCSS pour le support RTL
    'rtlcss': process.env.RTL === 'true' ? {
      autoRename: true,
      autoRenameStrict: true,
      blacklist: {},
      clean: true,
      greedy: false,
      processUrls: true,
      stringMap: []
    } : false
  },
  
  // Configuration PostCSS
  parser: 'postcss-scss',
  syntax: 'postcss-scss',
  map: process.env.NODE_ENV === 'development' ? {
    inline: true,
    annotation: true,
    sourcesContent: true
  } : false,
  
  // Sources
  from: 'frontend/web-app/src/styles/globals.css',
  to: 'frontend/web-app/.next/static/css/globals.css',
  
  // Extensions de fichiers
  extensions: ['.css', '.scss', '.sass', '.pcss'],
  
  // Extract pour PurgeCSS
  extract: {
    content: [
      './frontend/web-app/src/**/*.{js,jsx,ts,tsx}',
      './frontend/web-app/pages/**/*.{js,jsx,ts,tsx}',
      './frontend/web-app/components/**/*.{js,jsx,ts,tsx}',
      './frontend/web-app/app/**/*.{js,jsx,ts,tsx}',
      './frontend/admin-dashboard/**/*.{js,jsx,ts,tsx}'
    ],
    defaultExtractor: content => content.match(/[\w-/:]+(?<!:)/g) || [],
    safelist: [
      'html',
      'body',
      /^slick-/,
      /^carousel-/,
      /^modal-/,
      /^drawer-/,
      /^popover-/,
      /^tooltip-/,
      /^Toast/,
      /^Notification/,
      /^animate-/,
      /^slide-/,
      /^fade-/,
      /^scale-/,
      /^spin-/,
      /^ping-/,
      /^pulse-/,
      /^bounce-/,
      /^live-/,
      /^float-/,
      /^shimmer-/,
      /^glass/,
      /^text-stroke/,
      /^no-scrollbar/,
      /^card-hover/,
      /^live-indicator/,
      /^theme-/,
      /^dark/,
      /^light/,
      /^rtl/,
      /^ltr/
    ]
  },
  
  // Cache pour le développement
  cache: process.env.NODE_ENV === 'development' ? {
    cacheDirectory: './node_modules/.cache/postcss',
    cacheIdentifier: JSON.stringify({
      'postcss': require('postcss/package.json').version,
      'tailwindcss': require('tailwindcss/package.json').version,
      'autoprefixer': require('autoprefixer/package.json').version,
      'env': process.env.NODE_ENV
    })
  } : false,
  
  // Parallel processing
  parallel: process.env.NODE_ENV === 'production',
  
  // Source maps
  sourceMap: process.env.NODE_ENV === 'development' ? 'inline' : false,
  
  // Minimiser en production
  minimize: process.env.NODE_ENV === 'production',
  
  // Plugins à exécuter uniquement en production
  productionPlugins: [
    'cssnano',
    'postcss-oldie'
  ],
  
  // Plugins à exécuter uniquement en développement
  developmentPlugins: [
    'postcss-browser-reporter',
    'postcss-sorting'
  ],
  
  // Configuration pour Next.js
  config: {
    ctx: {
      env: process.env.NODE_ENV,
      theme: process.env.THEME || 'light'
    }
  }
};
