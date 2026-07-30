import { Link } from 'react-router';
import { COUNTRY_ROUTES } from '@/data/countryRoutes';
import { staticRoute } from '@/data/staticRoutes';
import {
  COLLABORATE_PATH,
  CONTACT_EMAIL,
  contributionMailto,
  countryContributionUrl,
  EXPERT_PROFILES,
} from '@/lib/contribution';
import { usePageTitle } from '@/lib/usePageTitle';
import { useScrollTopOnLoad } from '@/lib/useScrollTopOnLoad';

// Título y descripción salen de `staticRoutes.json`, que es también lo que lee
// `scripts/prerender.mjs`: si estuvieran escritos aquí, el visitante y el bot
// podrían acabar leyendo descripciones distintas.
const META = staticRoute(COLLABORATE_PATH);

/** Lo que ya existe y por tanto nadie tiene que volver a construir. */
const YA_EXISTE = [
  'El pipeline de análisis, agnóstico del país.',
  'La verificación de cada cita contra el documento de origen.',
  'El schema de criterios, categorías de prueba y resultado.',
  'La web, el buscador conversacional y su despliegue.',
];

export function ColaborarPage() {
  usePageTitle('Colaborar', COLLABORATE_PATH, META.description);

  const pendientes = COUNTRY_ROUTES.filter((route) => route.corpusStatus === 'pending');
  const scrollRef = useScrollTopOnLoad<HTMLDivElement>();

  return (
    <div ref={scrollRef} className='w-full overflow-y-auto'>
      <div className='mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14'>
        <header className='border-t-4 border-primary pt-6'>
          <p className='mb-3 font-mono text-xs font-semibold uppercase tracking-[0.16em] text-primary'>
            Residencia Fiscal · Colaborar
          </p>
          <h1 className='mb-4 font-heading text-3xl font-semibold tracking-tight sm:text-4xl'>
            Colaborar con el proyecto
          </h1>
          <p className='text-base leading-relaxed text-muted-foreground sm:text-lg'>
            La residencia fiscal se decide en los tribunales de cada país y la pregunta es la misma
            en todos: qué prueba acepta un juez. Lo que cambia es el articulado y quién lo
            interpreta, así que este proyecto{' '}
            <strong>
              se nutre de la contribución de expertos en fiscalidad y tributación internacional
            </strong>{' '}
            que conocen la jurisprudencia de su jurisdicción.
          </p>
          <p className='mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg'>
            España es hoy el único país con corpus —106 sentencias del Tribunal Supremo y la
            Audiencia Nacional, 2015-2025— y no porque el proyecto sea español, sino porque su
            jurisprudencia se delimitó con criterio jurídico-tributario: qué resoluciones importan,
            qué criterios del art. 9 LIRPF se aplican y en qué doce categorías se clasifica la
            prueba son decisiones de derecho tributario, no de un modelo. El pipeline es agnóstico
            del país; el criterio, no.
          </p>
        </header>

        <section
          className='mt-10 rounded-lg border border-border bg-muted p-6'
          aria-labelledby='canales'
        >
          <h2 id='canales' className='mb-3 font-heading text-xl font-semibold'>
            Empieza por aquí
          </h2>
          <p className='mb-5 text-sm leading-relaxed text-secondary-foreground'>
            No hace falta saber programar: lo que falta es criterio jurídico, no código. Tampoco
            hace falta aportarlo todo —señalar cuál es la fuente oficial de tu jurisdicción ya mueve
            el proyecto—, pero sí conocer la materia: esto no lo puede cerrar un aficionado.
          </p>
          <div className='flex flex-col gap-3 sm:flex-row sm:items-center'>
            <a
              href={countryContributionUrl()}
              target='_blank'
              rel='noopener noreferrer'
              className='control-focus control-press inline-flex items-center justify-center rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-600'
            >
              Proponer un país en GitHub
            </a>
            <a
              href={contributionMailto()}
              className='control-focus inline-flex items-center justify-center rounded-md border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-secondary'
            >
              Escribir a {CONTACT_EMAIL}
            </a>
          </div>
        </section>

        <section className='mt-12' aria-labelledby='que-hace-falta'>
          <h2
            id='que-hace-falta'
            className='mb-3 font-heading text-2xl font-semibold tracking-tight'
          >
            Qué necesita un país nuevo
          </h2>
          <p className='mb-5 text-sm leading-relaxed text-muted-foreground'>
            Tres cosas. Rara vez las aporta una sola persona.
          </p>
          <ol
            aria-label='Qué necesita un país nuevo'
            className='grid gap-4 text-sm leading-relaxed text-secondary-foreground'
          >
            <li className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>Una fuente pública oficial</strong> — el buscador de
              jurisprudencia del país y sus condiciones de reutilización. Sin una licencia clara, el
              corpus no se publica. Los documentos deben llevar capa de texto: no hay OCR, así que
              un PDF escaneado hoy no se procesa.
            </li>
            <li className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>El precepto que decide la residencia</strong> — el
              equivalente al art. 9 LIRPF español en la normativa nacional, con su texto oficial, y
              el artículo de desempate de sus convenios de doble imposición.
            </li>
            <li className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>Un especialista que lo valide</strong> — el análisis
              lo redacta un modelo de lenguaje y puede equivocarse. Ningún país se publica sin que
              un profesional del derecho tributario de esa jurisdicción compruebe que el análisis
              dice lo que dice la resolución.
            </li>
          </ol>
        </section>

        <section className='mt-12' aria-labelledby='perfiles'>
          <h2 id='perfiles' className='mb-3 font-heading text-2xl font-semibold tracking-tight'>
            Quién puede colaborar
          </h2>
          <p className='mb-5 text-sm leading-relaxed text-muted-foreground'>
            El cuello de botella no es técnico: es saber qué resolución importa y por qué. Estos son
            los perfiles profesionales que mueven la aguja.
          </p>
          <ul aria-label='Perfiles que pueden colaborar' className='grid gap-4 sm:grid-cols-2'>
            {EXPERT_PROFILES.map((profile) => (
              <li key={profile.title} className='rounded-md border border-border p-4'>
                <h3 className='mb-1.5 font-heading text-sm font-semibold'>{profile.title}</h3>
                <p className='text-sm leading-relaxed text-muted-foreground'>{profile.detail}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className='mt-12' aria-labelledby='ya-existe'>
          <h2 id='ya-existe' className='mb-3 font-heading text-2xl font-semibold tracking-tight'>
            Lo que no hace falta aportar
          </h2>
          <ul className='grid gap-2 text-sm leading-relaxed text-muted-foreground'>
            {YA_EXISTE.map((item) => (
              <li key={item} className='border-l-2 border-border pl-4'>
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className='mt-12' aria-labelledby='invariantes'>
          <h2 id='invariantes' className='mb-3 font-heading text-2xl font-semibold tracking-tight'>
            Reglas que no se negocian
          </h2>
          <p className='mb-5 text-sm leading-relaxed text-muted-foreground'>
            Valen para cualquier corpus, no solo para el español.
          </p>
          <div className='grid gap-4 text-sm leading-relaxed text-secondary-foreground'>
            <p className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>El texto de una resolución no se reescribe.</strong>{' '}
              Ni se corrige, ni se completa, ni se parafrasea. Puede formatearse, pero una cita solo
              se publica desde una subcadena exacta del texto extraído del documento oficial. Toda
              corrección o interpretación vive en metadatos separados.
            </p>
            <p className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>Cada corpus está aislado del resto.</strong> Una
              consulta sobre un país no puede devolver una cita de otro, y hay tests que lo
              comprueban.
            </p>
            <p className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>
                Nada se publica sin la validación de un especialista.
              </strong>{' '}
              El análisis lo genera un modelo de lenguaje; sin un profesional de la materia que lo
              valide, el corpus se queda sin publicar. Es la razón por la que hoy hay un solo país y
              no veinte a medias.
            </p>
          </div>
        </section>

        <section className='mt-12' aria-labelledby='despues'>
          <h2 id='despues' className='mb-3 font-heading text-2xl font-semibold tracking-tight'>
            Qué pasa cuando propones un país
          </h2>
          <p className='mb-4 text-sm leading-relaxed text-muted-foreground'>
            Se responde en la propia issue y lo primero que se acuerda es la fuente y sus
            condiciones de reutilización, antes de mover ningún documento. El criterio para arrancar
            el siguiente país es simple y no es el orden de llegada:{' '}
            <strong>el primero que reúna una fuente reutilizable y un revisor comprometido</strong>.
          </p>
          <p className='text-sm leading-relaxed text-muted-foreground'>
            Este proyecto lo mantiene una persona en su tiempo libre, así que no hay plazos
            prometidos. Una propuesta sin revisor puede quedarse abierta mucho tiempo, y decirlo es
            más honesto que dar una fecha que no se va a cumplir.
          </p>
        </section>

        <section className='mt-12 border-t border-border pt-8' aria-labelledby='pendientes'>
          <h2 id='pendientes' className='mb-3 font-heading text-2xl font-semibold tracking-tight'>
            Países con ruta reservada
          </h2>
          <p className='mb-5 text-sm leading-relaxed text-muted-foreground'>
            Estos {pendientes.length} países ya tienen su página preparada, aunque todavía sin
            corpus. La invitación no se limita a ellos: <strong>cualquier jurisdicción</strong>{' '}
            puede entrar, tenga ruta o no, si cuenta con profesionales que la respalden.
          </p>
          <nav aria-label='Países sin corpus' className='grid gap-2 sm:grid-cols-2 lg:grid-cols-3'>
            {pendientes.map((route) => (
              <Link
                key={route.path}
                to={route.path}
                className='control-focus rounded-md border border-border px-3 py-2.5 text-sm transition-colors hover:bg-secondary'
              >
                {route.name}
              </Link>
            ))}
          </nav>
        </section>
      </div>
    </div>
  );
}
