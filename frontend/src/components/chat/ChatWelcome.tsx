import { Scale } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';

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
      <span className='mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground'>
        <Scale className='h-7 w-7' aria-hidden='true' />
      </span>
      <h1 className='mb-2 font-heading text-2xl font-semibold text-foreground'>
        Consulta la jurisprudencia de residencia fiscal
      </h1>
      <p className='mb-8 max-w-xl text-sm leading-relaxed text-muted-foreground'>
        106 sentencias del Tribunal Supremo y la Audiencia Nacional sobre el art. 9 LIRPF,
        analizadas y consultables en lenguaje natural. Cada respuesta cita las resoluciones en las
        que se apoya.
      </p>
      <div className='grid w-full max-w-2xl gap-2 sm:grid-cols-2'>
        {SUGGESTED_PROMPTS.map((prompt) => (
          <Button
            key={prompt}
            type='button'
            variant='outline'
            onClick={() => onSelectPrompt(prompt)}
            className='h-auto whitespace-normal px-3 py-3 text-left text-sm font-normal'
          >
            {prompt}
          </Button>
        ))}
      </div>
    </div>
  );
}
