-- Retira la sobrecarga de compatibilidad de `create_deep_research_job`.
--
-- Se creó el 3 de agosto de 2026 para el drain blue/green: la Function anterior
-- podía seguir viva unos minutos llamando a la firma sin comparación. Ese drain
-- terminó hace ocho días y la Function vigente envía siempre `p_comparison_id`,
-- así que PostgREST resuelve a la firma de seis y esta no la alcanza nadie.
--
-- No aporta seguridad conservarla: se limita a delegar con la comparación a
-- nulo, que la firma de seis ya admite. Lo que sí aporta retirarla es una
-- superficie menos que declarar, vigilar y explicar.

DROP FUNCTION IF EXISTS public.create_deep_research_job(text, text, text, text, text);
