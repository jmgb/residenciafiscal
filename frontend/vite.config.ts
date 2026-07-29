/// <reference types="vitest/config" />
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { sentryVitePlugin } from '@sentry/vite-plugin';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

const repositoryRoot = path.resolve(__dirname, '..');

const getGitRevision = (): string => {
  try {
    return execFileSync('git', ['rev-parse', '--short=12', 'HEAD'], {
      cwd: repositoryRoot,
    })
      .toString()
      .trim();
  } catch {
    return 'local';
  }
};

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repositoryRoot, '');
  const revision =
    env.VITE_SENTRY_RELEASE || process.env.COMMIT_REF?.slice(0, 12) || getGitRevision();
  const release = `residencia-fiscal-frontend@${revision}`;
  const authToken =
    env.SENTRY_AUTH_TOKEN ||
    env.SENTRY_PERSONAL_API_TOKEN ||
    process.env.SENTRY_AUTH_TOKEN ||
    process.env.SENTRY_PERSONAL_API_TOKEN;
  const sentryOrg = env.SENTRY_ORG_SLUG || process.env.SENTRY_ORG_SLUG;
  const sentryProject =
    env.SENTRY_FRONTEND_PROJECT_SLUG ||
    process.env.SENTRY_FRONTEND_PROJECT_SLUG ||
    'residencia-fiscal-frontend';
  const uploadSourceMaps = mode === 'production' && Boolean(authToken && sentryOrg);

  return {
    envDir: repositoryRoot,
    define: {
      __SENTRY_RELEASE__: JSON.stringify(release),
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
