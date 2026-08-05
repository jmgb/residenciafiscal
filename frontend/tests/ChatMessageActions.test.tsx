import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ChatMessageActions } from '@/components/chat/ChatMessageActions';
import type { ChatSourceV2, LegacyChatSource } from '@/types/chat';

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

const verifiedSource: ChatSourceV2 = {
  ...source,
  sourceId: 'sts-107-2018:residencia:anchor-1',
  issueId: 'residencia',
  issueLabel: 'Cómputo de permanencia',
  anchorId: 'anchor-1',
  pageIndex: 6,
  printedPage: '4',
  fidelity: 'exact',
  sourceSha256: 'a'.repeat(64),
  reviewStatus: { technical: 'VALIDATED', legal: 'AGENT_REVIEWED' },
};

function installExecCommand(result: boolean) {
  const execCommand = vi.fn().mockReturnValue(result);
  Object.defineProperty(document, 'execCommand', {
    configurable: true,
    value: execCommand,
  });
  return execCommand;
}

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener('load', () => resolve(String(reader.result)));
    reader.addEventListener('error', () => reject(reader.error));
    reader.readAsText(blob);
  });
}

describe('ChatMessageActions', () => {
  afterEach(() => {
    Reflect.deleteProperty(document, 'execCommand');
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

  it('usa el fallback si Clipboard API rechaza la copia', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError'));
    const execCommand = installExecCommand(true);
    vi.stubGlobal('navigator', { clipboard: { writeText } });

    render(<ChatMessageActions content='Respuesta para copiar.' sources={[]} />);

    await user.click(screen.getByRole('button', { name: 'Copiar respuesta' }));

    expect(execCommand).toHaveBeenCalledWith('copy');
    expect(screen.getByRole('button', { name: 'Respuesta copiada' })).toBeInTheDocument();
  });

  it('muestra un error accesible si no puede copiar', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError'));
    installExecCommand(false);
    vi.stubGlobal('navigator', { clipboard: { writeText } });

    render(<ChatMessageActions content='Respuesta para copiar.' sources={[]} />);

    await user.click(screen.getByRole('button', { name: 'Copiar respuesta' }));

    expect(await screen.findByRole('status')).toHaveTextContent('No se pudo copiar la respuesta');
  });

  it('descarga las fuentes con un enlace conectado y revoca después el Blob', async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn().mockReturnValue('blob:fuentes');
    const revokeObjectURL = vi.fn();
    let linkWasConnected = false;
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement
    ) {
      linkWasConnected = this.isConnected;
    });
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });

    render(
      <ChatMessageActions
        content='Respuesta con fuentes.'
        sourcesId='chat-sources-assistant-1'
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
    expect(linkWasConnected).toBe(true);
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:fuentes'));
  });

  it('rotula una fuente histórica como resumen no verificado en la descarga', async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn().mockReturnValue('blob:fuentes');
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    render(<ChatMessageActions content='Respuesta.' sources={[source]} />);
    await user.click(screen.getByRole('button', { name: 'Descargar fuentes' }));

    const text = await readBlob(createObjectURL.mock.calls[0]?.[0] as Blob);
    expect(text).toContain('Fuente histórica sin anclaje v2');
    expect(text).toContain('Resumen no verificado');
    expect(text).toContain('no es una cita judicial verificada');
  });

  it('conserva la trazabilidad completa de una fuente v2 en la descarga', async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn().mockReturnValue('blob:fuentes');
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    render(<ChatMessageActions content='Respuesta.' sources={[verifiedSource]} />);
    await user.click(screen.getByRole('button', { name: 'Descargar fuentes' }));

    const text = await readBlob(createObjectURL.mock.calls[0]?.[0] as Blob);
    expect(text).toContain('Cómputo de permanencia');
    expect(text).toContain('Página PDF: 6');
    expect(text).toContain('Página impresa: 4');
    expect(text).toContain('Cita literal exacta');
    expect(text).toContain(`SHA-256: ${verifiedSource.sourceSha256}`);
    expect(text).toContain('Validación técnica · Revisión jurídica por agente');
  });
});
