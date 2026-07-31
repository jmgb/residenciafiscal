export interface SqlResult {
  rows: Array<Record<string, unknown>>;
  rowCount?: number | null;
}

export interface SqlClient {
  query(sql: string, values?: unknown[]): Promise<SqlResult>;
  release(): void;
}

export interface SqlPool {
  connect(): Promise<SqlClient>;
}

export interface ReconciliationInput {
  requestId: string;
  actualMicrousd: number;
  actualComplete: boolean;
  strategies: Array<{
    strategy: string;
    status: string;
    model: string;
    latency_ms: number;
    cost_microusd: number | null;
    measurement: string;
    input_tokens: number | null;
    output_tokens: number | null;
    retrieved_document_tokens: number | null;
  }>;
}

export class PostgresBudgetLedger {
  constructor(
    private readonly pool: SqlPool,
    private readonly limits: { dailyLimitMicrousd: number; reservationMicrousd: number }
  ) {
    if (limits.dailyLimitMicrousd < 1 || limits.reservationMicrousd < 1) {
      throw new Error('Los límites del presupuesto deben ser positivos');
    }
  }

  async reserve(requestId: string) {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      await client.query(
        `INSERT INTO chat_daily_budgets (budget_date, allocated_microusd)
         VALUES (CURRENT_DATE, 0)
         ON CONFLICT (budget_date) DO NOTHING`
      );
      const locked = await client.query(
        `SELECT allocated_microusd::text AS allocated_microusd
         FROM chat_daily_budgets
         WHERE budget_date = CURRENT_DATE
         FOR UPDATE`
      );
      const allocated = Number(locked.rows[0]?.allocated_microusd ?? Number.NaN);
      if (!Number.isFinite(allocated)) throw new Error('Estado de presupuesto inválido');
      if (allocated + this.limits.reservationMicrousd > this.limits.dailyLimitMicrousd) {
        await client.query('COMMIT');
        return { allowed: false, reservationMicrousd: 0 };
      }
      await client.query(
        `INSERT INTO chat_request_costs
           (request_id, budget_date, reservation_microusd)
         VALUES ($1, CURRENT_DATE, $2)`,
        [requestId, this.limits.reservationMicrousd]
      );
      await client.query(
        `UPDATE chat_daily_budgets
         SET allocated_microusd = allocated_microusd + $1,
             updated_at = NOW()
         WHERE budget_date = CURRENT_DATE`,
        [this.limits.reservationMicrousd]
      );
      await client.query('COMMIT');
      return { allowed: true, reservationMicrousd: this.limits.reservationMicrousd };
    } catch (error) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw error;
    } finally {
      client.release();
    }
  }

  async reconcile(input: ReconciliationInput): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const locked = await client.query(
        `SELECT budget_date::text AS budget_date,
                reservation_microusd::text AS reservation_microusd,
                actual_microusd::text AS actual_microusd
         FROM chat_request_costs
         WHERE request_id = $1
         FOR UPDATE`,
        [input.requestId]
      );
      const row = locked.rows[0];
      if (!row) throw new Error('Reserva de presupuesto inexistente');
      if (row.actual_microusd !== null && row.actual_microusd !== undefined) {
        await client.query('COMMIT');
        return;
      }
      const reservation = Number(row.reservation_microusd);
      if (!Number.isFinite(reservation)) throw new Error('Reserva de presupuesto inválida');
      const budgetCharge = input.actualComplete
        ? input.actualMicrousd
        : Math.max(reservation, input.actualMicrousd);
      await client.query(
        `UPDATE chat_daily_budgets
         SET allocated_microusd = LEAST($3, GREATEST(0, allocated_microusd - $1 + $2)),
             updated_at = NOW()
         WHERE budget_date = $4::date`,
        [reservation, budgetCharge, this.limits.dailyLimitMicrousd, row.budget_date]
      );
      await client.query(
        `UPDATE chat_request_costs
         SET actual_microusd = $2,
             actual_complete = $3,
             strategy_usage = $4::jsonb,
             completed_at = NOW()
         WHERE request_id = $1`,
        [
          input.requestId,
          input.actualMicrousd,
          input.actualComplete,
          JSON.stringify(input.strategies),
        ]
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw error;
    } finally {
      client.release();
    }
  }
}
