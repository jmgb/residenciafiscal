import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { EDITORIAL_CHAT_ANSWERS } from '@/lib/editorial-chat-answers';

interface VerbatimArtifact {
  document_id: string;
  source_sha256: string;
  pages: Array<{ page_index: number; raw_page_text: string }>;
}

const artifactFor = (judgmentId: string): VerbatimArtifact =>
  JSON.parse(
    readFileSync(
      resolve(process.cwd(), `../knowledge/jurisprudencia-v3/verbatim/${judgmentId}.pages.json`),
      'utf8'
    )
  );

describe('respuestas editoriales de la home', () => {
  it('mantiene cuatro entradas versionadas con identificadores y preguntas únicos', () => {
    expect(EDITORIAL_CHAT_ANSWERS).toHaveLength(4);
    expect(new Set(EDITORIAL_CHAT_ANSWERS.map(({ id }) => id))).toHaveLength(4);
    expect(new Set(EDITORIAL_CHAT_ANSWERS.map(({ question }) => question))).toHaveLength(4);

    for (const answer of EDITORIAL_CHAT_ANSWERS) {
      expect(answer.version).toMatch(/^home-editorial-\d{4}-\d{2}-\d{2}-v\d+$/);
      expect(answer.updatedAt).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(answer.content.length).toBeGreaterThan(500);
      expect(answer.sources.length).toBeGreaterThan(0);
    }
  });

  it('publica solo citas que existen literalmente en la página y PDF declarados', () => {
    for (const answer of EDITORIAL_CHAT_ANSWERS) {
      for (const source of answer.sources) {
        const artifact = artifactFor(source.judgmentId);
        const page = artifact.pages.find(({ page_index }) => page_index === source.page);

        expect(source.verification).toBe('EXACT');
        expect(artifact.document_id).toBe(source.judgmentId);
        expect(artifact.source_sha256).toBe(source.sourceSha256);
        expect(page, `${source.roj} no contiene la página PDF ${source.page}`).toBeDefined();
        expect(page?.raw_page_text).toContain(source.quote);
      }
    }
  });
});
