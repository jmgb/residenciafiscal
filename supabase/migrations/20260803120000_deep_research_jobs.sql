-- C5: jobs asíncronos de investigación profunda, separados del ledger A/B.
-- La tabla y sus RPC son backend-only; el navegador solo ve un job opaco ligado
-- a la conversación que lo creó.

CREATE SCHEMA IF NOT EXISTS private;

CREATE TABLE private.deep_research_jobs (
    job_id text PRIMARY KEY,
    conversation_id text NOT NULL,
    country_path text NOT NULL CHECK (country_path ~ '^/[a-z0-9-]{1,63}$'),
    question text NOT NULL CHECK (length(question) BETWEEN 1 AND 500),
    bundle_id text NOT NULL CHECK (length(bundle_id) BETWEEN 1 AND 128),
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'cancelled', 'error')),
    stage text NOT NULL DEFAULT 'searching'
        CHECK (stage IN ('searching', 'reading', 'verifying', 'completed', 'cancelled', 'error')),
    result jsonb CHECK (result IS NULL OR jsonb_typeof(result) = 'object'),
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '15 days'),
    CHECK (length(job_id) BETWEEN 1 AND 128),
    CHECK (length(conversation_id) BETWEEN 1 AND 128)
);

CREATE INDEX deep_research_jobs_expires_at_idx
    ON private.deep_research_jobs (expires_at);
CREATE INDEX deep_research_jobs_conversation_idx
    ON private.deep_research_jobs (conversation_id, created_at DESC);

ALTER TABLE private.deep_research_jobs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE private.deep_research_jobs FROM PUBLIC, anon, authenticated, service_role;

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
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_job private.deep_research_jobs%ROWTYPE;
BEGIN
    IF p_job_id IS NULL OR length(p_job_id) NOT BETWEEN 1 AND 128
        OR p_conversation_id IS NULL OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR p_country_path IS NULL OR p_country_path !~ '^/[a-z0-9-]{1,63}$'
        OR p_question IS NULL OR length(trim(p_question)) NOT BETWEEN 1 AND 500
        OR p_bundle_id IS NULL OR length(p_bundle_id) NOT BETWEEN 1 AND 128
    THEN
        RAISE EXCEPTION 'invalid deep research job';
    END IF;

    INSERT INTO private.deep_research_jobs (
        job_id, conversation_id, country_path, question, bundle_id
    )
    VALUES (
        p_job_id, p_conversation_id, p_country_path, trim(p_question), p_bundle_id
    )
    ON CONFLICT (job_id) DO NOTHING;

    SELECT * INTO v_job
      FROM private.deep_research_jobs
     WHERE job_id = p_job_id;

    RETURN jsonb_build_object(
        'job_id', v_job.job_id,
        'conversation_id', v_job.conversation_id,
        'status', v_job.status,
        'stage', v_job.stage,
        'result', v_job.result,
        'error', v_job.error_message
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.get_deep_research_job(
    p_job_id text,
    p_conversation_id text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_job private.deep_research_jobs%ROWTYPE;
BEGIN
    SELECT * INTO v_job
      FROM private.deep_research_jobs
     WHERE job_id = p_job_id
       AND conversation_id = p_conversation_id
       AND expires_at > now();
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    RETURN jsonb_build_object(
        'job_id', v_job.job_id,
        'conversation_id', v_job.conversation_id,
        'status', v_job.status,
        'stage', v_job.stage,
        'result', v_job.result,
        'error', v_job.error_message
    );
END;
$$;

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
BEGIN
    IF p_status NOT IN ('queued', 'running', 'completed', 'cancelled', 'error')
        OR p_stage NOT IN ('searching', 'reading', 'verifying', 'completed', 'cancelled', 'error')
        OR (p_result IS NOT NULL AND jsonb_typeof(p_result) <> 'object')
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
       AND status NOT IN ('completed', 'cancelled', 'error');

    RETURN true;
END;
$$;

CREATE OR REPLACE FUNCTION public.cancel_deep_research_job(
    p_job_id text,
    p_conversation_id text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
BEGIN
    UPDATE private.deep_research_jobs
       SET status = 'cancelled',
           stage = 'cancelled',
           error_message = NULL,
           updated_at = now()
     WHERE job_id = p_job_id
       AND conversation_id = p_conversation_id
       AND status IN ('queued', 'running');
    RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION private.purge_expired_deep_research_jobs(p_cutoff timestamptz)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_deleted integer;
BEGIN
    IF p_cutoff IS NULL THEN
        RAISE EXCEPTION 'invalid deep research retention cutoff';
    END IF;
    DELETE FROM private.deep_research_jobs
     WHERE expires_at < p_cutoff;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$;

REVOKE ALL ON FUNCTION public.create_deep_research_job(text, text, text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_deep_research_job(text, text, text, text, text)
    TO service_role;
REVOKE ALL ON FUNCTION public.get_deep_research_job(text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_deep_research_job(text, text)
    TO service_role;
REVOKE ALL ON FUNCTION public.update_deep_research_job(text, text, text, jsonb, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_deep_research_job(text, text, text, jsonb, text)
    TO service_role;
REVOKE ALL ON FUNCTION public.cancel_deep_research_job(text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.cancel_deep_research_job(text, text)
    TO service_role;
REVOKE ALL ON FUNCTION private.purge_expired_deep_research_jobs(timestamptz)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.purge_expired_deep_research_jobs(timestamptz)
    TO service_role;

COMMENT ON TABLE private.deep_research_jobs IS
    'Jobs C asíncronos; backend-only, con retención máxima de 15 días y resultado estructurado sin cadena de pensamiento.';
