import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ChatMessageActions } from '@/components/chat/ChatMessageActions';
import type { LegacyChatSource } from '@/types/chat';

const source: LegacyChatSource = {
  archivo: 'STS_107_2018.pdf',
  roj: 'STS 107/2018',
  ecli: 'ECLI:ES:TS:2018:107',
  organo: 'Tribunal Supremo',
  fecha: '2018-01-16',
  resultado: 'GANA_AEAT',
  criterioDecisivo: ['CRIT_183_DIAS'],
  esCasoResidencia: true,
  extracto: 'Extracto literal de prueba.',
};

describe('ChatMessageActions', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('copia el texto de la respuesta y confirma la acción', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });

    render(<ChatMessageActions content='Respuesta para copiar.' sources={[]} />);

    await user.click(screen.getByRole('button', { name: 'Copiar respuesta' }));

    expect(writeText).toHaveBeenCalledWith('Respuesta para copiar.');
    expect(screen.getByRole('button', { name: 'Respuesta copiada' })).toBeInTheDocument();
  });

  it('descarga las fuentes como un archivo de texto y ofrece el ancla de fuentes', async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn().mockReturnValue('blob:fuentes');
    const revokeObjectURL = vi.fn();
    const anchorClick = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });

    render(
      <ChatMessageActions
        content='Respuesta con fuentes.'
        messageId='assistant-1'
        sources={[source]}
      />
    );

    expect(screen.getByRole('link', { name: 'Ver fuentes' })).toHaveAttribute(
      'href',
      '#chat-sources-assistant-1'
    );
    await user.click(screen.getByRole('button', { name: 'Descargar fuentes' }));

    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(anchorClick).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:fuentes');
  });
});
