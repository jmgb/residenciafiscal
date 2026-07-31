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
          El punto de partida es siempre la sentencia original. Su texto se conserva literal, página
          a página, junto con una huella digital que permite detectar cualquier alteración
          posterior. Lo que escribió el tribunal no se corrige, no se completa y no se parafrasea.
        </p>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Sobre ese texto, un modelo de inteligencia artificial propone el análisis: qué criterios
          de residencia se discutieron, qué pruebas se presentaron, cómo las valoró el tribunal, con
          qué razonamiento y con qué resultado. Cada afirmación queda anclada a una cita textual, y
          una verificación automática comprueba que esa cita existe, palabra por palabra, en la
          sentencia. Lo que no supera esa comprobación no se publica.
        </p>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Las pruebas se clasifican en doce categorías —desde la presencia física y los
          desplazamientos hasta las trazas digitales— y de cada una se registra a qué criterio
          afecta, si el tribunal la admitió o la rechazó y el peso que le dio, siempre con la cita
          literal que lo respalda.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Todo esto ocurre antes de publicar: el análisis se prepara y se verifica con antelación,
          no se improvisa cada vez que alguien consulta la web. Y es una propuesta: requiere
          revisión jurídica humana antes de considerarse aprobado.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Un método, un corpus por país</h2>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El método es el mismo para todos los países. Lo que cambia de una jurisdicción a otra son
          tres cosas: la fuente oficial de la que proceden las sentencias, la norma que decide la
          residencia fiscal y el especialista que valida el análisis. Por eso las fuentes y la
          normativa se documentan en la página de cada país: hoy, el{' '}
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
            El análisis lo genera un modelo y puede contener errores de interpretación. La
            literalidad de las citas se comprueba de forma automática; la valoración jurídica
            requiere un especialista.
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
