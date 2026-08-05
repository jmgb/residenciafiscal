import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ChatComparisonAnswers } from '@/components/chat/ChatComparisonAnswers';
import type { ChatStrategyAnswer } from '@/types/chat';

const answer = (
  strategy: ChatStrategyAnswer['strategy'],
  overrides: Partial<ChatStrategyAnswer> = {}
): ChatStrategyAnswer => ({
  strategy,
  status: 'completa',
  content: strategy === 'current_structured' ? 'Contenido de A.' : 'Contenido de B.',
  isStreaming: false,
  sources: [],
  limits: [],
  model: 'test',
  latencyMs: 100,
  cost: {
    currency: 'USD',
    amountUsd: '0.002425',
    costMicrousd: 2_425,
    measurement: 'ACTUAL',
    scope: 'REQUEST_MARGINAL',
    pricingVersion: 'test',
    inputTokens: 10,
    outputTokens: 5,
    retrievedDocumentTokens: 0,
    excludesCorpusPreparation: true,
  },
  ...overrides,
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ChatComparisonAnswers', () => {
  it('mantiene una sola columna e identifica A cuando solo A está activa', () => {
    render(<ChatComparisonAnswers answers={[answer('current_structured')]} />);

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
    expect(screen.getByTestId('comparison-grid')).not.toHaveClass('md:grid-cols-2');
    const response = screen.getByRole('region', { name: 'Respuesta de la opción A' });
    expect(response).toHaveTextContent('Contenido de A.');
    expect(response).toHaveTextContent('Coste: 0.002 USD');
    expect(response).not.toHaveTextContent('Coste de esta respuesta');
    expect(response).not.toHaveTextContent('No incluye la preparación previa del corpus.');
    expect(screen.queryByText(/comparación experimental/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: /valorar comparación/i })).not.toBeInTheDocument();
  });

  it('identifica B cuando solo B está activa', () => {
    render(<ChatComparisonAnswers answers={[answer('gemini_file_search')]} />);

    expect(screen.getByRole('region', { name: 'Respuesta de la opción B' })).toHaveTextContent(
      'Contenido de B.'
    );
  });

  it('ofrece acciones de copia y fuentes en una respuesta live terminada', () => {
    render(
      <ChatComparisonAnswers
        answers={[
          answer('current_structured', {
            sources: [
              {
                strategy: 'current_structured',
                judgmentId: 'STS-107-2018',
                page: 7,
                sourceSha256: 'a'.repeat(64),
                quote: 'Cita literal A.',
                verification: 'EXACT',
              },
            ],
          }),
        ]}
      />
    );

    const response = screen.getByRole('region', { name: 'Respuesta de la opción A' });
    expect(within(response).getByRole('button', { name: 'Copiar respuesta' })).toBeInTheDocument();
    expect(within(response).getByRole('button', { name: 'Descargar fuentes' })).toBeInTheDocument();
    expect(within(response).getByRole('link', { name: 'Ver fuentes' })).toHaveAttribute(
      'href',
      '#chat-sources-current_structured'
    );
  });

  it('muestra dos columnas en escritorio y pestañas ciegas en móvil', async () => {
    const user = userEvent.setup();
    render(
      <ChatComparisonAnswers
        answers={[answer('current_structured'), answer('gemini_file_search')]}
      />
    );

    expect(screen.getByTestId('comparison-grid')).toHaveClass('md:grid-cols-2');
    const tabs = screen.getByRole('tablist', { name: 'Opciones de respuesta' });
    const optionA = within(tabs).getByRole('tab', { name: 'Opción A' });
    const optionB = within(tabs).getByRole('tab', { name: 'Opción B' });
    expect(optionA).toHaveAttribute('aria-selected', 'true');
    expect(optionB).toHaveAttribute('aria-selected', 'false');
    expect(screen.queryByText('Corpus estructurado')).not.toBeInTheDocument();
    expect(screen.queryByText('Gemini File Search')).not.toBeInTheDocument();

    optionA.focus();
    await user.keyboard('{ArrowRight}');
    expect(optionB).toHaveFocus();
    expect(optionB).toHaveAttribute('aria-selected', 'true');

    await user.click(optionB);

    expect(optionA).toHaveAttribute('aria-selected', 'false');
    expect(optionB).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tabpanel', { name: 'Respuesta de la opción A' })).toHaveClass(
      'hidden',
      'md:block'
    );
    expect(screen.getByRole('tabpanel', { name: 'Respuesta de la opción B' })).not.toHaveClass(
      'hidden'
    );
  });

  it('envía un voto ciego con motivo cerrado y confirma el registro', async () => {
    const user = userEvent.setup();
    const fetch = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(null, { status: 204 })
    );
    vi.stubGlobal('fetch', fetch);
    render(
      <ChatComparisonAnswers
        answers={[answer('current_structured'), answer('gemini_file_search')]}
        comparisonId='chat-comparison-1'
      />
    );

    const vote = screen.getByRole('region', { name: 'Valorar comparación' });
    await user.click(within(vote).getByRole('radio', { name: 'Opción A' }));
    await user.selectOptions(within(vote).getByRole('combobox', { name: 'Motivo' }), 'clearer');
    await user.click(within(vote).getByRole('button', { name: 'Enviar valoración' }));

    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith(
      '/api/chat-vote',
      expect.objectContaining({ method: 'POST', headers: { 'content-type': 'application/json' } })
    );
    const request = fetch.mock.calls[0]?.[1];
    expect(JSON.parse(String(request?.body))).toEqual({
      request_id: 'chat-comparison-1',
      verdict: 'a',
      reason: 'clearer',
    });
    expect(await within(vote).findByRole('status')).toHaveTextContent('Valoración registrada');
  });

  it('no permite votar hasta que las dos respuestas han terminado', () => {
    render(
      <ChatComparisonAnswers
        answers={[
          answer('current_structured'),
          answer('gemini_file_search', { isStreaming: true, status: undefined }),
        ]}
        comparisonId='chat-comparison-1'
      />
    );

    expect(screen.queryByRole('region', { name: 'Valorar comparación' })).not.toBeInTheDocument();
  });

  it('incluye C en la valoración cuando la investigación profunda ha terminado', async () => {
    const user = userEvent.setup();
    const fetch = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(null, { status: 204 })
    );
    vi.stubGlobal('fetch', fetch);
    render(
      <ChatComparisonAnswers
        answers={[answer('current_structured'), answer('gemini_file_search')]}
        comparisonId='chat-comparison-1'
        includeDeepResearchVote
      />
    );

    const vote = screen.getByRole('region', { name: 'Valorar comparación' });
    await user.click(within(vote).getByRole('radio', { name: 'Opción C' }));
    await user.selectOptions(
      within(vote).getByRole('combobox', { name: 'Motivo' }),
      'better_grounding'
    );
    await user.click(within(vote).getByRole('button', { name: 'Enviar valoración' }));

    expect(JSON.parse(String(fetch.mock.calls[0]?.[1]?.body))).toMatchObject({
      request_id: 'chat-comparison-1',
      verdict: 'c',
      reason: 'better_grounding',
    });
  });

  it('presenta un coste desconocido como no disponible, nunca como cero', () => {
    render(
      <ChatComparisonAnswers
        answers={[
          answer('current_structured', {
            status: 'error',
            content: '',
            limits: ['Tiempo de respuesta agotado.'],
            model: 'unavailable',
            latencyMs: 52_000,
            cost: {
              currency: 'USD',
              amountUsd: null,
              costMicrousd: null,
              measurement: 'UNAVAILABLE',
              scope: 'REQUEST_MARGINAL',
              pricingVersion: 'unavailable',
              inputTokens: null,
              outputTokens: null,
              retrievedDocumentTokens: null,
              excludesCorpusPreparation: true,
            },
          }),
        ]}
      />
    );

    expect(screen.getByText('Coste: no disponible')).toBeInTheDocument();
    expect(screen.queryByText(/USD 0\.000000/)).not.toBeInTheDocument();
  });
});
