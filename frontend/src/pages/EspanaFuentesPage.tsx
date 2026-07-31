import { useEffect } from 'react';
import { Link, useLocation } from 'react-router';
import { NormativaAplicada } from '@/components/normativa/NormativaAplicada';
import { staticRoute } from '@/data/staticRoutes';
import { usePageTitle } from '@/lib/usePageTitle';

const META = staticRoute('/espana/fuentes');

function prefersReducedMotion(): boolean {
  if (typeof window.matchMedia !== 'function') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Fuentes, corpus validado y normativa aplicada de España. Es contenido de
 * país, no de método: cada jurisdicción que se abra tendrá el suyo, mientras
 * que la metodología común vive en `/metodologia`.
 */
export function EspanaFuentesPage() {
  usePageTitle('Corpus de España', META.path, META.description);
  const { hash } = useLocation();

  // React Router navega con la History API y NO provoca el salto nativo al ancla; además
  // el contenido vive dentro de un contenedor de scroll propio, no en el documento, así
  // que `location.hash` por sí solo no mueve nada. `scrollIntoView` sí recorre los
  // ancestros desplazables, sea cual sea cuál de ellos scrollea.
  useEffect(() => {
    const id = hash.startsWith('#') ? decodeURIComponent(hash.slice(1)) : '';
    if (!id) return;
    const target = document.getElementById(id);
    // jsdom no implementa `scrollIntoView`; en el navegador siempre existe.
    if (!target || typeof target.scrollIntoView !== 'function') return;
    target.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    });
  }, [hash]);

  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <h1 className='mb-6 font-heading text-2xl font-semibold'>El corpus de España</h1>

      <p className='mb-8 text-sm leading-relaxed text-muted-foreground'>
        España es el único país publicado. Estas son sus fuentes y su normativa; el método con el
        que se analizan es común a todas las jurisdicciones y se explica en la{' '}
        <Link to='/metodologia' className='text-foreground underline underline-offset-4'>
          metodología
        </Link>
        .
      </p>

      <section id='corpus' className='mb-8 scroll-mt-16'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Fuentes y corpus validado</h2>
        <ul className='mb-3 list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground'>
          <li>106 resoluciones judiciales españolas conservadas como fuentes.</li>
          <li>5 sentencias estructuradas y validadas en el corpus v3 actual.</li>
          <li>74 del Tribunal Supremo y 32 de la Audiencia Nacional.</li>
          <li>Período 2015-2025.</li>
          <li>Fuente: CENDOJ (Centro de Documentación Judicial).</li>
        </ul>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          La ampliación sigue el gate 1 → 5 → 106. Una fuente no se presenta como caso estructurado
          hasta superar la compilación, la verificación literal y la revisión correspondiente.
        </p>
      </section>

      <section id='normativa' className='scroll-mt-16'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Normativa aplicada</h2>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          El corpus incluye el texto de la ley, no solo las sentencias: los preceptos que deciden la
          residencia fiscal —art. 9 LIRPF y su entorno— y el artículo de residencia de los 96
          convenios de doble imposición firmados por España. Se descarga del BOE y se publica
          literal, sin reescribir una palabra.
        </p>
        <p className='mb-4 text-sm leading-relaxed text-muted-foreground'>
          Cada precepto conserva todas sus redacciones con la fecha desde la que rigió, porque una
          sentencia sobre el ejercicio 2010 aplicó la redacción de entonces y no la de hoy. Estos
          son los que citan las sentencias analizadas:
        </p>
        <NormativaAplicada />
      </section>
    </div>
  );
}
