-- Restaura el modelo cerrado de producto: Supabase registra consultas,
-- respuestas, estados y coste observado, pero el coste nunca decide admisión.

CREATE OR REPLACE FUNCTION public.create_chat_request(
    p_request_id text,
    p_conversation_id text,
    p_user_message_id text,
    p_country_path text,
    p_question text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_request_id text;
BEGIN
    IF p_request_id IS NULL OR length(p_request_id) NOT BETWEEN 1 AND 128
        OR p_conversation_id IS NULL OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR p_user_message_id IS NULL OR length(p_user_message_id) NOT BETWEEN 1 AND 128
        OR p_country_path IS NULL OR p_country_path !~ '^/[a-z0-9-]{1,63}$'
        OR p_question IS NULL OR length(trim(p_question)) NOT BETWEEN 1 AND 500
    THEN
        RAISE EXCEPTION 'invalid chat request';
    END IF;

    INSERT INTO private.chat_conversations (conversation_id, country_path)
    VALUES (p_conversation_id, p_country_path)
    ON CONFLICT (conversation_id) DO UPDATE
        SET updated_at = now();

    INSERT INTO private.chat_requests (
        request_id,
        conversation_id,
        user_message_id,
        country_path
    )
    VALUES (
        p_request_id,
        p_conversation_id,
        p_user_message_id,
        p_country_path
    )
    ON CONFLICT (conversation_id, user_message_id) DO NOTHING
    RETURNING request_id INTO v_request_id;

    IF v_request_id IS NULL THEN
        SELECT request_id
          INTO v_request_id
          FROM private.chat_requests
         WHERE conversation_id = p_conversation_id
           AND user_message_id = p_user_message_id;
    END IF;

    IF v_request_id IS NULL THEN
        RAISE EXCEPTION 'chat request could not be recorded';
    END IF;

    INSERT INTO private.chat_messages (
        request_id,
        conversation_id,
        client_message_id,
        role,
        content
    )
    SELECT
        v_request_id,
        p_conversation_id,
        p_user_message_id,
        'user',
        trim(p_question)
     WHERE NOT EXISTS (
         SELECT 1
           FROM private.chat_messages
          WHERE request_id = v_request_id
            AND role = 'user'
     );

    UPDATE private.chat_conversations
       SET updated_at = now()
     WHERE conversation_id = p_conversation_id;

    RETURN jsonb_build_object(
        'request_id', v_request_id,
        'created', v_request_id = p_request_id
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
BEGIN
    IF p_request_id IS NULL
        OR p_actual_microusd IS NULL
        OR p_actual_microusd < 0
        OR p_actual_complete IS NULL
        OR p_answers IS NULL
        OR jsonb_typeof(p_answers) <> 'array'
        OR jsonb_array_length(p_answers) NOT BETWEEN 1 AND 2
    THEN
        RAISE EXCEPTION 'invalid chat completion';
    END IF;

    SELECT *
      INTO v_request
      FROM private.chat_requests
     WHERE request_id = p_request_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'chat request not found';
    END IF;

    IF v_request.actual_microusd IS NOT NULL OR v_request.status <> 'processing' THEN
        RETURN true;
    END IF;

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

    UPDATE private.chat_requests
       SET actual_microusd = p_actual_microusd,
           actual_complete = p_actual_complete,
           status = 'completed',
           finished_at = now(),
           completed_at = now()
     WHERE request_id = p_request_id;

    UPDATE private.chat_conversations
       SET updated_at = now()
     WHERE conversation_id = v_request.conversation_id;

    RETURN true;
END;
$$;

REVOKE ALL ON FUNCTION public.create_chat_request(text, text, text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_chat_request(text, text, text, text, text)
    TO service_role;

REVOKE ALL ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    TO service_role;

DROP INDEX IF EXISTS private.chat_requests_budget_date_idx;

ALTER TABLE private.chat_requests
    DROP CONSTRAINT IF EXISTS chat_requests_budget_fields_check,
    DROP CONSTRAINT IF EXISTS chat_requests_budget_date_fkey,
    DROP COLUMN IF EXISTS budget_date,
    DROP COLUMN IF EXISTS daily_limit_microusd,
    DROP COLUMN IF EXISTS reservation_microusd;

DROP TABLE IF EXISTS private.chat_daily_budgets;
DROP TABLE IF EXISTS private.chat_budget_policy;

COMMENT ON TABLE private.chat_requests IS
    'Registro privado de consultas, coste observado y estado; sin cuotas monetarias.';
COMMENT ON COLUMN private.chat_requests.actual_microusd IS
    'Coste observado para métricas y control operativo; nunca decide admisión.';
COMMENT ON FUNCTION public.create_chat_request(text, text, text, text, text) IS
    'Registra de forma idempotente una consulta y su pregunta; solo service_role.';
COMMENT ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb) IS
    'Persiste respuestas A/B y coste observado sin modificar cuotas.';
