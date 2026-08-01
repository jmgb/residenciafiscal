import { readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDir, '../..');
const manifestPath = resolve(projectRoot, 'sentencias/jurisprudence_v3_rollout_106.json');
const outputPath = resolve(
  projectRoot,
  'frontend/netlify/functions/chat/verbatim-artifacts.generated.ts'
);
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));

if (manifest.expected_documents !== 106 || manifest.documents?.length !== 106) {
  throw new Error('El manifiesto productivo debe contener exactamente 106 sentencias');
}

const imports = [];
const entries = [];
for (const [index, document] of manifest.documents.entries()) {
  const artifactPath = resolve(
    projectRoot,
    `knowledge/jurisprudencia-v3/verbatim/${document.judgment_id}.pages.json`
  );
  await stat(artifactPath);
  const importPath = relative(dirname(outputPath), artifactPath).replaceAll('\\', '/');
  imports.push(
    `import artifact${index} from '${importPath.startsWith('.') ? importPath : `./${importPath}`}';`
  );
  entries.push(`  '${document.judgment_id}': artifact${index},`);
}

const output = `// biome-ignore-all assist/source/organizeImports: archivo generado en el orden del manifiesto
${imports.join('\n')}

// Generado por scripts/build-chat-verbatim-artifacts.mjs. No editar a mano.
export const productionVerbatimArtifacts = {
${entries.join('\n')}
} as const;
`;

await writeFile(outputPath, output, 'utf8');
console.log(`[build-chat-verbatim-artifacts] ${entries.length} artefactos conectados`);
