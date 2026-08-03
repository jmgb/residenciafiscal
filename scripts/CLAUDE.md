# Informe semanal de tráfico

Cada lunes a las 09:00 (Europe/Madrid) un `systemd --user` timer manda a Telegram
las visitas, los usuarios únicos y los recurrentes de `residenciafiscal.org`,
igual que hacen Presupuestor, Doctor y Comunicador con su propio timer. Lo
ejecuta `scripts/weekly_ga4_telegram.py` a través de `scripts/agentic/`.

Publica **una línea por analítica** —GA4 y PostHog— y no las promedia: en la
primera semana GA4 vio 81 usuarios y PostHog 1, porque GA4 registra bots que
ejecutan JavaScript y PostHog apenas los ve. Presentarlas juntas es lo que hace
visible ese sesgo; no se debe sustituir por una cifra única. El histórico se
escribe en `reports/`, que está en `.gitignore` porque el repositorio es público.
Métricas, trampas de la API y por qué divergen:
[`docs/operations/WEEKLY_TRAFFIC_REPORT.md`](../docs/operations/WEEKLY_TRAFFIC_REPORT.md).
