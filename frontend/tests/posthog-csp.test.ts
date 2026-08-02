import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const REPO_ROOT = join(__dirname, '..', '..');
const netlifyToml = readFileSync(join(REPO_ROOT, 'netlify.toml'), 'utf-8');
const csp = netlifyToml.match(/Content-Security-Policy = "([^"]+)"/)?.[1];

const sourcesFor = (directive: string): string[] => {
  const value = csp
    ?.split(';')
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(`${directive} `));

  return value?.split(/\s+/).slice(1) ?? [];
};

describe('CSP de PostHog', () => {
  it.each(['script-src', 'script-src-elem', 'connect-src'])(
    'permite el host de configuración remota en %s',
    (directive) => {
      expect(sourcesFor(directive)).toContain('https://eu-assets.i.posthog.com');
    }
  );
});
