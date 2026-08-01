/// <reference types="vitest/config" />
import path from 'node:path';
import { sentryVitePlugin } from '@sentry/vite-plugin';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import { resolveRelease } from './scripts/release.mjs';

const repositoryRoot = path.resolve(__dirname, '..');

export default defineConfig(({ mode, isSsrBuild }) => {
  const env = loadEnv(mode, repositoryRoot, '');
  // Mismo cálculo que `scripts/build-version.mjs`: el bundle y /version.json
  // tienen que declarar el mismo despliegue o la comprobación de versión miente.
  const revision = resolveRelease(mode);
  const release = `residencia-fiscal-frontend@${revision}`;
  const authToken = env.SENTRY_TOKEN || process.env.SENTRY_TOKEN;
  const sentryOrg = env.SENTRY_ORG_SLUG || process.env.SENTRY_ORG_SLUG;
  const sentryProject =
    env.SENTRY_FRONTEND_PROJECT_SLUG ||
    process.env.SENTRY_FRONTEND_PROJECT_SLUG ||
    'residencia-fiscal-frontend';
  // El bundle de servidor solo vive durante el build (lo consume
  // `scripts/prerender.mjs`): no se despliega, así que subir sus sourcemaps a
  // Sentry sería publicar un artefacto que ningún error puede mencionar.
  const uploadSourceMaps = mode === 'production' && !isSsrBuild && Boolean(authToken && sentryOrg);

  return {
    envDir: repositoryRoot,
    define: {
      __SENTRY_RELEASE__: JSON.stringify(release),
      __APP_RELEASE__: JSON.stringify(revision),
    },
    plugins: [
      react(),
      tailwindcss(),
      ...(uploadSourceMaps
        ? [
            sentryVitePlugin({
              authToken,
              org: sentryOrg,
              project: sentryProject,
              release: {
                name: release,
              },
              sourcemaps: {
                assets: './dist/assets/**',
                filesToDeleteAfterUpload: ['./dist/**/*.map'],
              },
              telemetry: false,
            }),
          ]
        : []),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '127.0.0.1',
      port: 5174,
    },
    build: {
      outDir: 'dist',
      sourcemap: uploadSourceMaps ? 'hidden' : false,
    },
    test: {
      environment: 'jsdom',
      environmentOptions: {
        jsdom: {
          url: 'https://residenciafiscal.org/',
        },
      },
      globals: true,
      setupFiles: ['./tests/setup.ts'],
      include: ['tests/**/*.test.{ts,tsx}'],
    },
  };
});
