const MS_POR_DIA = 86_400_000;

function inicioDelDia(fecha: Date): number {
  return new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()).getTime();
}

/**
 * Marca temporal del arranque de la conversación. Se sitúa una sola vez, arriba
 * del hilo, en lugar de repetir la hora en cada burbuja. Un día de la semana
 * suelto solo es legible dentro de la semana en curso; a partir de ahí se
 * escribe la fecha completa para no sugerir un «martes» que fue hace meses.
 */
export function formatConversationStart(isoString: string, now: Date = new Date()): string {
  const fecha = new Date(isoString);
  if (Number.isNaN(fecha.getTime())) {
    return '';
  }

  const hora = fecha.toLocaleTimeString('es-ES', { hour: 'numeric', minute: '2-digit' });
  const dias = Math.round((inicioDelDia(now) - inicioDelDia(fecha)) / MS_POR_DIA);

  if (dias <= 0) {
    return `hoy ${hora}`;
  }
  if (dias === 1) {
    return `ayer ${hora}`;
  }
  if (dias < 7) {
    return `${fecha.toLocaleDateString('es-ES', { weekday: 'long' })} ${hora}`;
  }
  return `${fecha.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })}, ${hora}`;
}

interface ChatDateDividerProps {
  createdAt: string;
}

export function ChatDateDivider({ createdAt }: ChatDateDividerProps) {
  const label = formatConversationStart(createdAt);
  if (!label) {
    return null;
  }

  return (
    <p data-testid='chat-date-divider' className='py-1 text-center text-xs text-muted-foreground'>
      {label}
    </p>
  );
}
