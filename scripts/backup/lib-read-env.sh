#!/bin/bash
# ============================================================================
# Helper compartido del subsistema de backup: leer claves del .env SIN ejecutarlo.
# ============================================================================
# Un .env NO es un script bash. `source`arlo funciona solo mientras todos los
# valores sean "shell-safe": un valor con espacios sin comillas (p. ej.
# `RESEND_FROM_NAME=Residencia Fiscal`) hace que bash intente ejecutar la 2ª
# palabra como comando -> exit 127 y el job entero falla. Le pasó a Presupuestor
# el 2026-07-01 y tumbó backup + freshness + restore drill el mismo día.
#
# `read_env_var <fichero> <clave>` imprime el valor (sin comillas envolventes) o
# cadena vacía si no existe. Nunca ejecuta contenido del fichero.
# `read_env_var_or_current` da prioridad a la variable ya exportada en el entorno.
# ============================================================================

read_env_var() {
    local file="$1" key="$2" line val
    [[ -f "$file" ]] || return 0
    line=$(grep -E "^[[:space:]]*${key}=" "$file" | tail -n1) || true
    [[ -z "$line" ]] && return 0
    val="${line#*=}"
    # quita comillas envolventes (dotenv/pydantic las eliminan igual)
    if [[ "$val" == \"*\" ]]; then val="${val#\"}"; val="${val%\"}";
    elif [[ "$val" == \'*\' ]]; then val="${val#\'}"; val="${val%\'}"; fi
    printf '%s' "$val"
}

read_env_var_or_current() {
    local file="$1" key="$2" current
    current="${!key-}"
    if [[ -n "$current" ]]; then
        printf '%s' "$current"
        return 0
    fi
    read_env_var "$file" "$key"
}
