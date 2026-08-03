import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { JudgmentDocumentActions } from '@/components/chat/JudgmentDocumentActions';
import { trackEvent } from '@/components/layout/PostHogAnalytics';

vi.mock('@/components/layout/PostHogAnalytics', () => ({
  trackEvent: vi.fn(),
}));

const expectedProperties = {
  judgment_id: 'sts-3498-2025',
  roj: 'STS 3498/2025',
  ecli: 'ECLI:ES:TS:2025:3498',
};

describe('JudgmentDocumentActions', () => {
  beforeEach(() => {
    vi.mocked(trackEvent).mockClear();
  });

  it.each([
    ['Abrir sentencia STS 3498/2025', 'sentencia_pdf_abierta'],
    ['Descargar PDF STS 3498/2025', 'sentencia_pdf_descargada'],
    ['Fuente oficial STS 3498/2025', 'sentencia_fuente_oficial_abierta'],
  ])('registra %s en PostHog', (accessibleName, eventName) => {
    render(<JudgmentDocumentActions judgmentId='STS-3498-2025' ecli='ECLI:ES:TS:2025:3498' />);

    const link = screen.getByRole('link', { name: accessibleName });
    link.addEventListener('click', (event) => event.preventDefault());
    fireEvent.click(link);

    expect(trackEvent).toHaveBeenCalledOnce();
    expect(trackEvent).toHaveBeenCalledWith(eventName, expectedProperties);
  });
});
