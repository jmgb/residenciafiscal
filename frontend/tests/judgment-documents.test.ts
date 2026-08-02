import { describe, expect, it } from 'vitest';
import { getJudgmentDocument, judgmentIdFromSourceFile } from '@/lib/judgment-documents';

describe('documentos descargables de sentencias', () => {
  it('construye las referencias del Tribunal Supremo', () => {
    expect(getJudgmentDocument('STS-3498-2025')).toEqual({
      judgmentId: 'sts-3498-2025',
      roj: 'STS 3498/2025',
      ecli: 'ECLI:ES:TS:2025:3498',
      pdfUrl: '/sentencias/sts-3498-2025.pdf',
      downloadName: 'STS_3498_2025.pdf',
      officialUrl: 'https://e-justice.europa.eu/ecli/ECLI:ES:TS:2025:3498',
    });
  });

  it('construye las referencias de la Audiencia Nacional', () => {
    expect(getJudgmentDocument('san-1210-2023')).toMatchObject({
      roj: 'SAN 1210/2023',
      ecli: 'ECLI:ES:AN:2023:1210',
      pdfUrl: '/sentencias/san-1210-2023.pdf',
      downloadName: 'SAN_1210_2023.pdf',
    });
  });

  it('obtiene el judgmentId de los nombres históricos del corpus', () => {
    expect(judgmentIdFromSourceFile('STS_107_2018.pdf')).toBe('sts-107-2018');
    expect(judgmentIdFromSourceFile('sentencias/SAN_1210_2023.pdf')).toBe('san-1210-2023');
    expect(judgmentIdFromSourceFile('../fuera.pdf')).toBeNull();
  });
});
