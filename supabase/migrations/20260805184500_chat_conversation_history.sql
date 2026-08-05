-- Historial conversacional del chat. La Function lo reconstruye desde el ledger
-- privado por `conversation_id`: el navegador manda solo la pregunta actual y el
-- servidor nunca da por buenas unas respuestas anteriores que el cliente podría
-- alterar. Devuelve exclusivamente pregunta y texto de cada respuesta; ni coste,
-- ni diagnóstico, ni citas, ni identificadores de petición.
--
-- Solo entran peticiones `completed`: una consulta fallida no tiene respuesta y
-- arrastraría preguntas sin contestar. `deep_research` queda fuera porque es otro
-- flujo, con su propio job y su propia superficie.
--
-- La retención de 15 días ya purga estas filas: el historial no conserva nada más
-- de lo que ya estaba guardado, ni durante más tiempo.

CREATE FUNCTION public.read_chat_history(
    p_conversation_id text,
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
         WHERE r.conversation_id = p_conversation_id
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

REVOKE ALL ON FUNCTION public.read_chat_history(text, integer)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.read_chat_history(text, integer)
    TO service_role;

COMMENT ON FUNCTION public.read_chat_history(text, integer) IS
    'Devuelve los últimos turnos completados de una conversación como contexto del chat; solo pregunta y texto de respuesta.';
