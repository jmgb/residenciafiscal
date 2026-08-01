import { Link } from 'react-router';

/**
 * Contenido indexable de la landing de España, servido debajo del chat.
 *
 * `/espana` es la URL de mayor prioridad del sitemap y la única que puede
 * competir por las búsquedas principales, pero su HTML prerenderizado era casi
 * solo la interfaz del chat: apenas mil caracteres de texto. Esta sección le da
 * al buscador el contexto que el visitante ya tiene: qué decide el art. 9
 * LIRPF y qué contiene el corpus.
 *
 * Es JSX estático sin efectos, a propósito: `entry-server` lo renderiza entero
 * en el build y el bot lo lee sin ejecutar JavaScript. El registro respeta los
 * límites del proyecto: el análisis lo genera un modelo y no se afirma
 * revisión humana.
 */
export function SpainLandingContent() {
  return (
    <section aria-labelledby='espana-art9-lirpf' className='shrink-0 border-t border-border'>
      <div className='mx-auto w-full max-w-3xl px-4 py-10'>
        <h2 id='espana-art9-lirpf' className='mb-3 font-heading text-lg font-semibold'>
          La residencia fiscal en España: qué dice el art. 9 LIRPF
        </h2>
        <p className='mb-6 text-sm leading-relaxed text-muted-foreground'>
          Una persona física es residente fiscal en España cuando concurre cualquiera de los
          criterios del artículo 9 de la Ley 35/2006 (LIRPF). Los tribunales resuelven cada año
          litigios sobre cómo se prueba cada uno, y este corpus recoge esas sentencias con su texto
          literal.
        </p>

        <h3 className='mb-2 text-sm font-semibold text-foreground'>
          Permanencia de más de 183 días
        </h3>
        <p className='mb-5 text-sm leading-relaxed text-muted-foreground'>
          Quien permanece más de 183 días del año natural en territorio español es residente fiscal.
          Para el cómputo se suman las ausencias esporádicas, salvo que el contribuyente acredite su
          residencia fiscal en otro país; buena parte de la jurisprudencia del corpus discute
          precisamente qué prueba basta para acreditarla.
        </p>

        <h3 className='mb-2 text-sm font-semibold text-foreground'>
          Núcleo principal de los intereses económicos
        </h3>
        <p className='mb-5 text-sm leading-relaxed text-muted-foreground'>
          También es residente quien tiene en España, de forma directa o indirecta, el núcleo
          principal o la base de sus actividades o intereses económicos. Cuando los días no deciden,
          las sentencias valoran dónde están el patrimonio, las rentas y la gestión de los negocios.
        </p>

        <h3 className='mb-2 text-sm font-semibold text-foreground'>Presunción familiar</h3>
        <p className='mb-5 text-sm leading-relaxed text-muted-foreground'>
          Se presume, salvo prueba en contrario, que el contribuyente reside en España cuando
          residen habitualmente aquí su cónyuge no separado legalmente y sus hijos menores de edad
          que dependan de él.
        </p>

        <h3 className='mb-2 text-sm font-semibold text-foreground'>
          Convenios de doble imposición
        </h3>
        <p className='mb-8 text-sm leading-relaxed text-muted-foreground'>
          Si otro país considera residente a la misma persona, el conflicto lo resuelven las reglas
          de desempate del convenio bilateral —vivienda permanente, centro de intereses vitales,
          donde viva habitualmente y nacionalidad, por ese orden—, herederas del artículo 4 del
          Modelo OCDE. La página de cada país publica el artículo de residencia de su convenio con
          España.
        </p>

        <h2 className='mb-3 font-heading text-lg font-semibold'>Qué contiene este corpus</h2>
        <p className='mb-4 text-sm leading-relaxed text-muted-foreground'>
          106 resoluciones del Tribunal Supremo y la Audiencia Nacional (2015–2025) sobre residencia
          fiscal de personas físicas, conservadas con su texto literal: ninguna cita se publica sin
          haberse contrastado palabra por palabra con la sentencia. El análisis lo genera un modelo
          de IA y su revisión jurídica es del agente, no una aprobación humana; esta herramienta
          sirve para investigación y no constituye asesoramiento jurídico.
        </p>
        <ul className='list-disc space-y-1 pl-5 text-sm leading-relaxed'>
          <li>
            <Link
              to='/espana/fuentes'
              className='rounded text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring'
            >
              Fuentes y normativa del corpus
            </Link>
          </li>
          <li>
            <Link
              to='/metodologia'
              className='rounded text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring'
            >
              Cómo se construye el análisis
            </Link>
          </li>
          <li>
            <a
              href='https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a9'
              target='_blank'
              rel='noopener noreferrer'
              className='rounded text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring'
            >
              Art. 9 LIRPF en el BOE
            </a>
          </li>
        </ul>
      </div>
    </section>
  );
}
