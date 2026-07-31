import { describe, expect, it, vi } from 'vitest';
import { PostgresBudgetLedger } from '../netlify/functions/chat/budget-ledger';

interface FakeResult {
  rows: Array<Record<string, unknown>>;
  rowCount: number;
}

const result = (rows: Array<Record<string, unknown>> = []): FakeResult => ({
  rows,
  rowCount: rows.length,
});

describe('presupuesto global atómico del chat', () => {
  it('bloquea bajo FOR UPDATE cuando la reserva excede el límite diario', async () => {
    const query = vi
      .fn()
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result([{ allocated_microusd: '950000' }]))
      .mockResolvedValueOnce(result());
    const release = vi.fn();
    const ledger = new PostgresBudgetLedger(
      { connect: async () => ({ query, release }) },
      { dailyLimitMicrousd: 1_000_000, reservationMicrousd: 100_000 }
    );

    const reservation = await ledger.reserve('chat-over-budget');

    expect(reservation).toEqual({ allowed: false, reservationMicrousd: 0 });
    expect(query.mock.calls.map(([sql]) => String(sql))).toEqual(
      expect.arrayContaining([expect.stringContaining('FOR UPDATE')])
    );
    expect(query.mock.calls.at(-1)?.[0]).toContain('COMMIT');
    expect(release).toHaveBeenCalledOnce();
  });

  it('reserva y reconcilia el coste real sin guardar la pregunta ni las citas', async () => {
    const query = vi
      .fn()
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result([{ allocated_microusd: '0' }]))
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(
        result([
          {
            budget_date: '2026-07-31',
            reservation_microusd: '100000',
            actual_microusd: null,
          },
        ])
      )
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result());
    const release = vi.fn();
    const ledger = new PostgresBudgetLedger(
      { connect: async () => ({ query, release }) },
      { dailyLimitMicrousd: 1_000_000, reservationMicrousd: 100_000 }
    );

    expect(await ledger.reserve('chat-ok')).toEqual({
      allowed: true,
      reservationMicrousd: 100_000,
    });
    await ledger.reconcile({
      requestId: 'chat-ok',
      actualMicrousd: 4_200,
      actualComplete: true,
      strategies: [
        {
          strategy: 'current_structured',
          status: 'completa',
          model: 'gpt-5.6-luna',
          latency_ms: 10,
          cost_microusd: 4_200,
          measurement: 'ACTUAL',
          input_tokens: 100,
          output_tokens: 20,
          retrieved_document_tokens: 0,
        },
      ],
    });

    const allParameters = query.mock.calls.flatMap((call) => call.slice(1));
    expect(JSON.stringify(allParameters)).not.toContain('pregunta');
    expect(JSON.stringify(allParameters)).not.toContain('quote');
    expect(query.mock.calls.filter(([sql]) => String(sql).includes('BEGIN'))).toHaveLength(2);
    expect(query.mock.calls.filter(([sql]) => String(sql).includes('COMMIT'))).toHaveLength(2);
    expect(release).toHaveBeenCalledTimes(2);
  });

  it('conserva la reserva como cargo prudente cuando el uso real está incompleto', async () => {
    const query = vi
      .fn()
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(
        result([
          {
            budget_date: '2026-07-31',
            reservation_microusd: '100000',
            actual_microusd: null,
          },
        ])
      )
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result());
    const ledger = new PostgresBudgetLedger(
      { connect: async () => ({ query, release: vi.fn() }) },
      { dailyLimitMicrousd: 1_000_000, reservationMicrousd: 100_000 }
    );

    await ledger.reconcile({
      requestId: 'chat-incomplete',
      actualMicrousd: 4_200,
      actualComplete: false,
      strategies: [],
    });

    const budgetUpdate = query.mock.calls.find(([sql]) =>
      String(sql).includes('UPDATE chat_daily_budgets')
    );
    expect(budgetUpdate?.[1]).toEqual([100_000, 100_000, 1_000_000, '2026-07-31']);
  });

  it('satura el contador diario si el coste real supera la reserva', async () => {
    const query = vi
      .fn()
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(
        result([
          {
            budget_date: '2026-07-31',
            reservation_microusd: '100000',
            actual_microusd: null,
          },
        ])
      )
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result())
      .mockResolvedValueOnce(result());
    const ledger = new PostgresBudgetLedger(
      { connect: async () => ({ query, release: vi.fn() }) },
      { dailyLimitMicrousd: 1_000_000, reservationMicrousd: 100_000 }
    );

    await ledger.reconcile({
      requestId: 'chat-over-reservation',
      actualMicrousd: 250_000,
      actualComplete: true,
      strategies: [],
    });

    const budgetUpdate = query.mock.calls.find(([sql]) =>
      String(sql).includes('UPDATE chat_daily_budgets')
    );
    expect(String(budgetUpdate?.[0])).toContain('LEAST');
    expect(budgetUpdate?.[1]).toEqual([100_000, 250_000, 1_000_000, '2026-07-31']);
  });
});
