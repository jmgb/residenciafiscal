import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoDir = resolve(scriptDir, '../..');
const defaultManifestPath = join(repoDir, 'sentencias', 'jurisprudence_v3_rollout_106.json');
const defaultTargetDir = join(repoDir, 'frontend', 'public', 'sentencias');
const JUDGMENT_ID = /^(sts|san)-(\d+)-(\d{4})$/;
const SHA_256 = /^[a-f0-9]{64}$/;

function assertInsideDirectory(filePath, directory) {
  const root = resolve(directory);
  const candidate = resolve(filePath);
  if (candidate !== root && !candidate.startsWith(`${root}${sep}`)) {
    throw new Error(`El PDF queda fuera del directorio permitido: ${filePath}`);
  }
}

export function buildJudgmentPdfs({
  manifestPath = defaultManifestPath,
  sourceDir = repoDir,
  targetDir = defaultTargetDir,
} = {}) {
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const documents = manifest.documents;

  if (!Array.isArray(documents) || manifest.expected_documents !== documents.length) {
    throw new Error('El número de sentencias no coincide con expected_documents');
  }

  const prepared = [];
  const ids = new Set();
  let bytes = 0;

  for (const document of documents) {
    const judgmentId = document.judgment_id;
    const match = typeof judgmentId === 'string' ? JUDGMENT_ID.exec(judgmentId) : null;
    if (!match || ids.has(judgmentId)) {
      throw new Error(`judgment_id inválido o duplicado: ${judgmentId}`);
    }
    ids.add(judgmentId);

    const [, court, number, year] = match;
    const expectedFileName = `${court.toUpperCase()}_${number}_${year}.pdf`;
    if (
      typeof document.source_file !== 'string' ||
      basename(document.source_file) !== expectedFileName
    ) {
      throw new Error(`source_file no corresponde con ${judgmentId}`);
    }
    if (typeof document.source_sha256 !== 'string' || !SHA_256.test(document.source_sha256)) {
      throw new Error(`source_sha256 inválido para ${judgmentId}`);
    }

    const sourcePath = resolve(sourceDir, document.source_file);
    assertInsideDirectory(sourcePath, sourceDir);
    if (!existsSync(sourcePath)) throw new Error(`Falta el PDF de ${judgmentId}: ${sourcePath}`);

    const content = readFileSync(sourcePath);
    const actualHash = createHash('sha256').update(content).digest('hex');
    if (actualHash !== document.source_sha256) {
      throw new Error(`El hash SHA-256 de ${judgmentId} no coincide con el manifiesto`);
    }

    bytes += content.length;
    prepared.push({ content, judgmentId });
  }

  const temporaryDir = `${targetDir}.tmp-${process.pid}`;
  rmSync(temporaryDir, { recursive: true, force: true });
  mkdirSync(temporaryDir, { recursive: true });

  try {
    for (const document of prepared) {
      writeFileSync(join(temporaryDir, `${document.judgmentId}.pdf`), document.content);
    }
    writeFileSync(
      join(temporaryDir, 'manifest.json'),
      `${JSON.stringify(
        {
          schemaVersion: 'residenciafiscal-judgment-pdfs/1',
          total: prepared.length,
          documents: prepared.map(({ judgmentId }) => ({
            judgmentId,
            url: `/sentencias/${judgmentId}.pdf`,
          })),
        },
        null,
        2
      )}\n`
    );

    rmSync(targetDir, { recursive: true, force: true });
    mkdirSync(dirname(targetDir), { recursive: true });
    renameSync(temporaryDir, targetDir);
  } finally {
    rmSync(temporaryDir, { recursive: true, force: true });
  }

  return { total: prepared.length, bytes };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = buildJudgmentPdfs();
  console.log(
    `[judgment-pdfs] ${result.total} sentencias publicadas (${(result.bytes / 1024 / 1024).toFixed(2)} MiB)`
  );
}
