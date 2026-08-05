-- Las respuestas editoriales son texto revisado y versionado del repositorio que
-- el chat muestra sin llamar a ningún modelo. Hasta ahora se resolvían solo en el
-- navegador, así que no existían para el servidor: un seguimiento sobre ellas
-- llegaba sin ningún antecedente y el router se abstenía.
--
-- Se registran con estrategia propia, nunca reutilizando la de A o la de B: el
-- ledger no puede atribuir a un modelo un texto que ese modelo no escribió, y las
-- métricas del experimento A/B deben poder excluirlas filtrando por `strategy`.

ALTER TABLE private.chat_messages
    DROP CONSTRAINT chat_messages_strategy_check,
    ADD CONSTRAINT chat_messages_strategy_check CHECK (
        strategy IN ('current_structured', 'gemini_file_search', 'deep_research', 'editorial')
    );

COMMENT ON COLUMN private.chat_messages.strategy IS
    'Estrategia que produjo la respuesta; `editorial` es contenido revisado del repositorio, sin llamada a modelo.';
