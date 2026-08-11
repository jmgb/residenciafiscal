-- Reaplica en producción los cambios de `fix(deep-research): close review gaps`.
--
-- Aquel commit editó en sitio dos migraciones ya aplicadas
-- (`20260803120000` y `20260803123000`), así que la base de datos se quedó con
-- la versión anterior de cinco objetos mientras el repositorio declaraba otra.
-- La deriva salió a la luz al desplegar `scripts/privacy/purge-chat-data.sh`,
-- que llama a `private.purge_expired_deep_research_jobs` con tres argumentos
-- contra una función que en producción solo tenía uno.
--
-- Esta migración es idempotente y no toca ningún dato: replica el estado
-- declarado por aquellas dos migraciones para las instalaciones que aplicaron
-- su redacción original.

-- ---------------------------------------------------------------------------
-- 1. La supresión por derechos debe cubrir también C
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.delete_chat_conversation(p_conversation_id text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_deep_research bigint;
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

    PERFORM 1
      FROM private.chat_conversations
     WHERE conversation_id = p_conversation_id
       FOR UPDATE;

    DELETE FROM private.deep_research_jobs
     WHERE conversation_id = p_conversation_id;
    GET DIAGNOSTICS v_deep_research = ROW_COUNT;

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
        'deep_research_deleted', v_deep_research,
        'messages_deleted', v_messages,
        'requests_deleted', v_requests,
        'conversations_deleted', v_conversations
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- 2. Auditoría del purgado: contadores de C
-- ---------------------------------------------------------------------------
ALTER TABLE private.chat_retention_purge_audit
    ADD COLUMN IF NOT EXISTS deep_research_candidates bigint NOT NULL DEFAULT 0
        CHECK (deep_research_candidates >= 0),
    ADD COLUMN IF NOT EXISTS deep_research_deleted bigint NOT NULL DEFAULT 0
        CHECK (deep_research_deleted >= 0);

-- ---------------------------------------------------------------------------
-- 3. Purgado C con cutoff, dry-run y límite de lote
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION private.purge_expired_deep_research_jobs(
    p_cutoff timestamptz,
    p_dry_run boolean DEFAULT true,
    p_batch_limit integer DEFAULT 500
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_candidates bigint := 0;
    v_deleted bigint := 0;
    v_status text;
BEGIN
    IF p_cutoff IS NULL OR p_cutoff >= clock_timestamp() THEN
        RAISE EXCEPTION 'invalid deep research retention cutoff';
    END IF;
    IF p_dry_run IS NULL THEN
        RAISE EXCEPTION 'invalid deep research retention dry-run flag';
    END IF;
    IF p_batch_limit IS NULL OR p_batch_limit NOT BETWEEN 1 AND 100000 THEN
        RAISE EXCEPTION 'invalid deep research retention batch limit';
    END IF;

    SELECT count(*)
      INTO v_candidates
      FROM private.deep_research_jobs
     WHERE created_at < p_cutoff;

    IF v_candidates > p_batch_limit THEN
        v_status := 'batch_overflow';
    ELSIF p_dry_run THEN
        v_status := 'dry_run';
    ELSE
        DELETE FROM private.deep_research_jobs
         WHERE created_at < p_cutoff;
        GET DIAGNOSTICS v_deleted = ROW_COUNT;
        v_status := 'completed';
    END IF;

    INSERT INTO private.chat_retention_purge_audit (
        cutoff,
        dry_run,
        batch_limit,
        status,
        deep_research_candidates,
        deep_research_deleted
    )
    VALUES (
        p_cutoff,
        p_dry_run,
        p_batch_limit,
        v_status,
        v_candidates,
        v_deleted
    );

    RETURN jsonb_build_object(
        'status', v_status,
        'cutoff', p_cutoff,
        'dry_run', p_dry_run,
        'batch_limit', p_batch_limit,
        'deep_research_candidates', v_candidates,
        'deep_research_deleted', v_deleted
    );
END;
$$;

-- La firma antigua de un solo argumento borraba sin dry-run, sin límite de lote
-- y sin auditoría. Convivir con la nueva sería un purgado en la sombra.
DROP FUNCTION IF EXISTS private.purge_expired_deep_research_jobs(timestamptz);

-- ---------------------------------------------------------------------------
-- 4. Alta de job C: la comparación declarada tiene que ser la misma pregunta
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.create_deep_research_job(
    p_job_id text,
    p_conversation_id text,
    p_comparison_id text,
    p_country_path text,
    p_question text,
    p_bundle_id text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_job private.deep_research_jobs%ROWTYPE;
BEGIN
    IF p_job_id IS NULL OR length(p_job_id) NOT BETWEEN 1 AND 128
        OR p_conversation_id IS NULL OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR (p_comparison_id IS NOT NULL AND p_comparison_id !~ '^chat-[A-Za-z0-9_-]{1,123}$')
        OR p_country_path IS NULL OR p_country_path !~ '^/[a-z0-9-]{1,63}$'
        OR p_question IS NULL OR length(trim(p_question)) NOT BETWEEN 1 AND 500
        OR p_bundle_id IS NULL OR length(p_bundle_id) NOT BETWEEN 1 AND 128
        OR (p_comparison_id IS NOT NULL AND NOT EXISTS (
            SELECT 1
              FROM private.chat_requests AS requests
              JOIN private.chat_messages AS messages
                ON messages.request_id = requests.request_id
               AND messages.role = 'user'
             WHERE requests.request_id = p_comparison_id
               AND requests.conversation_id = p_conversation_id
               AND requests.country_path = p_country_path
               AND messages.content = trim(p_question)
        ))
    THEN
        RAISE EXCEPTION 'invalid deep research job';
    END IF;

    INSERT INTO private.deep_research_jobs (
        job_id, conversation_id, comparison_id, country_path, question, bundle_id
    )
    VALUES (
        p_job_id, p_conversation_id, p_comparison_id, p_country_path, trim(p_question), p_bundle_id
    )
    ON CONFLICT (job_id) DO NOTHING;

    SELECT * INTO v_job
      FROM private.deep_research_jobs
     WHERE job_id = p_job_id;

    RETURN jsonb_build_object(
        'job_id', v_job.job_id,
        'conversation_id', v_job.conversation_id,
        'comparison_id', v_job.comparison_id,
        'status', v_job.status,
        'stage', v_job.stage,
        'result', v_job.result,
        'error', v_job.error_message
    );
END;
$$;

-- Compatibilidad blue/green: la Function anterior puede seguir viva durante el
-- drain y llama todavía a la firma sin comparación.
CREATE OR REPLACE FUNCTION public.create_deep_research_job(
    p_job_id text,
    p_conversation_id text,
    p_country_path text,
    p_question text,
    p_bundle_id text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN public.create_deep_research_job(
        p_job_id => p_job_id,
        p_conversation_id => p_conversation_id,
        p_comparison_id => NULL,
        p_country_path => p_country_path,
        p_question => p_question,
        p_bundle_id => p_bundle_id
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- 5. Voto: `c` exige un job C completado sobre esa misma comparación
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.record_chat_vote(
    p_request_id text,
    p_verdict text,
    p_reason text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_inserted integer;
BEGIN
    IF p_request_id IS NULL OR length(p_request_id) NOT BETWEEN 1 AND 128
        OR p_verdict NOT IN ('a', 'b', 'c', 'tie', 'both_bad')
        OR p_reason NOT IN (
            'better_grounding',
            'clearer',
            'more_complete',
            'better_limits',
            'no_preference',
            'both_inadequate'
        )
    THEN
        RAISE EXCEPTION 'invalid chat vote';
    END IF;

    INSERT INTO private.chat_comparison_votes (request_id, verdict, reason)
    SELECT request_id, p_verdict, p_reason
     FROM private.chat_requests
     WHERE request_id = p_request_id
       AND status = 'completed'
       AND (
           p_verdict <> 'c'
           OR EXISTS (
               SELECT 1
                 FROM private.deep_research_jobs AS jobs
                WHERE jobs.comparison_id = p_request_id
                  AND jobs.status = 'completed'
           )
       )
    ON CONFLICT (request_id) DO NOTHING;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    RETURN v_inserted = 1;
END;
$$;

-- ---------------------------------------------------------------------------
-- 6. Permisos de lo recreado
-- ---------------------------------------------------------------------------
REVOKE ALL ON FUNCTION private.delete_chat_conversation(text)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION private.purge_expired_deep_research_jobs(timestamptz, boolean, integer)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.purge_expired_deep_research_jobs(timestamptz, boolean, integer)
    TO service_role;
REVOKE ALL ON FUNCTION public.create_deep_research_job(text, text, text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_deep_research_job(text, text, text, text, text)
    TO service_role;
REVOKE ALL ON FUNCTION public.create_deep_research_job(text, text, text, text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_deep_research_job(text, text, text, text, text, text)
    TO service_role;
REVOKE ALL ON FUNCTION public.record_chat_vote(text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_chat_vote(text, text, text)
    TO service_role;

COMMENT ON FUNCTION private.purge_expired_deep_research_jobs(timestamptz, boolean, integer) IS
    'Purgado C con el cutoff legal común, dry-run, límite de lote y auditoría sin contenido.';
