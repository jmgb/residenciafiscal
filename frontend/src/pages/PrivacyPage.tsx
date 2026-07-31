import { staticRoute } from '@/data/staticRoutes';
import { CONTACT_EMAIL } from '@/lib/contribution';
import { usePageTitle } from '@/lib/usePageTitle';

const META = staticRoute('/privacidad');

export function PrivacyPage() {
  usePageTitle('Privacidad', META.path, META.description, META.indexable);
  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <h1 className='mb-6 font-heading text-2xl font-semibold'>Privacidad del chat</h1>
      <p className='mb-6 text-sm leading-relaxed text-muted-foreground'>
        No incluyas nombres, NIF, direcciones, expedientes ni otros datos que permitan identificar a
        una persona. El chat está diseñado para preguntas jurídicas abstractas y casos anonimizados.
      </p>

      <section className='mb-7'>
        <h2 className='mb-2 font-heading text-lg font-semibold'>Qué se envía</h2>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          En cada consulta se transmite únicamente la última pregunta. La estrategia A la envía a
          OpenAI junto con fragmentos estructurados de cinco sentencias; la estrategia B la envía a
          Google Gemini, que busca de forma independiente en el File Search Store de esos cinco PDF.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          No se reenvía el historial completo. Ambos proveedores reciben la consulta en paralelo y
          aplican sus propias condiciones de tratamiento y conservación contratadas para sus API.
        </p>
      </section>

      <section className='mb-7'>
        <h2 className='mb-2 font-heading text-lg font-semibold'>Qué conserva la aplicación</h2>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Para evaluar y mejorar el buscador, el servidor guarda en Supabase la pregunta y las dos
          respuestas comparadas. También conserva modelo, tokens, coste, duración y citas utilizadas
          por cada estrategia, vinculados a identificadores aleatorios de consulta y conversación.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El historial visible se conserva además en tu navegador mediante localStorage. Eliminarlo
          desde la interfaz o borrar los datos del sitio solo retira esa copia local; para solicitar
          la eliminación de un registro del servidor, contacta indicando el identificador de la
          conversación que aparece en su URL.
        </p>
      </section>

      <section>
        <h2 className='mb-2 font-heading text-lg font-semibold'>Contacto</h2>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Para consultas de privacidad, escribe a{' '}
          <a className='underline hover:text-foreground' href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </section>
    </div>
  );
}
