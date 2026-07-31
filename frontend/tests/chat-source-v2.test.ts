import { describe, expect, it } from 'vitest';
import { areChatSourcesV2, isChatSourceV2, isLegacyChatSource } from '@/lib/chat-source';
import type { ChatSourceV2 } from '@/types/chat';

const sourceV2: ChatSourceV2 = {
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
  printedPage: '6',
  extracto: 'La carga de la prueba corresponde a quien hace valer su derecho.',
  fidelity: 'exact',
  sourceSha256: '4d2f5f31cf8824a4fd9df1214c791e8009d16a250990533b64047467d8459d5d',
  reviewStatus: {
    technical: 'VALIDATED',
    legal: 'AGENT_REVIEWED',
  },
};

describe('ChatSource v2', () => {
  it('acepta una fuente ligada a cuestión, anclaje, página y PDF', () => {
    expect(isChatSourceV2(sourceV2)).toBe(true);
  });

  it.each([
    ['sourceId', ''],
    ['issueId', ''],
    ['anchorId', ''],
    ['pageIndex', 0],
    ['fidelity', 'fuzzy'],
    ['sourceSha256', 'abc'],
  ])('rechaza un %s inválido', (field, value) => {
    expect(isChatSourceV2({ ...sourceV2, [field]: value })).toBe(false);
  });

  it('rechaza estados de revisión que no pertenecen al contrato v3', () => {
    expect(
      isChatSourceV2({
        ...sourceV2,
        reviewStatus: { technical: 'VALIDATED', legal: 'APPROVED' },
      })
    ).toBe(false);
  });

  it('reconoce una fuente histórica sin atribuirle trazabilidad inventada', () => {
    expect(
      isLegacyChatSource({
        archivo: 'STS_107_2018.pdf',
        roj: 'STS 107/2018',
        ecli: 'ECLI:ES:TS:2018:107',
        organo: 'Tribunal Supremo',
        fecha: '2018-01-16',
        resultado: 'GANA_AEAT',
        criterioDecisivo: ['CRIT_183_DIAS'],
        esCasoResidencia: true,
        extracto: 'Resumen histórico del motor simulado.',
      })
    ).toBe(true);
  });

  it('exige sourceId únicos dentro de un evento de fuentes', () => {
    expect(areChatSourcesV2([sourceV2, { ...sourceV2 }])).toBe(false);
    expect(
      areChatSourcesV2([
        sourceV2,
        {
          ...sourceV2,
          sourceId: 'san-1210-2023:residencia-fiscal:anchor-conclusion',
          anchorId: 'anchor-conclusion',
        },
      ])
    ).toBe(true);
  });
});
