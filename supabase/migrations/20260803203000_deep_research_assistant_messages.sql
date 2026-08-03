-- Persiste cada resultado C visible como mensaje de asistente en el mismo
-- historial privado. El job sigue siendo la fuente de estado del polling; la
-- fila de mensaje ofrece el ledger conversacional único y se crea de forma
-- idempotente dentro de la misma transacción que completa el job.

ALTER TABLE private.chat_messages
    ALTER COLUMN request_id DROP NOT NULL,
    ADD COLUMN deep_research_job_id text
        REFERENCES private.deep_research_jobs(job_id) ON DELETE CASCADE;

ALTER TABLE private.chat_messages
    DROP CONSTRAINT chat_messages_strategy_check,
    ADD CONSTRAINT chat_messages_strategy_check CHECK (
        strategy IN ('current_structured', 'gemini_file_search', 'deep_research')
    ),
    ADD CONSTRAINT chat_messages_origin_check CHECK (
        (
            role = 'assistant'
            AND strategy = 'deep_research'
            AND deep_research_job_id IS NOT NULL
            AND request_id IS NULL
        )
        OR
        (
            strategy IS DISTINCT FROM 'deep_research'
            AND request_id IS NOT NULL
            AND deep_research_job_id IS NULL
        )
    );

CREATE UNIQUE INDEX chat_messages_one_deep_research_result
    ON private.chat_messages (deep_research_job_id)
    WHERE deep_research_job_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.update_deep_research_job(
    p_job_id text,
    p_status text,
    p_stage text,
    p_result jsonb,
    p_error text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_job private.deep_research_jobs%ROWTYPE;
BEGIN
    IF p_status NOT IN ('queued', 'running', 'completed', 'cancelled', 'error')
        OR p_stage NOT IN ('searching', 'reading', 'verifying', 'completed', 'cancelled', 'error')
        OR (p_result IS NOT NULL AND jsonb_typeof(p_result) <> 'object')
        OR (p_status = 'completed' AND p_result IS NULL)
        OR (p_status <> 'completed' AND p_result IS NOT NULL)
    THEN
        RAISE EXCEPTION 'invalid deep research update';
    END IF;

    UPDATE private.deep_research_jobs
       SET status = p_status,
           stage = p_stage,
           result = p_result,
           error_message = left(p_error, 500),
           updated_at = now()
     WHERE job_id = p_job_id
       AND status NOT IN ('completed', 'cancelled', 'error')
    RETURNING * INTO v_job;

    IF NOT FOUND THEN
        SELECT *
          INTO v_job
          FROM private.deep_research_jobs
         WHERE job_id = p_job_id;
    END IF;

    IF v_job.status = 'completed' AND v_job.result IS NOT NULL THEN
        INSERT INTO private.chat_conversations (conversation_id, country_path)
        VALUES (v_job.conversation_id, v_job.country_path)
        ON CONFLICT (conversation_id) DO UPDATE
            SET updated_at = now();

        INSERT INTO private.chat_messages (
            request_id,
            conversation_id,
            client_message_id,
            role,
            strategy,
            content,
            answer_status,
            model,
            reasoning_effort,
            latency_ms,
            cost_microusd,
            cost_measurement,
            sources,
            limits,
            claims,
            deep_research_job_id
        )
        VALUES (
            NULL,
            v_job.conversation_id,
            v_job.job_id,
            'assistant',
            'deep_research',
            v_job.result->>'text',
            v_job.result->>'status',
            v_job.result->>'model',
            v_job.result->>'reasoningEffort',
            (v_job.result->>'latencyMs')::integer,
            (v_job.result->>'costMicrousd')::bigint,
            v_job.result->>'costMeasurement',
            coalesce(v_job.result->'evidence', '[]'::jsonb),
            coalesce(v_job.result->'limits', '[]'::jsonb),
            coalesce(v_job.result->'claims', '[]'::jsonb),
            v_job.job_id
        )
        ON CONFLICT (deep_research_job_id)
            WHERE deep_research_job_id IS NOT NULL
            DO NOTHING;
    END IF;

    RETURN true;
END;
$$;

REVOKE ALL ON FUNCTION public.update_deep_research_job(text, text, text, jsonb, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_deep_research_job(text, text, text, jsonb, text)
    TO service_role;

COMMENT ON COLUMN private.chat_messages.deep_research_job_id IS
    'Job C que originó este mensaje de asistente; nulo para preguntas y respuestas A/B.';
COMMENT ON FUNCTION public.update_deep_research_job(text, text, text, jsonb, text) IS
    'Actualiza C y persiste atómicamente cada resultado completado como mensaje de asistente.';
