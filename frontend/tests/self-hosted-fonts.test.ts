/**
 * Las tipografías se sirven desde el mismo origen, y nada debe devolverlas al CDN.
 *
 * Google Fonts metía un tercero en la ruta crítica —dos conexiones nuevas y una
 * hoja de estilo bloqueante antes del primer pintado— y obligaba a abrir dos
 * agujeros en la CSP. Un `<link>` reintroducido a mano en `index.html` no
 * rompería nada visible: la página seguiría viéndose igual, solo más lenta, y
 * la CSP la bloquearía en producción sin que ningún test lo notara.
 *
 * También se comprueba el inyector del `preload`, que es el que ata el woff2
 * con hash del bundle a la shell que hereda cada ruta prerenderizada.
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

const FRONTEND_ROOT = join(__dirname, '..');
const REPO_ROOT = join(FRONTEND_ROOT, '..');

// Sin los comentarios: los de `index.html` nombran a Google Fonts justamente
// para explicar por qué ya no se usa, y eso no es una petición al CDN.
const shellHtml = readFileSync(join(FRONTEND_ROOT, 'index.html'), 'utf-8').replace(
  /<!--[\s\S]*?-->/g,
  ''
);
const netlifyToml = readFileSync(join(REPO_ROOT, 'netlify.toml'), 'utf-8');
const appCss = readFileSync(join(FRONTEND_ROOT, 'src/index.css'), 'utf-8');
const mainTsx = readFileSync(join(FRONTEND_ROOT, 'src/main.tsx'), 'utf-8');

const createdDirs: string[] = [];

afterEach(() => {
  for (const dir of createdDirs.splice(0)) {
    rmSync(dir, { recursive: true, force: true });
  }
});

/** Prepara un `dist` mínimo con la shell y el CSS que emitiría vite. */
function fakeDist({ css, html }: { css: string; html?: string }): string {
  const dir = mkdtempSync(join(tmpdir(), 'rf-fonts-'));
  createdDirs.push(dir);
  mkdirSync(join(dir, 'assets'), { recursive: true });
  writeFileSync(join(dir, 'assets', 'index-abc123.css'), css, 'utf-8');
  writeFileSync(
    join(dir, 'index.html'),
    html ??
      '<!doctype html>\n<html lang="es">\n  <head>\n    <link rel="stylesheet" crossorigin href="/assets/index-abc123.css">\n  </head>\n  <body></body>\n</html>\n',
    'utf-8'
  );
  return dir;
}

function injectFontPreload(distDir: string): string {
  execFileSync('node', [join(FRONTEND_ROOT, 'scripts/inject-font-preload.mjs'), distDir], {
    cwd: FRONTEND_ROOT,
    stdio: 'pipe',
  });
  return readFileSync(join(distDir, 'index.html'), 'utf-8');
}

const EMITTED_CSS = [
  "@font-face{font-family:'Inter Variable';src:url(/assets/inter-latin-ext-wght-normal-1111aaaa.woff2) format('woff2-variations')}",
  "@font-face{font-family:'Inter Variable';src:url(/assets/inter-latin-wght-normal-2222bbbb.woff2) format('woff2-variations')}",
  "@font-face{font-family:'Space Grotesk Variable';src:url(/assets/space-grotesk-latin-wght-normal-3333cccc.woff2) format('woff2-variations')}",
].join('\n');

describe('tipografías autoalojadas', () => {
  it('no carga ninguna fuente desde un tercero', () => {
    expect(shellHtml).not.toContain('fonts.googleapis.com');
    expect(shellHtml).not.toContain('fonts.gstatic.com');
    expect(appCss).not.toContain('fonts.googleapis.com');
    expect(appCss).not.toContain('fonts.gstatic.com');
  });

  it('importa las dos familias del bundle', () => {
    expect(mainTsx).toContain("import '@fontsource-variable/inter'");
    expect(mainTsx).toContain("import '@fontsource-variable/space-grotesk'");
  });

  it('usa las familias autoalojadas en los tokens de marca', () => {
    expect(appCss).toContain("--font-sans: 'Inter Variable'");
    expect(appCss).toContain("--font-heading: 'Space Grotesk Variable'");
  });

  it('mantiene la CSP sin orígenes de fuentes externos', () => {
    const csp = netlifyToml.match(/Content-Security-Policy = "([^"]+)"/)?.[1];
    expect(csp).toBeDefined();
    expect(csp).toContain("font-src 'self';");
    expect(csp).toContain("style-src 'self' 'unsafe-inline';");
    expect(csp).not.toContain('fonts.googleapis.com');
    expect(csp).not.toContain('fonts.gstatic.com');
  });
});

describe('preload de las fuentes en la shell', () => {
  it('precarga el subconjunto latino de cada familia con su hash', () => {
    const html = injectFontPreload(fakeDist({ css: EMITTED_CSS }));

    expect(html).toContain(
      '<link rel="preload" as="font" type="font/woff2" href="/assets/inter-latin-wght-normal-2222bbbb.woff2" crossorigin />'
    );
    expect(html).toContain(
      '<link rel="preload" as="font" type="font/woff2" href="/assets/space-grotesk-latin-wght-normal-3333cccc.woff2" crossorigin />'
    );
  });

  it('no precarga los subconjuntos que el castellano no necesita', () => {
    const html = injectFontPreload(fakeDist({ css: EMITTED_CSS }));

    expect(html).not.toContain('inter-latin-ext-wght-normal');
  });

  it('deja las etiquetas dentro del <head>', () => {
    const html = injectFontPreload(fakeDist({ css: EMITTED_CSS }));

    expect(html.indexOf('rel="preload"')).toBeLessThan(html.indexOf('</head>'));
  });

  it('falla si el bundle deja de emitir una de las fuentes', () => {
    const distDir = fakeDist({
      css: EMITTED_CSS.split('\n')
        .filter((line) => !line.includes('space-grotesk'))
        .join('\n'),
    });

    expect(() => injectFontPreload(distDir)).toThrow();
  });

  it('se inyecta antes de prerenderizar, que es de donde salen las copias por ruta', () => {
    const { scripts } = JSON.parse(readFileSync(join(FRONTEND_ROOT, 'package.json'), 'utf-8')) as {
      scripts: Record<string, string>;
    };

    expect(scripts.postbuild.indexOf('inject-font-preload.mjs')).toBeGreaterThanOrEqual(0);
    expect(scripts.postbuild.indexOf('inject-font-preload.mjs')).toBeLessThan(
      scripts.postbuild.indexOf('prerender.mjs')
    );
  });

  it('falla si la shell no enlaza ninguna hoja de estilo', () => {
    const distDir = fakeDist({
      css: EMITTED_CSS,
      html: '<!doctype html>\n<html lang="es">\n  <head></head>\n  <body></body>\n</html>\n',
    });

    expect(() => injectFontPreload(distDir)).toThrow();
  });
});
