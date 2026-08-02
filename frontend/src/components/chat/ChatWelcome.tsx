import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router';

export const SUGGESTED_PROMPTS = [
  '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
  '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?',
  '¿Qué peso tiene un certificado de residencia fiscal extranjero?',
  '¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?',
];

interface ChatWelcomeProps {
  onSelectPrompt: (prompt: string) => void;
}

export function ChatWelcome({ onSelectPrompt }: ChatWelcomeProps) {
  return (
    <div
      data-testid='chat-welcome'
      className='flex flex-1 flex-col items-center justify-center px-4 py-8 text-center'
    >
      <h1 className='mb-2 font-heading text-2xl font-semibold text-foreground'>
        Decide con las sentencias en la mano
      </h1>
      <p className='mb-3 max-w-xl text-sm leading-relaxed text-muted-foreground'>
        Modelo de IA entrenado con 106 sentencias del Tribunal Supremo y la Audiencia Nacional sobre
        el art. 9 LIRPF.
      </p>
      <p className='mb-8 text-sm'>
        <Link
          to='/manifiesto'
          className='rounded text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring'
        >
          Por qué existe este proyecto: lee el manifiesto
        </Link>
      </p>
      {/* Panel elevado: las sugerencias son una sola superficie blanca sobre el
          lienzo gris, separadas por hairlines en lugar de por huecos. */}
      <div className='w-full max-w-2xl overflow-hidden rounded-xl border border-border bg-card text-left shadow-sm'>
        {SUGGESTED_PROMPTS.map((prompt, index) => (
          <button
            key={prompt}
            type='button'
            onClick={() => onSelectPrompt(prompt)}
            className={`flex w-full items-center gap-3 px-4 py-3.5 text-left text-sm text-foreground transition-colors hover:bg-primary-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring ${
              index > 0 ? 'border-t border-border' : ''
            }`}
          >
            <span className='min-w-0 flex-1 leading-snug'>{prompt}</span>
            <ChevronRight className='h-4 w-4 shrink-0 text-muted-foreground' aria-hidden='true' />
          </button>
        ))}
      </div>
    </div>
  );
}
