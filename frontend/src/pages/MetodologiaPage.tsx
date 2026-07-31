import { Link } from 'react-router';
import { staticRoute } from '@/data/staticRoutes';
import { usePageTitle } from '@/lib/usePageTitle';

const META = staticRoute('/metodologia');

/**
 * El método es agnóstico de la jurisdicción y se explica una sola vez. Las
 * fuentes, el corpus y la normativa de cada país viven en su propia página
 * (hoy, `/espana/fuentes`).
 */
export function MetodologiaPage() {
  usePageTitle('Metodología', META.path, META.description);

  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <h1 className='mb-6 font-heading text-2xl font-semibold'>Metodología</h1>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Cómo se construye el análisis</h2>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Python extrae el texto íntegro por páginas y calcula sus hashes. Después, un agente
          propone en formato estructurado los criterios de residencia, las pruebas, su valoración
          judicial, el razonamiento del tribunal y el resultado; Python valida cada referencia
          contra la fuente.
        </p>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Las pruebas se clasifican en doce categorías —desde presencia física y desplazamientos
          hasta trazas digitales— y cada una se registra con el criterio que ataca, si fue admitida
          o rechazada, el peso que le dio el tribunal y la cita literal que lo respalda.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El repositorio no envía las sentencias a una API de modelos. Las propuestas del agente son
          análisis derivados y requieren revisión jurídica humana antes de considerarse aprobadas.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Un método, un corpus por país</h2>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El pipeline es agnóstico de la jurisdicción: lo que cambia de un país a otro son la fuente
          oficial, el precepto que decide la residencia y el especialista que valida el análisis.
          Por eso las fuentes y la normativa se documentan en la página de cada país: hoy, el{' '}
          <Link to='/espana/fuentes' className='text-foreground underline underline-offset-4'>
            corpus de España
          </Link>
          , el único publicado.
        </p>
      </section>

      <section>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Limitaciones</h2>
        <ul className='list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground'>
          <li>
            El contenido tiene finalidad informativa y de investigación. No constituye asesoramiento
            jurídico ni sustituye el criterio de un profesional.
          </li>
          <li>
            La propuesta jurídica del agente puede contener errores de interpretación. Python
            verifica texto y referencias, pero la aprobación jurídica requiere un especialista.
          </li>
          <li>
            El corpus de cada país es una selección, no la totalidad de la jurisprudencia sobre la
            materia.
          </li>
        </ul>
      </section>
    </div>
  );
}
