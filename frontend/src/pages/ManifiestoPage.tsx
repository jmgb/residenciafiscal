import { Link } from 'react-router';
import { JsonLd } from '@/components/seo/JsonLd';
import { breadcrumbJsonLd } from '@/lib/structured-data';
import { usePageTitle } from '@/lib/usePageTitle';
import { Button } from '@/shared/components/ui/button';

const BREADCRUMB = breadcrumbJsonLd([{ name: 'Manifiesto', path: '/manifiesto' }]);

// Versión íntegra canónica: docs/brand/manifiesto.md. Cualquier cambio de texto
// se hace allí primero y se replica aquí en el mismo commit.
const CREDOS: { title: string; paragraphs: string[] }[] = [
  {
    title: 'La residencia fiscal se decide en los tribunales.',
    paragraphs: [
      'El artículo 9 de la LIRPF cabe en una página; los litigios que lo interpretan llenan miles. Cuántos días computan y qué ausencias suman, qué prueba acredita la residencia en otro país, cuánto pesa el patrimonio cuando los días no bastan: nada de eso está resuelto en la ley. Está resuelto en las sentencias.',
    ],
  },
  {
    title: 'El criterio real estaba disperso.',
    paragraphs: [
      'El CENDOJ publica cada resolución, pero el criterio no viene sistematizado: hay que leer las sentencias una a una, clasificar qué se discutió, qué se probó y por qué se ganó o se perdió, y mantener ese archivo al día. Es un trabajo de semanas que no cabe en la preparación de un caso concreto.',
    ],
  },
  {
    title: 'Solo los equipos más grandes podían permitirse ese archivo.',
    paragraphs: [
      'Los despachos que litigan residencia fiscal a escala se saben cada sentencia: qué prueba convence a la Audiencia Nacional, cuál se desmonta en la primera vista, qué criterio decide cuando el cómputo de días no es concluyente. El abogado independiente, el despacho pequeño o el asesor al que le entra un caso de residencia trabajan enfrente de la Administración — que tiene cada expediente y cada precedente — con una fracción de esa información.',
    ],
  },
  {
    title: 'La asimetría no está en el criterio jurídico. Está en la infraestructura.',
    paragraphs: [
      'Cuando una parte tiene la jurisprudencia sistematizada y la otra no, la diferencia no la marca el mejor argumento, sino el mejor archivo. Esa es la asimetría concreta que este proyecto existe para corregir: no entre quien sabe derecho y quien no, sino entre quien tiene la base documental y quien no puede costearla.',
    ],
  },
  {
    title: 'Residencia Fiscal es ese archivo, abierto.',
    paragraphs: [
      '106 resoluciones del Tribunal Supremo y la Audiencia Nacional, leídas una a una y estructuradas por cuestión jurídica, prueba aportada, valoración y resultado. La misma base documental con la que trabajan los equipos más especializados, disponible como herramienta de trabajo para cualquier profesional del derecho tributario.',
    ],
  },
  {
    title: 'La cita no se negocia.',
    paragraphs: [
      'Ninguna afirmación se publica sin su sentencia, su página y su extracto literal, contrastado palabra por palabra con el documento de origen. El análisis lo genera un modelo y se declara como tal; el texto judicial no se reescribe jamás. No hace falta creernos: cada cita lleva el camino de vuelta a la resolución.',
    ],
  },
  {
    title: 'Una herramienta de trabajo, no un sustituto del criterio.',
    paragraphs: [
      'Esta herramienta no asesora, no predice el resultado de un caso ni firma escritos. Localiza los precedentes comparables, muestra qué se probó, cómo se valoró y qué decidió el tribunal, y deja la cita a la vista para verificarla. El criterio profesional — y la responsabilidad — siguen siendo del abogado.',
    ],
  },
  {
    title: 'El mismo punto de partida para todo el que ejerce.',
    paragraphs: [
      'Un asesor con un solo caso de residencia merece empezar donde empiezan los equipos que llevan cientos. Ese es el proyecto: que la calidad del trabajo la decida el criterio del profesional, no el tamaño de su archivo.',
    ],
  },
];

export function ManifiestoPage() {
  usePageTitle('Manifiesto', '/manifiesto');
  return (
    <div className='mx-auto w-full max-w-2xl overflow-y-auto px-4 py-10'>
      <JsonLd data={BREADCRUMB} />
      <div className='mb-10 border-t-4 border-primary pt-6'>
        <h1 className='mb-3 font-heading text-3xl font-semibold'>Manifiesto</h1>
        <p className='text-base leading-relaxed text-muted-foreground'>
          Trabaja cada caso de residencia fiscal con las sentencias en la mano.
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
        La jurisprudencia, por fin, a disposición de quien la trabaja.
      </p>

      <div className='flex flex-wrap items-center gap-4 border-t border-border pt-6'>
        <Button asChild>
          <Link to='/consulta'>Consulta la muestra jurisprudencial</Link>
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
