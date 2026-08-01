-- Ajustes derivados de la revisión de advisors y de la carrera de supresión.

CREATE INDEX IF NOT EXISTS chat_requests_budget_date_idx
    ON private.chat_requests (budget_date);

CREATE OR REPLACE FUNCTION private.delete_chat_conversation(p_conversation_id text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, private
AS $$
DECLARE
    v_messages bigint := 0;
    v_requests bigint := 0;
    v_conversations bigint := 0;
BEGIN
    IF p_conversation_id IS NULL
        OR length(p_conversation_id) NOT BETWEEN 1 AND 128
        OR p_conversation_id !~ '^[A-Za-z0-9_-]+$'
    THEN
        RAISE EXCEPTION 'invalid conversation identifier';
    END IF;

    -- Bloquea el agregado antes de borrar sus hijos para serializar el borrado
    -- con una reserva concurrente de la misma conversación.
    PERFORM 1
      FROM private.chat_conversations
     WHERE conversation_id = p_conversation_id
       FOR UPDATE;

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
