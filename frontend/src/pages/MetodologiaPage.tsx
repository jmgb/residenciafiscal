import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

function prefersReducedMotion(): boolean {
  if (typeof window.matchMedia !== 'function') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function MetodologiaPage() {
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
      <h1 className='mb-6 font-heading text-2xl font-semibold'>Metodología</h1>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Cómo se construyó el análisis</h2>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Cada sentencia se procesa con un modelo de lenguaje que extrae, en formato estructurado,
          los criterios de residencia aplicados (art. 9 LIRPF), las pruebas aportadas por cada parte
          con su valoración judicial, el razonamiento del tribunal y el resultado del fallo.
        </p>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          Las pruebas se clasifican en doce categorías —desde presencia física y desplazamientos
          hasta trazas digitales— y cada una se registra con el criterio que ataca, si fue admitida
          o rechazada, el peso que le dio el tribunal y la cita literal que lo respalda.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Las resoluciones de mayor relevancia doctrinal se procesan con un modelo premium para
          maximizar la precisión de la extracción.
        </p>
      </section>

      <section id='corpus' className='mb-8 scroll-mt-16'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>Corpus analizado</h2>
        <ul className='mb-3 list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground'>
          <li>106 resoluciones judiciales españolas.</li>
          <li>74 del Tribunal Supremo y 32 de la Audiencia Nacional.</li>
          <li>Período 2015-2025.</li>
          <li>Fuente: CENDOJ (Centro de Documentación Judicial).</li>
        </ul>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El corpus cubre litigios sobre residencia fiscal de personas físicas. Las resoluciones que
          el análisis identifica como fuera de alcance quedan marcadas y no se citan como apoyo.
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
            La extracción es automática: puede contener errores de interpretación. Cada respuesta
            cita las sentencias en las que se apoya para que puedan contrastarse en la fuente.
          </li>
          <li>
            El corpus es una selección, no la totalidad de la jurisprudencia sobre la materia.
          </li>
        </ul>
      </section>
    </div>
  );
}
