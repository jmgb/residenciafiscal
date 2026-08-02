import { useEffect, useState } from 'react';

/**
 * Textos de estado que se muestran mientras no llega el primer contenido.
 * Son orientativos —el protocolo no informa de la fase real— y por eso avanzan
 * por tiempo y se detienen en el último en vez de volver a empezar: reiniciar
 * el ciclo delataría que no describen progreso de verdad.
 */
export const TYPING_STATUS_MESSAGES = [
  'Comprobando sentencias sobre el tema…',
  'Analizando los criterios aplicados por los tribunales…',
  'Seleccionando extractos relevantes…',
  'Redactando la respuesta con sus fuentes…',
] as const;

export const TYPING_STATUS_ROTATION_MS = 5000;

export function TypingIndicator() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((current) => Math.min(current + 1, TYPING_STATUS_MESSAGES.length - 1));
    }, TYPING_STATUS_ROTATION_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className='flex justify-start' role='status' aria-label='Preparando la respuesta'>
      <div className='flex items-center gap-2.5 rounded-xl rounded-tl-none border border-border bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm'>
        <span aria-hidden='true' className='flex items-center gap-1'>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className='h-2 w-2 animate-typing-dot rounded-full bg-primary-500'
              style={{ animationDelay: `${i * 0.16}s` }}
            />
          ))}
        </span>
        <span>{TYPING_STATUS_MESSAGES[step]}</span>
      </div>
    </div>
  );
}
