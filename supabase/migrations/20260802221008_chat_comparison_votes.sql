-- Voto ciego del experimento A/B. Solo enums cerrados: no se acepta texto
-- libre ni se amplía la superficie de datos fiscales almacenados.

CREATE TABLE private.chat_comparison_votes (
    request_id text PRIMARY KEY REFERENCES private.chat_requests(request_id) ON DELETE CASCADE,
    verdict text NOT NULL CHECK (verdict IN ('a', 'b', 'tie', 'both_bad')),
    reason text NOT NULL CHECK (
        reason IN (
            'better_grounding',
            'clearer',
            'more_complete',
            'better_limits',
            'no_preference',
            'both_inadequate'
        )
    ),
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE private.chat_comparison_votes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE private.chat_comparison_votes FROM PUBLIC, anon, authenticated, service_role;

CREATE FUNCTION public.record_chat_vote(
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
        OR p_verdict NOT IN ('a', 'b', 'tie', 'both_bad')
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

REVOKE ALL ON FUNCTION public.record_chat_vote(text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_chat_vote(text, text, text)
    TO service_role;

COMMENT ON TABLE private.chat_comparison_votes IS
    'Un voto ciego y un motivo cerrado por petición A/B; sin texto libre ni identificadores de persona.';
