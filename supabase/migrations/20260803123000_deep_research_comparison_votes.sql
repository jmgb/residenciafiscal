-- Vincula C con la comparación A/B que la originó y amplía el catálogo de voto.
-- Se mantiene como migración incremental para instalaciones donde C5 ya estaba aplicado.

ALTER TABLE private.deep_research_jobs
    ADD COLUMN comparison_id text REFERENCES private.chat_requests(request_id) ON DELETE SET NULL;

CREATE INDEX deep_research_jobs_comparison_idx
    ON private.deep_research_jobs (comparison_id)
    WHERE comparison_id IS NOT NULL;

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
            SELECT 1 FROM private.chat_requests WHERE request_id = p_comparison_id
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

DROP FUNCTION public.create_deep_research_job(text, text, text, text, text);
REVOKE ALL ON FUNCTION public.create_deep_research_job(text, text, text, text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_deep_research_job(text, text, text, text, text, text)
    TO service_role;

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
        'comparison_id', v_job.comparison_id,
        'status', v_job.status,
        'stage', v_job.stage,
        'result', v_job.result,
        'error', v_job.error_message
    );
END;
$$;

ALTER TABLE private.chat_comparison_votes
    DROP CONSTRAINT chat_comparison_votes_verdict_check;
ALTER TABLE private.chat_comparison_votes
    ADD CONSTRAINT chat_comparison_votes_verdict_check
    CHECK (verdict IN ('a', 'b', 'c', 'tie', 'both_bad'));

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
    ON CONFLICT (request_id) DO NOTHING;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    RETURN v_inserted = 1;
END;
$$;
