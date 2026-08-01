-- Agregados diarios del ledger del chat para el resumen operativo.
--
-- Invariante de privacidad: la función devuelve exclusivamente recuentos, sumas
-- y percentiles. No expone `content` de `private.chat_messages` ni ningún campo
-- capaz de transportar la pregunta o la respuesta. El día es natural español
-- (`Europe/Madrid`), no UTC, porque el informe lo lee una persona en Madrid.

CREATE OR REPLACE FUNCTION public.chat_daily_stats(p_day date)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
    WITH bounds AS (
        SELECT (p_day::timestamp AT TIME ZONE 'Europe/Madrid') AS day_start,
               ((p_day + 1)::timestamp AT TIME ZONE 'Europe/Madrid') AS day_end
    ),
    requests AS (
        SELECT r.status, r.failure_code, r.actual_microusd, r.actual_complete
          FROM private.chat_requests r, bounds b
         WHERE r.created_at >= b.day_start
           AND r.created_at < b.day_end
    ),
    answers AS (
        SELECT m.strategy, m.cost_measurement, m.latency_ms, m.cost_microusd
          FROM private.chat_messages m
          JOIN private.chat_requests r ON r.request_id = m.request_id
         CROSS JOIN bounds b
         WHERE m.role = 'assistant'
           AND r.created_at >= b.day_start
           AND r.created_at < b.day_end
    )
    SELECT jsonb_build_object(
        'day', p_day,
        'requests', (SELECT count(*) FROM requests),
        'by_status', coalesce(
            (SELECT jsonb_object_agg(status, n)
               FROM (SELECT status, count(*) AS n FROM requests GROUP BY status) s),
            '{}'::jsonb
        ),
        'by_failure_code', coalesce(
            (SELECT jsonb_object_agg(failure_code, n)
               FROM (
                   SELECT failure_code, count(*) AS n
                     FROM requests
                    WHERE failure_code IS NOT NULL
                    GROUP BY failure_code
               ) f),
            '{}'::jsonb
        ),
        'total_microusd', coalesce((SELECT sum(actual_microusd) FROM requests), 0),
        'cost_complete_requests', (
            SELECT count(*) FROM requests WHERE actual_complete IS TRUE
        ),
        'by_measurement', coalesce(
            (SELECT jsonb_object_agg(cost_measurement, n)
               FROM (
                   SELECT cost_measurement, count(*) AS n
                     FROM answers
                    WHERE cost_measurement IS NOT NULL
                    GROUP BY cost_measurement
               ) m),
            '{}'::jsonb
        ),
        'by_strategy', coalesce(
            (SELECT jsonb_object_agg(strategy, detail)
               FROM (
                   SELECT strategy,
                          jsonb_build_object(
                              'answers', count(*),
                              'cost_microusd', coalesce(sum(cost_microusd), 0),
                              'p50_latency_ms', percentile_disc(0.5)
                                  WITHIN GROUP (ORDER BY latency_ms),
                              'p95_latency_ms', percentile_disc(0.95)
                                  WITHIN GROUP (ORDER BY latency_ms)
                          ) AS detail
                     FROM answers
                    WHERE strategy IS NOT NULL
                    GROUP BY strategy
               ) g),
            '{}'::jsonb
        )
    );
$$;

COMMENT ON FUNCTION public.chat_daily_stats(date) IS
    'Agregados diarios del ledger del chat (día natural Europe/Madrid). Nunca devuelve contenido de mensajes.';

REVOKE ALL ON FUNCTION public.chat_daily_stats(date) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.chat_daily_stats(date) TO service_role;
