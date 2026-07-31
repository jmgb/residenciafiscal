import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ChatSources } from '@/components/chat/ChatSources';
import type { ChatSourceV2, LegacyChatSource } from '@/types/chat';

const baseSource: ChatSourceV2 = {
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
  extracto: 'Primer fragmento literal.',
  fidelity: 'exact',
  sourceSha256: '4d2f5f31cf8824a4fd9df1214c791e8009d16a250990533b64047467d8459d5d',
  reviewStatus: {
    technical: 'VALIDATED',
    legal: 'AGENT_REVIEWED',
  },
};

const secondAnchor: ChatSourceV2 = {
  ...baseSource,
  sourceId: 'san-1210-2023:residencia-fiscal:anchor-conclusion',
  anchorId: 'anchor-conclusion',
  pageIndex: 8,
  printedPage: null,
  extracto: 'Segundo fragmento literal.',
  fidelity: 'exact_with_ellipsis',
};

const legacySource: LegacyChatSource = {
  archivo: 'STS_107_2018.pdf',
  roj: 'STS 107/2018',
  ecli: 'ECLI:ES:TS:2018:107',
  organo: 'Tribunal Supremo',
  fecha: '2018-01-16',
  resultado: 'GANA_AEAT',
  criterioDecisivo: ['CRIT_183_DIAS'],
  esCasoResidencia: true,
  extracto: 'Resumen histórico del motor simulado.',
};

describe('ChatSources', () => {
  it('mantiene separados varios anclajes de una misma sentencia', async () => {
    const user = userEvent.setup();
    render(<ChatSources sources={[baseSource, secondAnchor]} />);

    const buttons = screen.getAllByRole('button', { name: /SAN 1210\/2023/ });
    expect(buttons).toHaveLength(2);

    await user.click(buttons[0]);

    expect(screen.getByText('Primer fragmento literal.')).toBeInTheDocument();
    expect(screen.queryByText('Segundo fragmento literal.')).not.toBeInTheDocument();
  });

  it('muestra cuestión, página, fidelidad, revisión y hash al desplegar v2', async () => {
    const user = userEvent.setup();
    render(<ChatSources sources={[baseSource]} />);

    await user.click(screen.getByRole('button', { name: /SAN 1210\/2023/ }));

    expect(screen.getByText('Residencia fiscal en España')).toBeInTheDocument();
    expect(
      screen.getByText('Página PDF 6 · Página impresa 4 · Cita literal exacta')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Validación técnica · Revisión jurídica por agente')
    ).toBeInTheDocument();
    expect(screen.getByText(`PDF SHA-256: ${baseSource.sourceSha256}`)).toBeInTheDocument();
  });

  it('distingue una fuente histórica de una cita judicial verificada', async () => {
    const user = userEvent.setup();
    render(<ChatSources sources={[legacySource]} />);

    await user.click(screen.getByRole('button', { name: /STS 107\/2018/ }));

    expect(screen.getByText('Fuente histórica sin anclaje v2')).toBeInTheDocument();
    expect(screen.getByText('Resumen histórico del motor simulado.')).toBeInTheDocument();
  });
});
