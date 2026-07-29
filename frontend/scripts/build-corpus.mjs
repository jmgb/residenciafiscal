#!/usr/bin/env node
/**
 * Genera `public/data/corpus.json` a partir del análisis más reciente del
 * pipeline Python (`output/analisis_*.jsonl`).
 *
 * Solo se publican metadatos ligeros: el JSONL completo (~900 KB con
 * razonamientos y pruebas) no se sirve al navegador.
 *
 * Se ejecuta en `prebuild`. El corpus generado se versiona como fallback para
 * que Netlify no lo pierda en un clon limpio donde `output/` está ignorado.
 * Si tampoco existe ese fallback, escribe un corpus vacío y avisa en lugar de
 * romper el build.
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..');
const outputDir = join(frontendDir, '..', 'output');
const targetDir = join(frontendDir, 'public', 'data');
const targetFile = join(targetDir, 'corpus.json');

const VALID_RESULTS = new Set([
  'GANA_AEAT',
  'GANA_CONTRIBUYENTE',
  'PARCIAL',
  'RETROACCION',
  'INADMISION',
]);

function findLatestJsonl() {
  if (!existsSync(outputDir)) return null;
  const candidates = readdirSync(outputDir)
    .filter((name) => name.startsWith('analisis_') && name.endsWith('.jsonl'))
    .map((name) => {
      const path = join(outputDir, name);
      return { path, mtime: statSync(path).mtimeMs };
    })
    .sort((a, b) => b.mtime - a.mtime);
  return candidates[0]?.path ?? null;
}

function toEntry(raw) {
  const ids = raw.identificadores ?? {};
  const resultado = VALID_RESULTS.has(raw.resultado_final) ? raw.resultado_final : 'DESCONOCIDO';
  const criterio = Array.isArray(raw.Criterio_decisivo)
    ? raw.Criterio_decisivo.filter((c) => typeof c === 'string')
    : [];
  return {
    archivo: raw.archivo ?? '',
    roj: ids.ROJ ?? '',
    ecli: ids.ECLI ?? '',
    organo: raw.organo ?? '',
    fecha: raw.fecha_resolucion ?? '',
    resultado,
    criterioDecisivo: criterio,
    esCasoResidencia: raw.es_caso_residencia_irpf === 'SI',
  };
}

function main() {
  mkdirSync(targetDir, { recursive: true });

  const source = findLatestJsonl();
  if (!source) {
    if (existsSync(targetFile)) {
      console.warn(
        '[build-corpus] No se encontró ningún analisis_*.jsonl en output/. Se conserva el corpus versionado.'
      );
      return;
    }

    console.warn(
      '[build-corpus] No se encontró ningún analisis_*.jsonl ni corpus versionado. Corpus vacío.'
    );
    writeFileSync(targetFile, '[]\n', 'utf8');
    return;
  }

  const entries = [];
  for (const line of readFileSync(source, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      entries.push(toEntry(JSON.parse(trimmed)));
    } catch {
      console.warn('[build-corpus] Línea JSON inválida omitida.');
    }
  }

  entries.sort((a, b) => b.fecha.localeCompare(a.fecha));
  writeFileSync(targetFile, `${JSON.stringify(entries)}\n`, 'utf8');
  console.log(`[build-corpus] ${entries.length} sentencias escritas en public/data/corpus.json`);
}

main();
