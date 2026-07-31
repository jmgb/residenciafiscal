CREATE TABLE IF NOT EXISTS chat_daily_budgets (
  budget_date date PRIMARY KEY,
  allocated_microusd bigint NOT NULL DEFAULT 0 CHECK (allocated_microusd >= 0),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_request_costs (
  request_id text PRIMARY KEY,
  budget_date date NOT NULL REFERENCES chat_daily_budgets (budget_date),
  reservation_microusd bigint NOT NULL CHECK (reservation_microusd > 0),
  actual_microusd bigint CHECK (actual_microusd >= 0),
  actual_complete boolean,
  strategy_usage jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS chat_request_costs_budget_date_idx
  ON chat_request_costs (budget_date);

COMMENT ON TABLE chat_request_costs IS
  'Metadatos de coste y latencia. No almacena preguntas, respuestas ni citas del usuario.';
