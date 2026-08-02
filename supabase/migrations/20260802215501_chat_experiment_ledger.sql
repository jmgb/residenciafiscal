-- Ledger reproducible del experimento A/B. La petición conserva la versión y
-- el release; cada respuesta conserva afirmaciones y diagnóstico de retrieval.

ALTER TABLE private.chat_requests
    ADD COLUMN experiment jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD CONSTRAINT chat_requests_experiment_object_check CHECK (
        jsonb_typeof(experiment) = 'object'
    );

ALTER TABLE private.chat_messages
    ADD COLUMN claims jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN diagnostics jsonb,
    ADD CONSTRAINT chat_messages_claims_array_check CHECK (
        jsonb_typeof(claims) = 'array'
    ),
    ADD CONSTRAINT chat_messages_diagnostics_object_check CHECK (
        diagnostics IS NULL OR jsonb_typeof(diagnostics) = 'object'
    );

-- Se conserva temporalmente la firma anterior de cinco argumentos para que el
-- deploy vigente siga aceptando consultas hasta que Netlify publique el código
-- que envía `p_experiment`.
CREATE FUNCTION public.create_chat_request(
    p_request_id text,
    p_conversation_id text,
    p_user_message_id text,
    p_country_path text,
    p_question text,
    p_experiment jsonb
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
        OR p_experiment IS NULL OR jsonb_typeof(p_experiment) <> 'object'
        OR p_experiment->>'experiment_version' IS NULL
        OR length(p_experiment->>'experiment_version') NOT BETWEEN 1 AND 128
        OR p_experiment->>'deployed_commit' IS NULL
        OR length(p_experiment->>'deployed_commit') NOT BETWEEN 1 AND 128
        OR p_experiment->>'comparison_schema_version' IS NULL
        OR p_experiment->>'structured_corpus_version' IS NULL
        OR p_experiment->>'structured_prompt_version' IS NULL
        OR p_experiment->>'file_search_store' IS NULL
        OR p_experiment->>'file_search_prompt_version' IS NULL
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
        country_path,
        experiment
    )
    VALUES (
        p_request_id,
        p_conversation_id,
        p_user_message_id,
        p_country_path,
        p_experiment
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
        reasoning_effort,
        latency_ms,
        cost_microusd,
        cost_measurement,
        pricing_version,
        input_tokens,
        output_tokens,
        retrieved_document_tokens,
        sources,
        limits,
        claims,
        diagnostics
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
        coalesce(answer->'limits', '[]'::jsonb),
        coalesce(answer->'claims', '[]'::jsonb),
        answer->'diagnostics'
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

REVOKE ALL ON FUNCTION public.create_chat_request(text, text, text, text, text, jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_chat_request(text, text, text, text, text, jsonb)
    TO service_role;

REVOKE ALL ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.complete_chat_request(text, bigint, boolean, jsonb)
    TO service_role;

COMMENT ON COLUMN private.chat_requests.experiment IS
    'Versiones del experimento, release, corpus, prompts y store usados en la petición.';
COMMENT ON COLUMN private.chat_messages.claims IS
    'Afirmaciones de la respuesta y sus índices de evidencia; vacío cuando la estrategia no los expone.';
COMMENT ON COLUMN private.chat_messages.diagnostics IS
    'Filtro, documentos recuperados, citas candidatas/verificadas y fallo tipado por estrategia.';
COMMENT ON FUNCTION public.create_chat_request(text, text, text, text, text, jsonb) IS
    'Registra consulta y contexto reproducible del experimento; solo service_role.';
