-- Hardening forward-only del historial ya desplegado: el UUID aparece en la URL
-- local y no puede actuar como autorización. Los clientes nuevos demuestran
-- posesión mediante un secreto de 256 bits; Supabase conserva solo su SHA-256.

ALTER TABLE private.chat_conversations
    ADD COLUMN IF NOT EXISTS conversation_access_hash text;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'chat_conversations_access_hash_check'
           AND conrelid = 'private.chat_conversations'::regclass
    ) THEN
        ALTER TABLE private.chat_conversations
            ADD CONSTRAINT chat_conversations_access_hash_check CHECK (
                conversation_access_hash IS NULL
                OR conversation_access_hash ~ '^[0-9a-f]{64}$'
            );
    END IF;
END;
$$;

-- Una conversación anterior, sin hash, no puede reclamarse después: el cliente
-- abre para ella un ledger_id nuevo al migrar su estado local.
CREATE OR REPLACE FUNCTION public.authorize_chat_conversation(
    p_conversation_id text,
    p_country_path text,
    p_conversation_access_hash text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    IF p_conversation_id IS NULL
        OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR p_country_path IS NULL
        OR p_country_path !~ '^/[a-z0-9-]{1,63}$'
        OR p_conversation_access_hash IS NULL
        OR p_conversation_access_hash !~ '^[0-9a-f]{64}$'
    THEN
        RAISE EXCEPTION 'invalid chat conversation authorization';
    END IF;

    INSERT INTO private.chat_conversations (
        conversation_id,
        country_path,
        conversation_access_hash
    )
    VALUES (
        p_conversation_id,
        p_country_path,
        p_conversation_access_hash
    )
    ON CONFLICT (conversation_id) DO NOTHING;

    PERFORM 1
      FROM private.chat_conversations c
     WHERE c.conversation_id = p_conversation_id
       AND c.country_path = p_country_path
       AND c.conversation_access_hash = p_conversation_access_hash
     FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'chat conversation ownership mismatch';
    END IF;

    UPDATE private.chat_conversations
       SET updated_at = now()
     WHERE conversation_id = p_conversation_id;
    RETURN true;
END;
$$;

-- La firma anterior solo comprobaba el UUID. Se retira expresamente para que
-- ningún consumidor con service_role pueda seguir usándola por accidente.
DROP FUNCTION IF EXISTS public.read_chat_history(text, integer);

CREATE OR REPLACE FUNCTION public.read_chat_history(
    p_conversation_id text,
    p_conversation_access_hash text,
    p_turn_limit integer
)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_history jsonb;
BEGIN
    IF p_conversation_id IS NULL
        OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR p_conversation_access_hash IS NULL
        OR p_conversation_access_hash !~ '^[0-9a-f]{64}$'
        OR p_turn_limit IS NULL
        OR p_turn_limit NOT BETWEEN 1 AND 20
    THEN
        RAISE EXCEPTION 'invalid chat history request';
    END IF;

    WITH turns AS (
        SELECT r.request_id,
               r.created_at,
               (
                   SELECT m.content
                     FROM private.chat_messages m
                    WHERE m.request_id = r.request_id
                      AND m.role = 'user'
                    ORDER BY m.created_at
                    LIMIT 1
               ) AS question,
               coalesce(
                   (
                       SELECT jsonb_agg(
                                  jsonb_build_object('strategy', m.strategy, 'content', m.content)
                                  ORDER BY m.strategy
                              )
                         FROM private.chat_messages m
                        WHERE m.request_id = r.request_id
                          AND m.role = 'assistant'
                          AND m.strategy <> 'deep_research'
                   ),
                   '[]'::jsonb
               ) AS answers
         FROM private.chat_requests r
         JOIN private.chat_conversations c
           ON c.conversation_id = r.conversation_id
         WHERE r.conversation_id = p_conversation_id
           AND c.conversation_access_hash = p_conversation_access_hash
           AND r.status = 'completed'
         ORDER BY r.created_at DESC
         LIMIT p_turn_limit
    )
    SELECT coalesce(
               jsonb_agg(
                   jsonb_build_object('question', question, 'answers', answers)
                   ORDER BY created_at
               ),
               '[]'::jsonb
           )
      INTO v_history
      FROM turns
     WHERE question IS NOT NULL;

    RETURN v_history;
END;
$$;

REVOKE ALL ON FUNCTION public.authorize_chat_conversation(text, text, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.authorize_chat_conversation(text, text, text)
    TO service_role;

REVOKE ALL ON FUNCTION public.read_chat_history(text, text, integer)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.read_chat_history(text, text, integer)
    TO service_role;

COMMENT ON COLUMN private.chat_conversations.conversation_access_hash IS
    'SHA-256 del secreto anónimo de posesión; el secreto en claro solo existe en el navegador.';
COMMENT ON FUNCTION public.authorize_chat_conversation(text, text, text) IS
    'Crea un hilo protegido o verifica su secreto antes de registrar otro turno.';
COMMENT ON FUNCTION public.read_chat_history(text, text, integer) IS
    'Devuelve los últimos turnos completados solo cuando coincide el hash de posesión.';
