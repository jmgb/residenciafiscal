# Informe semanal de tráfico

Cada lunes a las 09:10 (Europe/Madrid) un `systemd` timer de **sistema** del VPS
`alfredo` manda a Telegram las visitas, los usuarios únicos y los recurrentes de
`residenciafiscal.org`, igual que hacen Presupuestor, Doctor y Comunicador con su
propio timer. Lo ejecuta `scripts/weekly_ga4_telegram.py` a través de
`scripts/agentic/`, sobre el checkout `~/residenciafiscal` del VPS. Desde el
2026-11-05 la autoactualización está desactivada: **hacer push no actualiza el
runner**. Publicar solo un commit revisado mediante el procedimiento manual de
[`WEEKLY_TRAFFIC_REPORT.md`](../docs/operations/WEEKLY_TRAFFIC_REPORT.md#actualizar-el-código-del-informe).

Publica **una línea por analítica** —GA4 y PostHog— y no las promedia: en la
primera semana GA4 vio 81 usuarios y PostHog 1, porque GA4 registra bots que
ejecutan JavaScript y PostHog apenas los ve. Presentarlas juntas es lo que hace
visible ese sesgo; no se debe sustituir por una cifra única. El histórico se
escribe en `reports/`, que está en `.gitignore` porque el repositorio es público.
Métricas, trampas de la API y por qué divergen:
[`docs/operations/WEEKLY_TRAFFIC_REPORT.md`](../docs/operations/WEEKLY_TRAFFIC_REPORT.md).
