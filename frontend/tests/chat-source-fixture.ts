import type { ChatSourceV2 } from '@/types/chat';

export function makeChatSourceV2(overrides: Partial<ChatSourceV2> = {}): ChatSourceV2 {
  return {
    archivo: 'SAN_1210_2023.pdf',
    roj: 'SAN 1210/2023',
    ecli: 'ECLI:ES:AN:2023:1210',
    organo: 'Audiencia Nacional. Sala de lo Contencioso-Administrativo',
    fecha: '2023-02-22',
    resultado: 'GANA_AEAT',
    criterioDecisivo: ['CRIT_183_DIAS'],
    esCasoResidencia: true,
    sourceId: 'san-1210-2023:residencia-fiscal:anchor-carga-prueba',
    issueId: 'residencia-fiscal',
    issueLabel: 'Residencia fiscal en España',
    anchorId: 'anchor-carga-prueba',
    pageIndex: 6,
    printedPage: '4',
    extracto: 'La sentencia valora las pruebas aportadas por las partes.',
    fidelity: 'exact',
    sourceSha256: '4d2f5f31cf8824a4fd9df1214c791e8009d16a250990533b64047467d8459d5d',
    reviewStatus: {
      technical: 'VALIDATED',
      legal: 'AGENT_REVIEWED',
    },
    ...overrides,
  };
}
