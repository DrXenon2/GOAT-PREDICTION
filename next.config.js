/** @type {import('next').NextConfig} */
const nextConfig = {
  // ============================================
  // CORE CONFIGURATION
  // ============================================
  
  // React strict mode pour détecter les problèmes
  reactStrictMode: true,
  
  // Experimental features
  experimental: {
    // App Router features
    serverActions: {
      bodySizeLimit: '2mb'
    },
    optimizeCss: true,
    scrollRestoration: true,
    typedRoutes: true,
    workerThreads: true,
    // Turbopack pour le développement (beta)
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js'
        }
      }
    },
    // Optimisations mémoire
    memoryBasedWorkersCount: true,
    // Optimisations images
    optimizeServerReact: true,
    // Middleware avancé
    middlewarePrefetch: 'flexible',
    // Webpack 5 persistent caching
    webpackMemoryCache: true,
    // SWC minification améliorée
    swcMinify: true,
    // Partial prerendering
    ppr: true,
    // View Transitions API
    viewTransitions: true,
    // Server Components améliorés
    serverComponentsExternalPackages: [
      '@prisma/client',
      'bcryptjs',
      'jsonwebtoken',
      'sharp',
      'canvas',
      'onnxruntime-node'
    ]
  },
  
  // ============================================
  // COMPILER OPTIMIZATIONS
  // ============================================
  
  compiler: {
    // Supprime les console.log en production
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn']
    } : false,
    
    // Emotion/Styled Components support
    emotion: {
      sourceMap: process.env.NODE_ENV === 'development',
      autoLabel: 'dev-only',
      labelFormat: '[local]'
    },
    
    // Relay support
    relay: {
      src: './frontend/web-app/src',
      artifactDirectory: './frontend/web-app/__generated__',
      language: 'typescript'
    },
    
    // TypeScript avec SWC
    typescript: {
      ignoreBuildErrors: false,
      tsconfigPath: './frontend/web-app/tsconfig.json'
    }
  },
  
  // ============================================
  // IMAGES OPTIMIZATION
  // ============================================
  
  images: {
    // Formats d'image supportés
    formats: ['image/avif', 'image/webp'],
    
    // Domaines autorisés pour les images externes
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
        pathname: '**'
      }
    ],
    
    // Tailles d'image pour deviceSizes et imageSizes
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    
    // Contrôle du cache
    minimumCacheTTL: 60,
    disableStaticImages: false,
    
    // Content Security Policy pour les images
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    
    // Optimisation avancée
    unoptimized: process.env.NODE_ENV === 'development',
    
    // Loader personnalisé pour Cloudinary/S3
    loader: 'default',
    loaderFile: './frontend/web-app/src/lib/image-loader.js',
    
    // Remote Patterns pour les sources d'images
    domains: [
      'localhost',
      'goat-prediction.com',
      'api.goat-prediction.com',
      'cdn.goat-prediction.com',
      'res.cloudinary.com',
      'images.unsplash.com',
      'picsum.photos',
      'source.unsplash.com',
      '*.amazonaws.com',
      '*.googleapis.com',
      '*.cloudfront.net'
    ]
  },
  
  // ============================================
  // HEADERS & SECURITY
  // ============================================
  
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Security Headers
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()'
          },
          {
            key: 'Content-Security-Policy',
            value: `
              default-src 'self';
              script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http:;
              style-src 'self' 'unsafe-inline' https:;
              img-src 'self' data: https: http:;
              font-src 'self' https:;
              connect-src 'self' https: http: ws: wss:;
              frame-src 'self' https:;
              media-src 'self' https:;
              object-src 'none';
              base-uri 'self';
              form-action 'self';
              frame-ancestors 'self';
              block-all-mixed-content;
              upgrade-insecure-requests;
            `.replace(/\s+/g, ' ').trim()
          },
          // Performance Headers
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable'
          }
        ]
      },
      {
        source: '/api/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, no-cache, must-revalidate, proxy-revalidate'
          },
          {
            key: 'Pragma',
            value: 'no-cache'
          },
          {
            key: 'Expires',
            value: '0'
          }
        ]
      },
      {
        source: '/_next/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable'
          }
        ]
      }
    ]
  },
  
  // ============================================
  // REDIRECTS & REWRITES
  // ============================================
  
  async redirects() {
    return [
      {
        source: '/old-betting/:path*',
        destination: '/betting/:path*',
        permanent: true
      },
      {
        source: '/predictions/legacy/:path*',
        destination: '/predictions/:path*',
        permanent: true
      },
      {
        source: '/admin',
        destination: '/admin/dashboard',
        permanent: false
      },
      {
        source: '/login',
        destination: '/auth/login',
        permanent: true
      },
      {
        source: '/register',
        destination: '/auth/register',
        permanent: true
      }
    ]
  },
  
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*'
      },
      {
        source: '/api/v2/:path*',
        destination: 'http://localhost:8000/api/v2/:path*'
      },
      {
        source: '/ml-api/:path*',
        destination: 'http://localhost:8001/:path*'
      },
      {
        source: '/ws/:path*',
        destination: 'ws://localhost:8000/ws/:path*'
      },
      // Rewrites pour les fichiers statiques
      {
        source: '/static/:path*',
        destination: '/_next/static/:path*'
      }
    ]
  },
  
  // ============================================
  // WEBPACK CONFIGURATION
  // ============================================
  
  webpack: (config, { isServer, dev, webpack }) => {
    // Configurations communes
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      net: false,
      tls: false,
      crypto: require.resolve('crypto-browserify'),
      stream: require.resolve('stream-browserify'),
      path: require.resolve('path-browserify'),
      zlib: require.resolve('browserify-zlib'),
      http: require.resolve('stream-http'),
      https: require.resolve('https-browserify'),
      os: require.resolve('os-browserify/browser'),
      assert: require.resolve('assert')
    }
    
    // Plugins Webpack
    config.plugins.push(
      new webpack.DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV),
        'process.env.BUILD_ID': JSON.stringify(process.env.BUILD_ID || 'development'),
        'process.env.APP_VERSION': JSON.stringify(process.env.npm_package_version || '1.0.0')
      }),
      new webpack.ProvidePlugin({
        Buffer: ['buffer', 'Buffer']
      })
    )
    
    // Optimisations pour le client
    if (!isServer) {
      // Split chunks optimization
      config.optimization.splitChunks = {
        chunks: 'all',
        minSize: 20000,
        maxSize: 244000,
        minChunks: 1,
        maxAsyncRequests: 30,
        maxInitialRequests: 30,
        automaticNameDelimiter: '~',
        enforceSizeThreshold: 50000,
        cacheGroups: {
          defaultVendors: {
            test: /[\\/]node_modules[\\/]/,
            priority: -10,
            reuseExistingChunk: true
          },
          default: {
            minChunks: 2,
            priority: -20,
            reuseExistingChunk: true
          },
          // React et Core chunks
          react: {
            name: 'react',
            test: /[\\/]node_modules[\\/](react|react-dom|react-is|scheduler|prop-types)[\\/]/,
            priority: 40
          },
          // UI components chunks
          ui: {
            name: 'ui',
            test: /[\\/]node_modules[\\/](@radix-ui|class-variance-authority|clsx|tailwind-merge|lucide-react)[\\/]/,
            priority: 30
          },
          // Charts & Visualization
          charts: {
            name: 'charts',
            test: /[\\/]node_modules[\\/](recharts|victory|d3|apexcharts|chart\.js|echarts)[\\/]/,
            priority: 20
          },
          // Forms & Validation
          forms: {
            name: 'forms',
            test: /[\\/]node_modules[\\/](react-hook-form|zod|yup|formik)[\\/]/,
            priority: 15
          },
          // State Management
          state: {
            name: 'state',
            test: /[\\/]node_modules[\\/](zustand|redux|@reduxjs|mobx|recoil|jotai)[\\/]/,
            priority: 10
          }
        }
      }
      
      // Performance optimizations
      config.performance = {
        maxAssetSize: 244000,
        maxEntrypointSize: 244000,
        hints: process.env.NODE_ENV === 'production' ? 'warning' : false
      }
    }
    
    // Configurations pour le serveur
    if (isServer) {
      // Externals pour le serveur
      config.externals.push({
        'utf-8-validate': 'commonjs utf-8-validate',
        'bufferutil': 'commonjs bufferutil'
      })
    }
    
    // Loaders personnalisés
    config.module.rules.push(
      // SVG loader avec SVGR
      {
        test: /\.svg$/i,
        issuer: /\.[jt]sx?$/,
        use: [
          {
            loader: '@svgr/webpack',
            options: {
              svgo: true,
              svgoConfig: {
                plugins: [
                  {
                    name: 'preset-default',
                    params: {
                      overrides: {
                        removeViewBox: false,
                        cleanupIDs: false
                      }
                    }
                  }
                ]
              }
            }
          }
        ]
      },
      // GLSL/Shader loader
      {
        test: /\.(glsl|vs|fs|vert|frag)$/i,
        use: ['raw-loader', 'glslify-loader']
      },
      // CSV loader
      {
        test: /\.csv$/,
        use: ['csv-loader']
      },
      // XML loader
      {
        test: /\.xml$/,
        use: ['xml-loader']
      }
    )
    
    // Optimisation des résolutions
    config.resolve.alias = {
      ...config.resolve.alias,
      // Alias pour les chemins du projet
      '@': require('path').resolve(__dirname, 'frontend/web-app/src'),
      '@components': require('path').resolve(__dirname, 'frontend/web-app/src/components'),
      '@lib': require('path').resolve(__dirname, 'frontend/web-app/src/lib'),
      '@utils': require('path').resolve(__dirname, 'frontend/web-app/src/lib/utils'),
      '@styles': require('path').resolve(__dirname, 'frontend/web-app/src/styles'),
      '@hooks': require('path').resolve(__dirname, 'frontend/web-app/src/hooks'),
      '@store': require('path').resolve(__dirname, 'frontend/web-app/src/store'),
      '@types': require('path').resolve(__dirname, 'frontend/web-app/src/lib/types'),
      '@config': require('path').resolve(__dirname, 'frontend/web-app/src/config'),
      '@services': require('path').resolve(__dirname, 'frontend/web-app/src/lib/services'),
      '@contexts': require('path').resolve(__dirname, 'frontend/web-app/src/contexts'),
      '@public': require('path').resolve(__dirname, 'frontend/web-app/public'),
      // Alias pour éviter les warnings
      'next/font/google': require.resolve('next/font/google'),
      'next/font/local': require.resolve('next/font/local')
    }
    
    // Optimisation des extensions
    config.resolve.extensions = [
      '.tsx', '.ts', '.jsx', '.js', '.mjs', '.json', '.wasm'
    ]
    
    // Cache pour le développement
    if (dev) {
      config.cache = {
        type: 'filesystem',
        buildDependencies: {
          config: [__filename]
        }
      }
    }
    
    return config
  },
  
  // ============================================
  // ENVIRONMENT VARIABLES
  // ============================================
  
  env: {
    // Core App Configuration
    APP_NAME: process.env.APP_NAME || 'GOAT Prediction Ultimate',
    APP_VERSION: process.env.npm_package_version || '1.0.0',
    APP_ENV: process.env.NODE_ENV || 'development',
    APP_URL: process.env.APP_URL || 'http://localhost:3000',
    API_URL: process.env.API_URL || 'http://localhost:8000',
    ML_API_URL: process.env.ML_API_URL || 'http://localhost:8001',
    
    // Feature Flags
    ENABLE_BETTING: process.env.ENABLE_BETTING || 'true',
    ENABLE_LIVE_PREDICTIONS: process.env.ENABLE_LIVE_PREDICTIONS || 'true',
    ENABLE_ADVANCED_ANALYTICS: process.env.ENABLE_ADVANCED_ANALYTICS || 'true',
    ENABLE_MULTI_SPORT: process.env.ENABLE_MULTI_SPORT || 'true',
    
    // Sports Configuration
    SUPPORTED_SPORTS: process.env.SUPPORTED_SPORTS || 'football,basketball,tennis,esports',
    
    // API Keys (public)
    GOOGLE_ANALYTICS_ID: process.env.GOOGLE_ANALYTICS_ID || '',
    SENTRY_DSN: process.env.SENTRY_DSN || '',
    MAPBOX_TOKEN: process.env.MAPBOX_TOKEN || '',
    
    // Build Information
    BUILD_ID: process.env.BUILD_ID || Date.now().toString(),
    BUILD_TIME: new Date().toISOString(),
    COMMIT_SHA: process.env.VERCEL_GIT_COMMIT_SHA || '',
    BRANCH: process.env.VERCEL_GIT_COMMIT_REF || 'main'
  },
  
  // ============================================
  // I18N CONFIGURATION
  // ============================================
  
  i18n: {
    locales: ['en', 'fr', 'es', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh'],
    defaultLocale: 'en',
    localeDetection: true,
    domains: [
      {
        domain: 'goat-prediction.com',
        defaultLocale: 'en'
      },
      {
        domain: 'goat-prediction.fr',
        defaultLocale: 'fr'
      },
      {
        domain: 'goat-prediction.es',
        defaultLocale: 'es'
      }
    ]
  },
  
  // ============================================
  // PWA CONFIGURATION
  // ============================================
  
  pwa: {
    dest: 'public',
    disable: process.env.NODE_ENV === 'development',
    register: true,
    skipWaiting: true,
    runtimeCaching: [
      {
        urlPattern: /^https?.*/,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'https-calls',
          networkTimeoutSeconds: 15,
          expiration: {
            maxEntries: 150,
            maxAgeSeconds: 30 * 24 * 60 * 60 // 30 days
          },
          cacheableResponse: {
            statuses: [0, 200]
          }
        }
      },
      {
        urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'images',
          expiration: {
            maxEntries: 1000,
            maxAgeSeconds: 365 * 24 * 60 * 60 // 1 year
          }
        }
      },
      {
        urlPattern: /\.(?:js|css)$/,
        handler: 'StaleWhileRevalidate',
        options: {
          cacheName: 'static-resources',
          expiration: {
            maxEntries: 1000,
            maxAgeSeconds: 7 * 24 * 60 * 60 // 7 days
          }
        }
      }
    ]
  },
  
  // ============================================
  // OUTPUT & BUILD CONFIGURATION
  // ============================================
  
  // Output configuration
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  
  // Build output directory
  distDir: process.env.NEXT_BUILD_DIR || '.next',
  
  // Generate build ID
  generateBuildId: async () => {
    return process.env.BUILD_ID || `build-${Date.now()}`
  },
  
  // Production browser source maps
  productionBrowserSourceMaps: process.env.NODE_ENV === 'development',
  
  // ============================================
  // ON-DEMAND ISR & CACHING
  // ============================================
  
  // Incremental Static Regeneration
  onDemandEntries: {
    // period (in ms) where the server will keep pages in the buffer
    maxInactiveAge: 25 * 1000,
    // number of pages that should be kept simultaneously without being disposed
    pagesBufferLength: 2
  },
  
  // ============================================
  // TRAILING SLASH CONFIGURATION
  // ============================================
  
  trailingSlash: false,
  
  // ============================================
  // ASSET PREFIX (CDN)
  // ============================================
  
  assetPrefix: process.env.CDN_URL || '',
  
  // ============================================
  // BASE PATH CONFIGURATION
  // ============================================
  
  basePath: process.env.BASE_PATH || '',
  
  // ============================================
  // CUSTOM SERVER CONFIGURATION
  // ============================================
  
  // Custom server configuration
  serverRuntimeConfig: {
    // Will only be available on the server side
    PROJECT_ROOT: __dirname,
    SECRET_KEY: process.env.SECRET_KEY,
    JWT_SECRET: process.env.JWT_SECRET,
    DATABASE_URL: process.env.DATABASE_URL,
    REDIS_URL: process.env.REDIS_URL,
    ML_MODELS_PATH: process.env.ML_MODELS_PATH || './backend/prediction-engine/models'
  },
  
  publicRuntimeConfig: {
    // Will be available on both server and client
    APP_NAME: process.env.APP_NAME || 'GOAT Prediction Ultimate',
    APP_VERSION: process.env.npm_package_version || '1.0.0',
    API_BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    WS_BASE_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    ENABLE_ANALYTICS: process.env.NEXT_PUBLIC_ENABLE_ANALYTICS || 'false',
    SENTRY_DSN: process.env.NEXT_PUBLIC_SENTRY_DSN || '',
    GA_MEASUREMENT_ID: process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || '',
    MAPBOX_TOKEN: process.env.NEXT_PUBLIC_MAPBOX_TOKEN || ''
  },
  
  // ============================================
  // MIDDLEWARE CONFIGURATION
  // ============================================
  
  // Middleware matcher
  middleware: {
    matcher: [
      '/((?!api|_next/static|_next/image|favicon.ico|public|static).*)'
    ]
  },
  
  // ============================================
  // ANALYTICS & MONITORING
  // ============================================
  
  // Analytics configuration
  analyticsId: process.env.ANALYTICS_ID || '',
  
  // ============================================
  // SWC MINIFICATION
  // ============================================
  
  swcMinify: true,
  
  // ============================================
  // COMPRESSION
  // ============================================
  
  compress: true,
  
  // ============================================
  // POWERED BY HEADER
  // ============================================
  
  poweredByHeader: false,
  
  // ============================================
  // STATIC EXPORT CONFIGURATION
  // ============================================
  
  // Static export configuration
  // output: 'export', // Uncomment for static export
  
  // ============================================
  // CROSS-ORIGIN CONFIGURATION
  // ============================================
  
  crossOrigin: 'anonymous',
  
  // ============================================
  // MODULARIZE IMPORTS (OPTIONAL)
  // ============================================
  
  modularizeImports: {
    'lodash': {
      transform: 'lodash/{{member}}'
    },
    'date-fns': {
      transform: 'date-fns/{{member}}'
    },
    '@radix-ui/react-icons': {
      transform: '@radix-ui/react-icons/{{member}}'
    }
  },
  
  // ============================================
  // BUNDLE ANALYZER (DEV ONLY)
  // ============================================
  
  bundleAnalyzer: {
    enabled: process.env.ANALYZE === 'true',
    openAnalyzer: true,
    analyzerMode: 'static',
    reportFilename: '../bundles/analyzer.html'
  },
  
  // ============================================
  // TURBOPACK (EXPERIMENTAL)
  // ============================================
  
  // Uncomment for Turbopack (Next.js 14+)
  // turbopack: {
  //   resolveAlias: {
  //     'react-native': 'react-native-web'
  //   }
  // },
  
  // ============================================
  // CUSTOM ERROR PAGES
  // ============================================
  
  // Custom error pages configuration
  // Custom 404 and 500 pages are handled by Next.js automatically
  
  // ============================================
  // PROGRESS BAR CONFIGURATION
  // ============================================
  
  // Next.js progress bar
  devIndicators: {
    buildActivity: true,
    buildActivityPosition: 'bottom-right'
  },
  
  // ============================================
  // PAGE EXTENSIONS
  // ============================================
  
  pageExtensions: ['tsx', 'ts', 'jsx', 'js', 'mdx'],
  
  // ============================================
  // MDX CONFIGURATION
  // ============================================
  
  mdxRs: {
    development: process.env.NODE_ENV === 'development'
  },
  
  // ============================================
  // EXPERIMENTAL: PARTIAL PRERENDERING
  // ============================================
  
  // Experimental: Partial Prerendering (Next.js 14+)
  experimentalPPR: true,
  
  // ============================================
  // SERVER COMPONENTS EXTERNAL PACKAGES
  // ============================================
  
  // Packages that should be externalized for server components
  serverExternalPackages: [
    '@prisma/client',
    'bcryptjs',
    'jsonwebtoken',
    'sharp',
    'onnxruntime-node',
    '@tensorflow/tfjs-node',
    'canvas',
    'pdfkit'
  ],
  
  // ============================================
  // LOGGING CONFIGURATION
  // ============================================
  
  logging: {
    fetches: {
      fullUrl: true
    }
  },
  
  // ============================================
  // FINAL EXPORT
  // ============================================
  
  // Export configuration
  exportPathMap: async function(defaultPathMap, { dev, dir, outDir, distDir, buildId }) {
    return {
      '/': { page: '/' },
      '/predictions': { page: '/predictions' },
      '/betting': { page: '/betting' },
      '/analytics': { page: '/analytics' },
      '/admin': { page: '/admin' },
      '/auth/login': { page: '/auth/login' },
      '/auth/register': { page: '/auth/register' },
      '/api/health': { page: '/api/health' }
    }
  }
}

// Configuration conditionnelle pour l'environnement
const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development'
})

const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true'
})

const withMDX = require('@next/mdx')({
  extension: /\.mdx?$/,
  options: {
    remarkPlugins: [],
    rehypePlugins: []
  }
})

const withPlugins = require('next-compose-plugins')

module.exports = withPlugins([
  [withPWA],
  [withBundleAnalyzer],
  [withMDX, { pageExtensions: ['ts', 'tsx', 'js', 'jsx', 'md', 'mdx'] }]
], nextConfig)
