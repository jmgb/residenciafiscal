export interface JudgmentDocument {
  judgmentId: string;
  roj: string;
  ecli: string;
  pdfUrl: string;
  downloadName: string;
  officialUrl: string;
}

const JUDGMENT_ID = /^(sts|san)-(\d+)-(\d{4})$/i;
const SOURCE_FILE = /^(STS|SAN)_(\d+)_(\d{4})\.pdf$/i;

export function getJudgmentDocument(judgmentId: string): JudgmentDocument | null {
  const match = JUDGMENT_ID.exec(judgmentId);
  if (!match) return null;

  const [, rawCourt, number, year] = match;
  const court = rawCourt.toLowerCase();
  const sigla = court.toUpperCase();
  const ecliCourt = court === 'sts' ? 'TS' : 'AN';
  const normalizedId = `${court}-${number}-${year}`;
  const ecli = `ECLI:ES:${ecliCourt}:${year}:${number}`;

  return {
    judgmentId: normalizedId,
    roj: `${sigla} ${number}/${year}`,
    ecli,
    pdfUrl: `/sentencias/${normalizedId}.pdf`,
    downloadName: `${sigla}_${number}_${year}.pdf`,
    officialUrl: `https://e-justice.europa.eu/ecli/${ecli}`,
  };
}

export function judgmentIdFromSourceFile(sourceFile: string): string | null {
  const fileName = sourceFile.split(/[\\/]/).at(-1);
  const match = fileName ? SOURCE_FILE.exec(fileName) : null;
  if (!match) return null;

  return `${match[1].toLowerCase()}-${match[2]}-${match[3]}`;
}
