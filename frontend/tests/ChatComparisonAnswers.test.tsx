import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ChatComparisonAnswers } from '@/components/chat/ChatComparisonAnswers';
import type { ChatStrategyAnswer } from '@/types/chat';

describe('ChatComparisonAnswers', () => {
  it('presenta un coste desconocido como no disponible, nunca como cero', () => {
    const answer: ChatStrategyAnswer = {
      strategy: 'current_structured',
      status: 'error',
      content: '',
      isStreaming: false,
      sources: [],
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
    };

    render(<ChatComparisonAnswers answers={[answer]} />);

    expect(screen.getByText('no disponible')).toBeInTheDocument();
    expect(screen.queryByText(/USD 0\.000000/)).not.toBeInTheDocument();
  });
});
