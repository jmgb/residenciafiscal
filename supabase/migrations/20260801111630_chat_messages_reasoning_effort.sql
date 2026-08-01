-- Registra por respuesta el reasoning effort enviado explícitamente al proveedor.
-- Las preguntas, respuestas deterministas y proveedores sin configuración
-- equivalente conservan NULL; también quedan compatibles las filas históricas.

ALTER TABLE private.chat_messages
    ADD COLUMN reasoning_effort text,
    ADD CONSTRAINT chat_messages_reasoning_effort_check CHECK (
        reasoning_effort IS NULL
        OR (
            role = 'assistant'
            AND length(reasoning_effort) BETWEEN 1 AND 32
            AND reasoning_effort ~ '^[a-z][a-z0-9_-]*$'
        )
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
        reasoning_effort,
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
        answer->>'reasoning_effort',
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

REVOKE ALL ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    TO service_role;

COMMENT ON COLUMN private.chat_messages.reasoning_effort IS
    'Esfuerzo de razonamiento enviado explícitamente al proveedor; NULL si no se configuró.';
COMMENT ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb) IS
    'Persiste respuestas A/B, reasoning effort y coste observado sin modificar cuotas.';
