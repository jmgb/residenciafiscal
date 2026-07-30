import { Link } from 'react-router';
import { usePageTitle } from '@/lib/usePageTitle';
import { useScrollTopOnLoad } from '@/lib/useScrollTopOnLoad';
import { Button } from '@/shared/components/ui/button';

// Versión íntegra canónica: docs/brand/manifiesto.md. Cualquier cambio de texto
// se hace allí primero y se replica aquí en el mismo commit.
const CREDOS: { title: string; paragraphs: string[] }[] = [
  {
    title: 'Naciste en un país. No le perteneces.',
    paragraphs: [
      'Naciste donde naciste por azar, y el azar no es un contrato. Eres libre de vivir donde mejor te traten: donde encajen tus intereses, tu estilo de vida y tu momento vital. Hay etapas para emprender, etapas para criar, etapas para cuidar y etapas para volver. Un mundo más justo es uno en el que cada persona puede elegir su sitio en cada una de ellas — sin pedir perdón por ello.',
    ],
  },
  {
    title: 'Elegir dónde tributas es un derecho, no una sospecha.',
    paragraphs: [
      'La ley lo reconoce. Los convenios entre países lo regulan artículo por artículo. Miles de personas lo ejercen cada año, y los tribunales llevan décadas diciendo exactamente qué hace falta para hacerlo bien. No es un vacío legal ni una ingeniería exótica: es un derecho ordinario, con sus reglas escritas y públicas.',
    ],
  },
  {
    title: 'Pero ese derecho tenía dueño.',
    paragraphs: [
      'Sobre el papel era de todos. En la práctica, solo de quienes podían pagar a los mejores: los grandes despachos que se saben cada sentencia, que conocen qué prueba convence a un tribunal, cuál se desmonta en la primera vista y qué criterio decide el caso cuando los días no bastan. Los millonarios y los políticos siempre han tenido ese conocimiento a su servicio. Enfrente, la Administración lo tiene todo: cada expediente, cada precedente, cada criterio. Y en medio tú, con lo que te hayan contado.',
    ],
  },
  {
    title: 'La asimetría no está en la ley. Está en la información.',
    paragraphs: [
      'Y siempre ha caído del mismo lado. Cuando solo una parte conoce las reglas del juego, la ley deja de ser un marco común y se convierte en la ventaja de los que ya ganaban. Esa es la injusticia concreta contra la que existe este proyecto: no que haya reglas, sino que solo unos pocos supieran leerlas.',
    ],
  },
  {
    title: 'Este movimiento existe para romper esa asimetría.',
    paragraphs: [
      'Residencia Fiscal pone la jurisprudencia real — las sentencias del Tribunal Supremo y la Audiencia Nacional que deciden estos casos, leídas una a una — al alcance de cualquiera. La misma materia prima con la que trabajan los mejores asesores fiscales del país, ahora en tus manos. Y con la cita siempre a la vista, para que no tengas que creernos: puedes ir a la sentencia y comprobarlo.',
    ],
  },
  {
    title: 'Todo legal. Todo a la luz.',
    paragraphs: [
      'Aquí no hay trucos, ni atajos, ni sombras. Las reglas están publicadas y son las mismas para todos; la diferencia es que ahora todos las conocen. Quien elige bien su residencia no tiene nada que esconder — precisamente por eso necesita saber qué se le va a exigir, qué tendrá que probar y cómo se valora esa prueba.',
    ],
  },
  {
    title: 'No te decimos dónde vivir. Te enseñamos cómo lo juzgan los tribunales.',
    paragraphs: [
      'La decisión es tuya y de nadie más. Lo nuestro es que la tomes sabiendo lo mismo que sabe la otra parte: qué dice el Supremo, qué dice la Audiencia Nacional, qué pesó en cada caso y por qué. La libertad se ejerce mejor informado.',
    ],
  },
];

export function ManifiestoPage() {
  usePageTitle('Manifiesto', '/manifiesto');
  const scrollRef = useScrollTopOnLoad<HTMLDivElement>();
  return (
    <div ref={scrollRef} className='mx-auto w-full max-w-2xl overflow-y-auto px-4 py-10'>
      <div className='mb-10 border-t-4 border-primary pt-6'>
        <h1 className='mb-3 font-heading text-3xl font-semibold'>Manifiesto</h1>
        <p className='text-base leading-relaxed text-muted-foreground'>
          Reside donde mejor te traten. Decide con las sentencias en la mano.
        </p>
      </div>

      {CREDOS.map((credo) => (
        <section key={credo.title} className='mb-8'>
          <h2 className='mb-3 font-heading text-xl font-semibold'>{credo.title}</h2>
          {credo.paragraphs.map((paragraph) => (
            <p key={paragraph} className='mb-3 leading-relaxed text-muted-foreground'>
              {paragraph}
            </p>
          ))}
        </section>
      ))}

      <p className='mb-10 font-heading text-2xl font-semibold'>
        La ley, por fin, también a tu favor.
      </p>

      <div className='flex flex-wrap items-center gap-4 border-t border-border pt-6'>
        <Button asChild>
          <Link to='/consulta'>Consulta las 106 sentencias</Link>
        </Button>
        <Link
          to='/metodologia'
          className='text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring'
        >
          Cómo se construyó el corpus
        </Link>
      </div>
    </div>
  );
}
