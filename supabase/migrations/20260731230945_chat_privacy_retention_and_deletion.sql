-- Ciclo de vida del dato conversacional.
--
-- La retención efectiva se decide fuera del esquema y se pasa como cutoff a
-- `purge_expired_chat_data`. No se fija aquí un plazo legal inventado.

ALTER TABLE private.chat_requests
    DROP CONSTRAINT IF EXISTS chat_requests_status_check;

ALTER TABLE private.chat_requests
    ADD COLUMN IF NOT EXISTS failure_code text,
    ADD COLUMN IF NOT EXISTS finished_at timestamptz;

ALTER TABLE private.chat_requests
    ADD CONSTRAINT chat_requests_status_check CHECK (
        status IN ('reserved', 'completed', 'failed', 'timed_out')
    );

ALTER TABLE private.chat_requests
    ADD CONSTRAINT chat_requests_failure_code_check CHECK (
        failure_code IS NULL
        OR failure_code IN ('comparison_error', 'timeout', 'aborted', 'unknown')
    );

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

    IF v_request.actual_microusd IS NOT NULL OR v_request.status <> 'reserved' THEN
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
           finished_at = now(),
           completed_at = now()
     WHERE request_id = p_request_id;

    UPDATE private.chat_conversations
       SET updated_at = now()
     WHERE conversation_id = v_request.conversation_id;

    RETURN true;
END;
$$;

CREATE OR REPLACE FUNCTION public.fail_chat_request(
    p_request_id text,
    p_status text,
    p_failure_code text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_status text := lower(trim(coalesce(p_status, '')));
    v_failure_code text := lower(trim(coalesce(p_failure_code, '')));
BEGIN
    IF v_status NOT IN ('failed', 'timed_out')
        OR v_failure_code NOT IN ('comparison_error', 'timeout', 'aborted', 'unknown')
    THEN
        RAISE EXCEPTION 'invalid chat failure';
    END IF;

    UPDATE private.chat_requests
       SET status = v_status,
           failure_code = v_failure_code,
           finished_at = coalesce(finished_at, now())
     WHERE request_id = p_request_id
       AND status = 'reserved'
       AND actual_microusd IS NULL;

    IF NOT FOUND THEN
        RETURN true;
    END IF;

    -- No se libera la reserva: el proveedor puede haber consumido presupuesto
    -- antes de que el proceso recibiera el error o el timeout.
    RETURN true;
END;
$$;

CREATE OR REPLACE FUNCTION private.delete_chat_conversation(p_conversation_id text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_messages bigint;
    v_requests bigint;
    v_conversations bigint;
BEGIN
    IF p_conversation_id IS NULL
        OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR p_conversation_id !~ '^[A-Za-z0-9_-]+$'
    THEN
        RAISE EXCEPTION 'invalid conversation identifier';
    END IF;

    DELETE FROM private.chat_messages
     WHERE conversation_id = p_conversation_id;
    GET DIAGNOSTICS v_messages = ROW_COUNT;

    DELETE FROM private.chat_requests
     WHERE conversation_id = p_conversation_id;
    GET DIAGNOSTICS v_requests = ROW_COUNT;

    DELETE FROM private.chat_conversations
     WHERE conversation_id = p_conversation_id;
    GET DIAGNOSTICS v_conversations = ROW_COUNT;

    RETURN jsonb_build_object(
        'conversation_id', p_conversation_id,
        'messages_deleted', v_messages,
        'requests_deleted', v_requests,
        'conversations_deleted', v_conversations
    );
END;
$$;

CREATE OR REPLACE FUNCTION private.purge_expired_chat_data(p_cutoff timestamptz)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_messages bigint;
    v_requests bigint;
    v_conversations bigint;
BEGIN
    IF p_cutoff IS NULL OR p_cutoff >= clock_timestamp() THEN
        RAISE EXCEPTION 'invalid chat retention cutoff';
    END IF;

    DELETE FROM private.chat_messages AS messages
    USING private.chat_requests AS requests
     WHERE messages.request_id = requests.request_id
       AND requests.created_at < p_cutoff;
    GET DIAGNOSTICS v_messages = ROW_COUNT;

    DELETE FROM private.chat_requests
     WHERE created_at < p_cutoff;
    GET DIAGNOSTICS v_requests = ROW_COUNT;

    DELETE FROM private.chat_conversations AS conversations
     WHERE conversations.updated_at < p_cutoff
       AND NOT EXISTS (
           SELECT 1
             FROM private.chat_requests AS requests
            WHERE requests.conversation_id = conversations.conversation_id
       );
    GET DIAGNOSTICS v_conversations = ROW_COUNT;

    RETURN jsonb_build_object(
        'cutoff', p_cutoff,
        'messages_deleted', v_messages,
        'requests_deleted', v_requests,
        'conversations_deleted', v_conversations
    );
END;
$$;

REVOKE ALL ON FUNCTION public.fail_chat_request(text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.fail_chat_request(text, text, text)
    TO service_role;

REVOKE ALL ON FUNCTION private.delete_chat_conversation(text)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION private.purge_expired_chat_data(timestamptz)
    FROM PUBLIC, anon, authenticated, service_role;

COMMENT ON COLUMN private.chat_requests.failure_code IS
    'Código técnico sin diagnóstico del proveedor ni contenido de la consulta.';
COMMENT ON FUNCTION private.delete_chat_conversation(text) IS
    'Supresión operativa tras verificar la identidad fuera de la base de datos.';
COMMENT ON FUNCTION private.purge_expired_chat_data(timestamptz) IS
    'Purgado por cutoff decidido por la política de retención aprobada.';
