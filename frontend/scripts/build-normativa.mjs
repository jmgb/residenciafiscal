#!/usr/bin/env node
/**
 * Genera los datos del corpus normativo que consume el frontend a partir de
 * `knowledge/normativa/<jurisdiccion>/`.
 *
 * Escribe dos cosas, por el mismo motivo que `build-corpus.mjs` no sirve el
 * JSONL entero: el articulado de los 108 preceptos son ~600 KB y nadie necesita
 * los 93 convenios para leer el artículo 9 LIRPF.
 *
 *   public/data/normativa.json          índice ligero de los 108 preceptos
 *   public/data/preceptos/<slug>.json   texto literal, uno por precepto
 *
 * El índice incorpora las sentencias que citan cada precepto, tomadas de
 * `enlaces/por_precepto.json`, que es lo que permite pasar del artículo a la
 * jurisprudencia y al revés.
 *
 * Igual que el corpus de sentencias, la salida se versiona como fallback para
 * que un clon limpio de Netlify no se quede sin datos. Si tampoco existe la
 * fuente, avisa por stderr y conserva lo versionado en lugar de romper el build.
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..');
const repoDir = join(frontendDir, '..');

const JURISDICCION = 'es';
const knowledgeDir = join(repoDir, 'knowledge', 'normativa', JURISDICCION);
const preceptosDir = join(knowledgeDir, 'preceptos');
const enlacesFile = join(knowledgeDir, 'enlaces', 'por_precepto.json');

const targetDir = join(frontendDir, 'public', 'data');
const indexFile = join(targetDir, 'normativa.json');
const textDir = join(targetDir, 'preceptos');

/** Encabezados con los que `export_normativa.py` rotula el articulado. */
const HEADING_VIGENTE = '# Texto vigente';
const HEADING_DEROGADO = '# Texto derogado';
const HEADING_ANTERIORES = '# Redacciones anteriores';
const HEADING_NOTAS = '# Notas del BOE';
const HEADING_PROCEDENCIA = '# Procedencia';

/**
 * Lee el frontmatter YAML sin dependencias: los ficheros los genera el pipeline
 * con un subconjunto muy acotado —escalares, listas de escalares y listas de
 * objetos planos—, así que un parser completo sería peso muerto.
 */
function parseFrontmatter(raw) {
  const end = raw.indexOf('\n---', 4);
  if (!raw.startsWith('---') || end === -1) {
    throw new Error('el fichero no empieza con un bloque de frontmatter');
  }
  const lines = raw.slice(4, end).split('\n');
  const data = {};
  let currentKey = null;
  let list = null;
  let pendingObject = null;

  const flush = () => {
    if (currentKey && list) data[currentKey] = list;
    list = null;
    pendingObject = null;
  };

  for (const line of lines) {
    if (!line.trim()) continue;
    const listItem = line.match(/^ {0,2}- (.*)$/);
    const nestedField = line.match(/^ {2,}(\w+): (.*)$/);
    const scalar = line.match(/^(\w+): ?(.*)$/);

    if (listItem) {
      list ??= [];
      const item = listItem[1];
      const inlineField = item.match(/^(\w+): (.*)$/);
      if (inlineField) {
        pendingObject = { [inlineField[1]]: parseScalar(inlineField[2]) };
        list.push(pendingObject);
      } else {
        list.push(parseScalar(item));
        pendingObject = null;
      }
      continue;
    }
    if (pendingObject && nestedField) {
      pendingObject[nestedField[1]] = parseScalar(nestedField[2]);
      continue;
    }
    if (scalar) {
      flush();
      currentKey = scalar[1];
      const value = scalar[2];
      // Una clave sin valor abre una lista o un objeto anidado; solo se
      // necesitan las listas (`tags`, `versiones`, `sources`).
      if (value === '') continue;
      data[currentKey] = parseScalar(value);
      currentKey = null;
      continue;
    }
    // Continuación de un escalar plegado por PyYAML en varias líneas.
    if (currentKey === null) continue;
  }
  flush();
  return data;
}

function parseScalar(value) {
  const trimmed = value.trim();
  if (trimmed === 'true') return true;
  if (trimmed === 'false') return false;
  if (trimmed === 'null' || trimmed === '') return null;
  if (/^'.*'$/.test(trimmed)) return trimmed.slice(1, -1);
  if (/^".*"$/.test(trimmed)) return trimmed.slice(1, -1);
  return trimmed;
}

/**
 * Recompone un escalar que PyYAML pudo plegar en varias líneas. Se hace sobre el
 * texto bruto para no perder palabras de un título largo.
 */
function readFoldedScalar(raw, key) {
  const pattern = new RegExp(`^${key}: (.*(?:\\n {2,}\\S.*)*)$`, 'm');
  const match = raw.slice(0, raw.indexOf('\n---', 4)).match(pattern);
  if (!match) return null;
  return parseScalar(match[1].replace(/\n\s+/g, ' '));
}

function sectionBetween(body, from, to) {
  const start = body.indexOf(from);
  if (start === -1) return '';
  const rest = body.slice(start + from.length);
  const end = to ? rest.indexOf(to) : -1;
  return (end === -1 ? rest : rest.slice(0, end)).trim();
}

/**
 * Párrafos que el fichero presenta como texto de la norma. Se descartan los
 * encabezados, los avisos en cita y los textos de ausencia en cursiva: no son
 * articulado, y publicarlos como tal rompería el invariante de literalidad.
 */
function paragraphs(section) {
  return section
    .split('\n')
    .map((line) => line.trim())
    .filter(
      (line) => line && !line.startsWith('#') && !line.startsWith('>') && !line.startsWith('_')
    );
}

function buildPrecepto(fileName, raw, citas) {
  const front = parseFrontmatter(raw);
  const body = raw.slice(raw.indexOf('\n---', 4) + 4);
  const derogada = front.derogada === true;
  const heading = derogada ? HEADING_DEROGADO : HEADING_VIGENTE;

  const articulado = paragraphs(sectionBetween(body, heading, HEADING_ANTERIORES));
  const anteriores = sectionBetween(body, HEADING_ANTERIORES, HEADING_NOTAS);
  const notas = paragraphs(sectionBetween(body, HEADING_NOTAS, HEADING_PROCEDENCIA))
    .filter((line) => line.startsWith('- '))
    .map((line) => line.slice(2));

  const slug = fileName.replace(/\.md$/, '');
  const titulo = readFoldedScalar(raw, 'title') ?? front.title;
  const norma = readFoldedScalar(raw, 'norma') ?? front.norma;

  return {
    slug,
    jurisdiccion: front.jurisdiccion,
    titulo,
    norma,
    designacion: front.designacion,
    epigrafe: front.epigrafe ?? null,
    grupo: front.grupo,
    boeId: front.boe_id,
    urlBoe: front.url_boe ?? null,
    derogada,
    notaDerogacion: front.nota_derogacion ?? null,
    vigenteDesde: front.vigente_desde ?? null,
    redacciones: (front.versiones ?? []).length,
    articulado,
    redaccionesAnteriores: anteriores.startsWith('_') ? [] : paragraphs(anteriores),
    notasBoe: notas,
    sentencias: citas,
  };
}

function loadCitas() {
  if (!existsSync(enlacesFile)) return new Map();
  const data = JSON.parse(readFileSync(enlacesFile, 'utf8'));
  return new Map(
    (data.preceptos ?? []).map((entry) => [
      entry.slug,
      entry.sentencias.map((s) => ({
        archivo: s.archivo,
        roj: s.roj ?? null,
        ejercicios: s.ejercicios ?? [],
        certeza: s.certeza,
      })),
    ])
  );
}

function main() {
  if (!existsSync(preceptosDir)) {
    process.stderr.write(
      `[normativa] No existe ${preceptosDir}; se conserva lo versionado en public/data.\n` +
        '[normativa] Regenéralo con `make export-normativa` desde la raíz del repositorio.\n'
    );
    return;
  }

  const citas = loadCitas();
  const files = readdirSync(preceptosDir)
    .filter((name) => name.endsWith('.md') && name !== 'index.md')
    .sort();

  const preceptos = files.map((name) =>
    buildPrecepto(
      name,
      readFileSync(join(preceptosDir, name), 'utf8'),
      citas.get(name.replace(/\.md$/, '')) ?? []
    )
  );

  mkdirSync(targetDir, { recursive: true });
  rmSync(textDir, { recursive: true, force: true });
  mkdirSync(textDir, { recursive: true });

  for (const precepto of preceptos) {
    writeFileSync(join(textDir, `${precepto.slug}.json`), `${JSON.stringify(precepto)}\n`, 'utf8');
  }

  // El índice omite el articulado: es lo que lo mantiene ligero.
  const index = preceptos.map(({ articulado, redaccionesAnteriores, notasBoe, ...resto }) => ({
    ...resto,
    parrafos: articulado.length,
    totalSentencias: new Set(resto.sentencias.map((s) => s.archivo)).size,
  }));

  writeFileSync(indexFile, `${JSON.stringify(index, null, 2)}\n`, 'utf8');

  const citados = index.filter((p) => p.totalSentencias > 0).length;
  process.stdout.write(
    `[normativa] ${index.length} preceptos (${citados} citados por sentencias) -> public/data/\n`
  );
}

main();
