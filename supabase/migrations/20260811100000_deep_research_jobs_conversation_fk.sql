-- La supresión de una conversación tiene que llevarse sus jobs C, siempre.
--
-- `private.delete_chat_conversation` bloquea la fila de `chat_conversations`
-- con `FOR UPDATE` antes de borrar, pero `public.create_deep_research_job` no
-- tocaba esa fila y `deep_research_jobs.conversation_id` no tenía clave ajena:
-- solo un `CHECK` de longitud. Nada serializaba ambas transacciones, así que un
-- job insertado a la vez que una supresión por derechos sobrevivía al borrado.
--
-- La clave ajena lo cierra sin añadir bloqueos al camino caliente: el `INSERT`
-- toma un lock sobre la fila padre que conflictúa con ese `FOR UPDATE`, de modo
-- que las dos transacciones se ordenan solas. `chat_requests` y `chat_messages`
-- ya la tienen contra la misma tabla; `deep_research_jobs` era la excepción.
--
-- El flujo real no crea jobs sin conversación: la Function llama antes a
-- `public.authorize_chat_conversation`, que inserta la fila si falta.

-- ---------------------------------------------------------------------------
-- 1. La restricción, primero y sin validar
-- ---------------------------------------------------------------------------
-- `NOT VALID` la impone ya sobre toda escritura nueva sin exigir que las filas
-- viejas cumplan. Limpiar antes y restringir después dejaría una ventana en la
-- que la misma carrera que esto arregla crearía otro huérfano y tumbaría la
-- migración entera.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'private.deep_research_jobs'::regclass
           AND conname = 'deep_research_jobs_conversation_id_fkey'
    ) THEN
        ALTER TABLE private.deep_research_jobs
            ADD CONSTRAINT deep_research_jobs_conversation_id_fkey
            FOREIGN KEY (conversation_id)
            REFERENCES private.chat_conversations(conversation_id)
            ON DELETE CASCADE
            NOT VALID;
    END IF;
END;
$$;

-- ---------------------------------------------------------------------------
-- 2. Huérfanos previos
-- ---------------------------------------------------------------------------
-- Residuo del rollout de C del 3 y 4 de agosto de 2026: los smokes borraron sus
-- conversaciones sintéticas y dejaron atrás los jobs, que es justo el fallo que
-- esta migración impide. Son datos que ya no debían existir.
DELETE FROM private.deep_research_jobs AS jobs
 WHERE NOT EXISTS (
     SELECT 1
       FROM private.chat_conversations AS conversations
      WHERE conversations.conversation_id = jobs.conversation_id
 );

-- ---------------------------------------------------------------------------
-- 3. Validación
-- ---------------------------------------------------------------------------
ALTER TABLE private.deep_research_jobs
    VALIDATE CONSTRAINT deep_research_jobs_conversation_id_fkey;
