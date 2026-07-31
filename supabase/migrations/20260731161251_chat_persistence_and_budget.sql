-- Persistencia backend-only del comparador jurisprudencial A/B.
--
-- Guarda la pregunta aceptada, una respuesta por estrategia y su uso/coste.
-- No guarda IP, user-agent, credenciales ni diagnósticos brutos del proveedor.

CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated;

CREATE TABLE private.chat_conversations (
    conversation_id text PRIMARY KEY,
    country_path text NOT NULL CHECK (country_path ~ '^/[a-z0-9-]{1,63}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (length(conversation_id) BETWEEN 1 AND 128)
);

CREATE TABLE private.chat_daily_budgets (
    budget_date date PRIMARY KEY,
    allocated_microusd bigint NOT NULL DEFAULT 0 CHECK (allocated_microusd >= 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE private.chat_requests (
    request_id text PRIMARY KEY,
    conversation_id text NOT NULL REFERENCES private.chat_conversations(conversation_id),
    user_message_id text NOT NULL,
    country_path text NOT NULL CHECK (country_path ~ '^/[a-z0-9-]{1,63}$'),
    budget_date date NOT NULL REFERENCES private.chat_daily_budgets(budget_date),
    daily_limit_microusd bigint NOT NULL CHECK (daily_limit_microusd > 0),
    reservation_microusd bigint NOT NULL CHECK (reservation_microusd > 0),
    actual_microusd bigint CHECK (actual_microusd >= 0),
    actual_complete boolean,
    status text NOT NULL DEFAULT 'reserved' CHECK (status IN ('reserved', 'completed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CHECK (length(request_id) BETWEEN 1 AND 128),
    CHECK (length(user_message_id) BETWEEN 1 AND 128),
    UNIQUE (conversation_id, user_message_id)
);

CREATE TABLE private.chat_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id text NOT NULL REFERENCES private.chat_requests(request_id) ON DELETE CASCADE,
    conversation_id text NOT NULL REFERENCES private.chat_conversations(conversation_id),
    client_message_id text,
    role text NOT NULL CHECK (role IN ('user', 'assistant')),
    strategy text CHECK (strategy IN ('current_structured', 'gemini_file_search')),
    content text NOT NULL,
    answer_status text CHECK (
        answer_status IN ('completa', 'parcial', 'pregunta', 'abstención', 'error')
    ),
    model text,
    latency_ms integer CHECK (latency_ms >= 0),
    cost_microusd bigint CHECK (cost_microusd >= 0),
    cost_measurement text CHECK (cost_measurement IN ('ACTUAL', 'ESTIMATED', 'UNAVAILABLE')),
    pricing_version text,
    input_tokens integer CHECK (input_tokens >= 0),
    output_tokens integer CHECK (output_tokens >= 0),
    retrieved_document_tokens integer CHECK (retrieved_document_tokens >= 0),
    sources jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(sources) = 'array'),
    limits jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(limits) = 'array'),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (length(content) <= 100000 AND (role = 'assistant' OR length(content) >= 1)),
    CHECK (client_message_id IS NULL OR length(client_message_id) BETWEEN 1 AND 128),
    CHECK (
        (role = 'user'
            AND strategy IS NULL
            AND answer_status IS NULL
            AND model IS NULL
            AND cost_microusd IS NULL
            AND cost_measurement IS NULL)
        OR
        (role = 'assistant'
            AND strategy IS NOT NULL
            AND answer_status IS NOT NULL
            AND model IS NOT NULL
            AND cost_measurement IS NOT NULL)
    )
);

CREATE UNIQUE INDEX chat_messages_one_user_per_request
    ON private.chat_messages (request_id)
    WHERE role = 'user';

CREATE UNIQUE INDEX chat_messages_one_answer_per_strategy
    ON private.chat_messages (request_id, strategy)
    WHERE role = 'assistant';

CREATE INDEX chat_requests_created_at_idx
    ON private.chat_requests (created_at DESC);

CREATE INDEX chat_messages_conversation_created_idx
    ON private.chat_messages (conversation_id, created_at);

ALTER TABLE private.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE private.chat_daily_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE private.chat_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE private.chat_messages ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON ALL TABLES IN SCHEMA private FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA private FROM PUBLIC, anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION public.reserve_chat_request(
    p_request_id text,
    p_conversation_id text,
    p_user_message_id text,
    p_country_path text,
    p_question text,
    p_daily_limit_microusd bigint,
    p_reservation_microusd bigint
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_allocated bigint;
BEGIN
    IF p_request_id IS NULL OR length(p_request_id) NOT BETWEEN 1 AND 128
        OR p_conversation_id IS NULL OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR p_user_message_id IS NULL OR length(p_user_message_id) NOT BETWEEN 1 AND 128
        OR p_country_path IS NULL OR p_country_path !~ '^/[a-z0-9-]{1,63}$'
        OR p_question IS NULL OR length(trim(p_question)) NOT BETWEEN 1 AND 500
        OR p_daily_limit_microusd < 1
        OR p_reservation_microusd < 1
        OR p_reservation_microusd > p_daily_limit_microusd
    THEN
        RAISE EXCEPTION 'invalid chat reservation';
    END IF;

    INSERT INTO private.chat_daily_budgets (budget_date, allocated_microusd)
    VALUES (CURRENT_DATE, 0)
    ON CONFLICT (budget_date) DO NOTHING;

    SELECT allocated_microusd
      INTO v_allocated
      FROM private.chat_daily_budgets
     WHERE budget_date = CURRENT_DATE
       FOR UPDATE;

    IF v_allocated + p_reservation_microusd > p_daily_limit_microusd THEN
        RETURN jsonb_build_object('allowed', false, 'reservation_microusd', 0);
    END IF;

    INSERT INTO private.chat_conversations (conversation_id, country_path)
    VALUES (p_conversation_id, p_country_path)
    ON CONFLICT (conversation_id) DO UPDATE
        SET updated_at = now();

    INSERT INTO private.chat_requests (
        request_id,
        conversation_id,
        user_message_id,
        country_path,
        budget_date,
        daily_limit_microusd,
        reservation_microusd
    )
    VALUES (
        p_request_id,
        p_conversation_id,
        p_user_message_id,
        p_country_path,
        CURRENT_DATE,
        p_daily_limit_microusd,
        p_reservation_microusd
    );

    INSERT INTO private.chat_messages (
        request_id,
        conversation_id,
        client_message_id,
        role,
        content
    )
    VALUES (
        p_request_id,
        p_conversation_id,
        p_user_message_id,
        'user',
        trim(p_question)
    );

    UPDATE private.chat_daily_budgets
       SET allocated_microusd = allocated_microusd + p_reservation_microusd,
           updated_at = now()
     WHERE budget_date = CURRENT_DATE;

    RETURN jsonb_build_object(
        'allowed', true,
        'reservation_microusd', p_reservation_microusd
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_chat_request(
    p_request_id text,
    p_actual_microusd bigint,
    p_actual_complete boolean,
    p_answers jsonb
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_request private.chat_requests%ROWTYPE;
    v_budget_charge bigint;
BEGIN
    IF p_actual_microusd < 0
        OR p_actual_complete IS NULL
        OR p_answers IS NULL
        OR jsonb_typeof(p_answers) <> 'array'
        OR jsonb_array_length(p_answers) NOT BETWEEN 1 AND 2
    THEN
        RAISE EXCEPTION 'invalid chat reconciliation';
    END IF;

    SELECT *
      INTO v_request
      FROM private.chat_requests
     WHERE request_id = p_request_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'chat reservation not found';
    END IF;

    IF v_request.actual_microusd IS NOT NULL THEN
        RETURN true;
    END IF;

    v_budget_charge := CASE
        WHEN p_actual_complete THEN p_actual_microusd
        ELSE greatest(v_request.reservation_microusd, p_actual_microusd)
    END;

    INSERT INTO private.chat_messages (
        request_id,
        conversation_id,
        role,
        strategy,
        content,
        answer_status,
        model,
        latency_ms,
        cost_microusd,
        cost_measurement,
        pricing_version,
        input_tokens,
        output_tokens,
        retrieved_document_tokens,
        sources,
        limits
    )
    SELECT
        p_request_id,
        v_request.conversation_id,
        'assistant',
        answer->>'strategy',
        answer->>'content',
        answer->>'status',
        answer->>'model',
        (answer->>'latency_ms')::integer,
        (answer->>'cost_microusd')::bigint,
        answer->>'cost_measurement',
        answer->>'pricing_version',
        (answer->>'input_tokens')::integer,
        (answer->>'output_tokens')::integer,
        (answer->>'retrieved_document_tokens')::integer,
        coalesce(answer->'sources', '[]'::jsonb),
        coalesce(answer->'limits', '[]'::jsonb)
      FROM jsonb_array_elements(p_answers) AS answer;

    UPDATE private.chat_daily_budgets
       SET allocated_microusd = least(
               v_request.daily_limit_microusd,
               greatest(0, allocated_microusd - v_request.reservation_microusd + v_budget_charge)
           ),
           updated_at = now()
     WHERE budget_date = v_request.budget_date;

    UPDATE private.chat_requests
       SET actual_microusd = p_actual_microusd,
           actual_complete = p_actual_complete,
           status = 'completed',
           completed_at = now()
     WHERE request_id = p_request_id;

    UPDATE private.chat_conversations
       SET updated_at = now()
     WHERE conversation_id = v_request.conversation_id;

    RETURN true;
END;
$$;

REVOKE ALL ON FUNCTION public.reserve_chat_request(text, text, text, text, text, bigint, bigint)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reserve_chat_request(text, text, text, text, text, bigint, bigint)
    TO service_role;

REVOKE ALL ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    TO service_role;

COMMENT ON TABLE private.chat_messages IS
    'Preguntas y respuestas A/B del chat; backend-only, sin IP ni user-agent.';
COMMENT ON COLUMN private.chat_messages.sources IS
    'Citas exactas ya filtradas por el contrato público de cada estrategia.';
