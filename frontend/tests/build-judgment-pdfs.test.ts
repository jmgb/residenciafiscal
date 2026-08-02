import { createHash } from 'node:crypto';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
// @ts-expect-error - script de build en JavaScript, sin tipos
import { buildJudgmentPdfs } from '../scripts/build-judgment-pdfs.mjs';

let sourceDir: string;
let targetDir: string;
let manifestPath: string;

const sha256 = (content: string) => createHash('sha256').update(content).digest('hex');

beforeEach(() => {
  sourceDir = mkdtempSync(join(tmpdir(), 'judgment-pdfs-src-'));
  targetDir = mkdtempSync(join(tmpdir(), 'judgment-pdfs-out-'));
  manifestPath = join(sourceDir, 'manifest.json');
});

afterEach(() => {
  rmSync(sourceDir, { recursive: true, force: true });
  rmSync(targetDir, { recursive: true, force: true });
});

describe('build-judgment-pdfs', () => {
  it('publica cada PDF con una URL estable y elimina ficheros obsoletos', () => {
    const pdf = '%PDF-1.7 sentencia';
    writeFileSync(join(sourceDir, 'STS_3498_2025.pdf'), pdf);
    writeFileSync(join(targetDir, 'obsoleta.pdf'), 'old');
    writeFileSync(
      manifestPath,
      JSON.stringify({
        expected_documents: 1,
        documents: [
          {
            judgment_id: 'sts-3498-2025',
            source_file: 'STS_3498_2025.pdf',
            source_sha256: sha256(pdf),
          },
        ],
      })
    );

    const result = buildJudgmentPdfs({ manifestPath, sourceDir, targetDir });

    expect(result).toEqual({ total: 1, bytes: Buffer.byteLength(pdf) });
    expect(readFileSync(join(targetDir, 'sts-3498-2025.pdf'), 'utf8')).toBe(pdf);
    expect(existsSync(join(targetDir, 'obsoleta.pdf'))).toBe(false);
    expect(JSON.parse(readFileSync(join(targetDir, 'manifest.json'), 'utf8'))).toEqual({
      schemaVersion: 'residenciafiscal-judgment-pdfs/1',
      total: 1,
      documents: [
        {
          judgmentId: 'sts-3498-2025',
          url: '/sentencias/sts-3498-2025.pdf',
        },
      ],
    });
  });

  it('rechaza un PDF cuyos bytes no coinciden con el corpus verificado', () => {
    writeFileSync(join(sourceDir, 'SAN_1210_2023.pdf'), '%PDF-adulterado');
    writeFileSync(
      manifestPath,
      JSON.stringify({
        expected_documents: 1,
        documents: [
          {
            judgment_id: 'san-1210-2023',
            source_file: 'SAN_1210_2023.pdf',
            source_sha256: 'a'.repeat(64),
          },
        ],
      })
    );

    expect(() => buildJudgmentPdfs({ manifestPath, sourceDir, targetDir })).toThrow(
      /hash.*no coincide/i
    );
  });

  it('el corpus productivo materializa las 106 sentencias descargables', () => {
    const repoDir = resolve(process.cwd(), '..');
    const result = buildJudgmentPdfs({
      manifestPath: join(repoDir, 'sentencias', 'jurisprudence_v3_rollout_106.json'),
      sourceDir: repoDir,
      targetDir,
    });

    expect(result.total).toBe(106);
    expect(result.bytes).toBeGreaterThan(20 * 1024 * 1024);
    expect(existsSync(join(targetDir, 'sts-3498-2025.pdf'))).toBe(true);
    expect(existsSync(join(targetDir, 'san-1210-2023.pdf'))).toBe(true);
  });
});
