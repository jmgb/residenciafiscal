import { Link } from 'react-router';
import { JurisdictionLegalReferences } from '@/components/jurisdiction/JurisdictionLegalReferences';
import type { LegalReference } from '@/data/countryRoutes';
import { Button } from '@/shared/components/ui/button';

export const SUGGESTED_PROMPTS = [
  '¿Qué pruebas acepta el Tribunal Supremo para desvirtuar los 183 días?',
  '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?',
  '¿Qué peso tiene un certificado de residencia fiscal extranjero?',
  '¿Cuándo entra el tie-breaker del art. 4 del Modelo OCDE?',
];

interface ChatWelcomeProps {
  onSelectPrompt: (prompt: string) => void;
  legalReferences: LegalReference[];
}

export function ChatWelcome({ onSelectPrompt, legalReferences }: ChatWelcomeProps) {
  return (
    <div
      data-testid='chat-welcome'
      className='flex flex-1 flex-col items-center justify-center px-4 py-8 text-center'
    >
      <img src='/favicon.svg' alt='' className='mb-4 h-14 w-14' />
      <h1 className='mb-2 font-heading text-2xl font-semibold text-foreground'>
        Consulta la jurisprudencia de residencia fiscal
      </h1>
      <p className='mb-3 max-w-xl text-sm leading-relaxed text-muted-foreground'>
        La colección conserva 106 sentencias del Tribunal Supremo y la Audiencia Nacional sobre el
        art. 9 LIRPF. La consulta usa por ahora una muestra estructurada y validada de cinco; cada
        respuesta indica las resoluciones en las que se apoya.
      </p>
      {legalReferences.length > 0 && <JurisdictionLegalReferences references={legalReferences} />}
      <p className='mb-8 text-sm'>
        <Link
          to='/manifiesto'
          className='rounded text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring'
        >
          Por qué existe este proyecto: lee el manifiesto
        </Link>
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
