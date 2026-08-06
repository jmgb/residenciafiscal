import { staticRoute } from '@/data/staticRoutes';
import { CONTACT_EMAIL } from '@/lib/contribution';
import { usePageTitle } from '@/lib/usePageTitle';
import { useConversations } from '@/stores/useConversations';

const META = staticRoute('/privacidad');

/** Fecha de la última revisión editorial del texto, no la del build. */
const LAST_UPDATED = '6 de agosto de 2026';

/**
 * Responsable del tratamiento. Es la misma entidad titular del resto de
 * proyectos, y se declara aquí porque `/privacidad` es también la página que
 * cumple el deber de identificación del art. 10 LSSI-CE.
 */
const CONTROLLER = {
  name: 'Intangible Land LLC',
  ein: '92-2584862',
  address: 'Brickell Dr #1111, Miami, FL (33131), Estados Unidos',
  site: 'residenciafiscal.org',
};

/**
 * Encargados y destinatarios reales del tratamiento. Cada fila corresponde a un
 * proveedor que interviene hoy en el sistema; si se retira uno, se retira su
 * fila. No se listan proveedores «previstos».
 */
const RECIPIENTS: { name: string; role: string; location: string }[] = [
  {
    name: 'Netlify',
    role: 'Alojamiento del sitio y ejecución del endpoint del chat',
    location: 'Estados Unidos',
  },
  {
    name: 'Cloudflare',
    role: 'DNS, CDN, cortafuegos y bucket privado de copias de seguridad',
    location: 'Red global',
  },
  {
    name: 'Supabase',
    role: 'Base de datos que conserva la pregunta y las dos respuestas del turno',
    location: 'Irlanda (eu-west-1)',
  },
  {
    name: 'OpenAI',
    role: 'Redacta la respuesta de la estrategia A a partir del corpus estructurado',
    location: 'Estados Unidos',
  },
  {
    name: 'Google',
    role: 'Redacta la respuesta de la estrategia B y busca en el almacén de los 106 PDF',
    location: 'Estados Unidos',
  },
  {
    name: 'Sentry',
    role: 'Registro de errores de la aplicación, sin cabeceras, cookies ni cuerpo',
    location: 'Estados Unidos',
  },
  {
    name: 'Google Analytics 4',
    role: 'Medición agregada de audiencia',
    location: 'Estados Unidos',
  },
  {
    name: 'PostHog',
    role: 'Medición agregada de audiencia',
    location: 'Unión Europea (eu.i.posthog.com)',
  },
];

const LEGAL_BASES: { purpose: string; basis: string }[] = [
  {
    purpose: 'Atender la consulta que envías al chat y devolverte las dos respuestas comparadas',
    basis:
      'La relación que inicias al usar el servicio, art. 6.1.b RGPD; sin tratar la pregunta no hay respuesta posible',
  },
  {
    purpose:
      'Conservar durante un plazo corto la pregunta y las respuestas para evaluar y mejorar la recuperación jurisprudencial',
    basis:
      'Interés legítimo en verificar la calidad del buscador, art. 6.1.f RGPD, con minimización previa y aviso antes de enviar',
  },
  {
    purpose:
      'Proteger el servicio frente a abuso: límite de peticiones por IP y minuto, límite de mensajes por navegador y registros técnicos de la plataforma',
    basis: 'Interés legítimo en la seguridad y disponibilidad del servicio, art. 6.1.f RGPD',
  },
  {
    purpose: 'Medir de forma agregada cuánta gente usa el sitio y qué páginas consulta',
    basis:
      'Interés legítimo en conocer el uso del sitio, art. 6.1.f RGPD, con exclusión permanente disponible en un clic',
  },
  {
    purpose: 'Responder a los correos que nos escribes',
    basis: 'Interés legítimo en atender tu solicitud, art. 6.1.f RGPD',
  },
];

const RIGHTS: { name: string; description: string }[] = [
  { name: 'Acceso', description: 'saber qué datos tuyos tratamos y obtener una copia' },
  { name: 'Rectificación', description: 'corregir los que sean inexactos o incompletos' },
  { name: 'Supresión', description: 'pedir que los borremos cuando ya no sean necesarios' },
  { name: 'Oposición', description: 'oponerte a los tratamientos basados en interés legítimo' },
  { name: 'Limitación', description: 'pedir que los conservemos sin usarlos mientras se resuelve' },
  { name: 'Portabilidad', description: 'recibirlos en un formato estructurado y de uso común' },
];

export function PrivacyPage() {
  usePageTitle('Privacidad', META.path, META.description, META.indexable);
  const conversations = useConversations((state) => state.conversations);
  return (
    <div className='mx-auto w-full max-w-3xl overflow-y-auto px-4 py-8'>
      <h1 className='mb-2 font-heading text-2xl font-semibold'>Privacidad</h1>
      <p className='mb-6 text-xs text-muted-foreground'>Última actualización: {LAST_UPDATED}</p>

      <p className='mb-6 rounded-lg border border-border bg-muted p-4 text-sm leading-relaxed'>
        No incluyas nombres, NIF, direcciones, expedientes ni otros datos que permitan identificar a
        una persona. El chat está diseñado para preguntas jurídicas abstractas y casos anonimizados.
      </p>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>1. Responsable del tratamiento</h2>
        <ul className='space-y-1 text-sm leading-relaxed text-muted-foreground'>
          <li>
            <span className='text-foreground'>Titular:</span> {CONTROLLER.name}
          </li>
          <li>
            <span className='text-foreground'>EIN:</span> {CONTROLLER.ein}
          </li>
          <li>
            <span className='text-foreground'>Domicilio:</span> {CONTROLLER.address}
          </li>
          <li>
            <span className='text-foreground'>Sitio web:</span> {CONTROLLER.site}
          </li>
          <li>
            <span className='text-foreground'>Contacto:</span>{' '}
            <a
              className='text-foreground underline underline-offset-4'
              href={`mailto:${CONTACT_EMAIL}`}
            >
              {CONTACT_EMAIL}
            </a>
          </li>
        </ul>
        <p className='mt-3 text-sm leading-relaxed text-muted-foreground'>
          El servicio se dirige también a personas que se encuentran en la Unión Europea, de modo
          que el tratamiento se rige por el Reglamento (UE) 2016/679 (RGPD) y, en lo que resulte
          aplicable, por la Ley Orgánica 3/2018 (LOPDGDD).
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>2. Qué datos tratamos</h2>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          No hay cuentas de usuario: no pedimos ni almacenamos nombre, correo ni contraseña para
          navegar por el sitio ni para usar el chat. Los datos que llegan a tratarse son estos:
        </p>
        <ul className='list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground'>
          <li>
            <span className='text-foreground'>Tu pregunta.</span> El texto que escribes en el chat.
            Si incluyes datos personales en él —tuyos o de un tercero— pasan a formar parte del
            tratamiento; por eso te pedimos que no lo hagas.
          </li>
          <li>
            <span className='text-foreground'>Identificadores aleatorios</span> de consulta y de
            conversación, generados en tu navegador. No se derivan de tu identidad ni de tu
            dispositivo y no permiten reconocerte en otra visita.
          </li>
          <li>
            <span className='text-foreground'>Métricas técnicas de cada respuesta:</span> modelo
            empleado, tokens consumidos, coste, tiempo de respuesta y sentencias citadas por cada
            estrategia.
          </li>
          <li>
            <span className='text-foreground'>Datos de conexión.</span> El proveedor de alojamiento
            y la red que protege el dominio procesan tu dirección IP y los datos técnicos de la
            petición para servir la página y aplicar el límite de cinco peticiones por IP y minuto.
            Esa información no se copia a nuestra base de datos.
          </li>
          <li>
            <span className='text-foreground'>Uso agregado del sitio:</span> páginas vistas y datos
            aproximados de origen y dispositivo, mediante las dos herramientas de analítica.
          </li>
          <li>
            <span className='text-foreground'>Errores de la aplicación,</span> cuando el registro de
            errores está activado, sin cabeceras, cookies ni cuerpo de la petición.
          </li>
          <li>
            <span className='text-foreground'>Tu correo</span> y lo que nos cuentes en él, si nos
            escribes.
          </li>
        </ul>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>3. Qué se envía al preguntar</h2>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Del contenido de la conversación, tu navegador transmite únicamente la última pregunta. La
          estrategia A la envía a OpenAI junto con fragmentos estructurados de 106 sentencias; la
          estrategia B la envía a Google Gemini, que busca de forma independiente en el File Search
          Store de esos 106 PDF.
        </p>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Para que el chat entienda a qué te refieres cuando preguntas por algo ya dicho, el
          servidor añade los seis últimos turnos de esa misma conversación, tomados de lo que ya
          había guardado y recortados. Cada estrategia recibe solo sus propias respuestas
          anteriores. Ese contexto se envía al proveedor junto con la pregunta, no amplía lo que se
          almacena y desaparece con la conversación a los 15 días.
        </p>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Ambos proveedores reciben la consulta en paralelo y aplican sus propias condiciones de
          tratamiento y conservación contratadas para sus API. La llamada de la estrategia A se
          realiza pidiendo expresamente que el proveedor no conserve la conversación; la estrategia
          B se apoya en un almacén de búsqueda que contiene únicamente los PDF públicos de las
          sentencias.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Al servidor no se envían ni la dirección IP ni el agente de usuario para guardarlos: no se
          almacenan en ninguna de nuestras tablas.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>4. Qué conserva la aplicación</h2>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Para evaluar y mejorar el buscador, el servidor guarda en Supabase la pregunta y las dos
          respuestas comparadas. También conserva modelo, tokens, coste, duración y citas utilizadas
          por cada estrategia, vinculados a identificadores aleatorios de consulta y conversación.
        </p>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Cuando el chat contesta con una de sus respuestas ya redactadas, sin llamar a ningún
          modelo, se guarda igualmente ese turno para poder seguir la conversación. En ese caso el
          texto sale del propio servidor y el coste registrado es cero.
        </p>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Esas tablas viven en un esquema privado que no está expuesto al navegador: la aplicación
          web no puede leerlas y solo los endpoints del chat y de investigación profunda escriben en
          ellas mediante funciones acotadas. No se guardan IP, agente de usuario, cookies ni el
          diagnóstico bruto de los proveedores.
        </p>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Para impedir que conocer la URL permita leer el hilo, tu navegador conserva además un
          secreto aleatorio de la conversación. Solo lo transmite a los endpoints del chat y de
          investigación profunda que necesitan demostrar posesión; Supabase guarda su huella
          SHA-256, nunca el secreto en claro.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El historial visible se conserva además en tu navegador mediante localStorage. Eliminarlo
          desde la interfaz o borrar los datos del sitio solo retira esa copia local.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>5. Con qué base jurídica</h2>
        <ul className='space-y-3 text-sm leading-relaxed text-muted-foreground'>
          {LEGAL_BASES.map((item) => (
            <li key={item.purpose} className='border-l-2 border-border pl-4'>
              <span className='text-foreground'>{item.purpose}.</span> {item.basis}.
            </li>
          ))}
        </ul>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>
          6. Destinatarios y transferencias
        </h2>
        <p className='mb-3 text-sm leading-relaxed text-muted-foreground'>
          No vendemos ni cedemos datos a terceros con fines comerciales. Intervienen únicamente los
          proveedores necesarios para que el servicio funcione:
        </p>
        <div className='mb-3 overflow-x-auto'>
          <table className='min-w-full border-collapse text-left text-xs'>
            <thead>
              <tr className='border-b border-border text-foreground'>
                <th className='py-2 pr-4 font-medium'>Proveedor</th>
                <th className='py-2 pr-4 font-medium'>Función</th>
                <th className='py-2 font-medium'>Ubicación del tratamiento</th>
              </tr>
            </thead>
            <tbody className='text-muted-foreground'>
              {RECIPIENTS.map((recipient) => (
                <tr key={recipient.name} className='border-b border-border align-top'>
                  <td className='py-2 pr-4 text-foreground'>{recipient.name}</td>
                  <td className='py-2 pr-4'>{recipient.role}</td>
                  <td className='py-2'>{recipient.location}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Parte de estos proveedores trata los datos fuera del Espacio Económico Europeo,
          principalmente en Estados Unidos. Esas transferencias se amparan en las condiciones de
          tratamiento de datos publicadas por cada proveedor, que incluyen cláusulas contractuales
          tipo de la Comisión Europea y, cuando el proveedor está certificado, el marco UE-EE. UU.
          de privacidad de datos. La base de datos del chat y una de las dos herramientas de
          analítica están alojadas dentro de la Unión Europea.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>7. Cuánto tiempo se conserva</h2>
        <ul className='list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground'>
          <li>
            <span className='text-foreground'>Preguntas y respuestas del chat: 15 días.</span> Un
            proceso automático diario elimina del servidor lo que supera ese plazo y deja constancia
            auditada de cada ejecución, sin copiar el contenido borrado.
          </li>
          <li>
            <span className='text-foreground'>Copias de seguridad:</span> el bucket es privado y
            cifrado, y tiene su propio plazo de retención. Tras una supresión, una copia puede
            permanecer hasta que ese plazo expire; no prometemos un borrado inmediato de las copias.
          </li>
          <li>
            <span className='text-foreground'>Analítica y errores:</span> según los plazos de
            conservación configurados en cada herramienta.
          </li>
          <li>
            <span className='text-foreground'>Correos:</span> mientras dure la conversación y el
            tiempo necesario para acreditar que se atendió.
          </li>
          <li>
            <span className='text-foreground'>Historial local:</span> permanece en tu navegador
            hasta que lo borres tú.
          </li>
        </ul>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>8. Tus derechos</h2>
        <ul className='mb-3 list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground'>
          {RIGHTS.map((right) => (
            <li key={right.name}>
              <span className='text-foreground'>{right.name}:</span> {right.description}.
            </li>
          ))}
        </ul>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Para ejercerlos, escribe a{' '}
          <a
            className='text-foreground underline underline-offset-4'
            href={`mailto:${CONTACT_EMAIL}`}
          >
            {CONTACT_EMAIL}
          </a>
          . Como no hay cuentas, para localizar una conversación concreta necesitamos su referencia
          técnica de supresión. Esa referencia no basta por sí sola para acreditar la identidad:
          verificaremos la solicitud por un canal separado antes de borrar nada.
        </p>
        {conversations.length > 0 && (
          <div className='mb-3 rounded-lg border border-border bg-muted p-3 text-sm'>
            <p className='mb-2 text-foreground'>
              Referencias técnicas guardadas en este navegador:
            </p>
            <ul className='space-y-1 text-muted-foreground'>
              {conversations.map((conversation, index) => (
                <li key={conversation.id}>
                  Conversación {index + 1}: {''}
                  <code className='break-all text-foreground'>{conversation.ledgerId}</code>
                </li>
              ))}
            </ul>
            <p className='mt-2 text-xs text-muted-foreground'>
              Envía solo la referencia necesaria; el secreto de posesión no se muestra ni debe
              compartirse.
            </p>
          </div>
        )}
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Si consideras que el tratamiento vulnera la normativa, puedes reclamar ante la{' '}
          <a
            className='text-foreground underline underline-offset-4'
            href='https://www.aepd.es'
            rel='noopener noreferrer'
            target='_blank'
          >
            Agencia Española de Protección de Datos
          </a>{' '}
          o ante la autoridad de control de tu país de residencia.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>
          9. Cookies y almacenamiento local
        </h2>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          El sitio no usa cookies propias ni de sesión: no hay inicio de sesión que mantener. Las
          dos herramientas de analítica sí instalan sus propios identificadores —cookies en el caso
          de Google Analytics 4, almacenamiento del navegador en el de PostHog— para no contar dos
          veces a la misma persona.
        </p>
        <p className='mb-2 text-sm leading-relaxed text-muted-foreground'>
          Puedes excluir tu navegador de forma permanente de ambas visitando{' '}
          <a className='text-foreground underline underline-offset-4' href='/?no_analytics=1'>
            residenciafiscal.org/?no_analytics=1
          </a>
          . La exclusión queda guardada en tu navegador y, a partir de ahí, ninguna de las dos
          herramientas se instala; se revierte con <code>?no_analytics=0</code>. También puedes
          bloquear o borrar cookies desde la configuración de tu navegador.
        </p>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Además del historial del chat y de esa marca de exclusión, el almacenamiento local guarda
          el secreto aleatorio que protege cada conversación y preferencias de la interfaz. Ese
          secreto solo sale de tu dispositivo hacia los endpoints del chat y de investigación
          profunda que deben demostrar que el navegador posee el hilo.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>10. Seguridad</h2>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Todo el tráfico viaja cifrado. Las tablas del chat están en un esquema privado con
          seguridad a nivel de fila y sin permisos para los roles públicos; el navegador nunca
          recibe las credenciales del servidor ni consulta la base de datos directamente. El
          registro de errores borra cabeceras, cookies y cuerpo de la petición antes de enviar nada.
          Ningún sistema es infalible, pero mantenemos medidas técnicas y organizativas adecuadas al
          riesgo y las revisamos cuando cambia la arquitectura.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>11. Menores</h2>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El servicio se dirige a profesionales y personas adultas interesadas en jurisprudencia
          tributaria. No está dirigido a menores de edad y no recogemos datos de menores de forma
          consciente.
        </p>
      </section>

      <section className='mb-8'>
        <h2 className='mb-3 font-heading text-lg font-semibold'>12. Contenido y responsabilidad</h2>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          El contenido del sitio tiene finalidad informativa y de investigación. No constituye
          asesoramiento jurídico ni sustituye el criterio de un profesional. Las respuestas del chat
          las genera un modelo de inteligencia artificial y pueden contener errores: contrasta
          siempre la sentencia y la norma citadas antes de tomar una decisión.
        </p>
      </section>

      <section>
        <h2 className='mb-3 font-heading text-lg font-semibold'>13. Cambios en esta política</h2>
        <p className='text-sm leading-relaxed text-muted-foreground'>
          Esta política se actualiza cuando cambia el sistema que describe: si entra o sale un
          proveedor, cambia el plazo de conservación o se añade un tratamiento nuevo. La fecha del
          encabezado indica la última revisión. Para cualquier duda, escribe a{' '}
          <a
            className='text-foreground underline underline-offset-4'
            href={`mailto:${CONTACT_EMAIL}`}
          >
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </section>
    </div>
  );
}
