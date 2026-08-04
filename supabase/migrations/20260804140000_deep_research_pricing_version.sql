-- Conserva la versión del catálogo usada por el runtime en el mensaje asistente.

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
            pricing_version,
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
            v_job.result->>'pricingVersion',
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

UPDATE private.chat_messages AS m
   SET pricing_version = j.result->>'pricingVersion'
  FROM private.deep_research_jobs AS j
 WHERE m.deep_research_job_id = j.job_id
   AND m.pricing_version IS NULL
   AND nullif(j.result->>'pricingVersion', '') IS NOT NULL;

COMMENT ON FUNCTION public.update_deep_research_job(text, text, text, jsonb, text) IS
    'Actualiza C y persiste atómicamente cada resultado completado como mensaje de asistente, incluida la versión de precios.';
