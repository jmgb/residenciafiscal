/**
 * Enlaces y contenido de contribución del proyecto.
 *
 * El pipeline no es español: analiza resoluciones, verifica las citas contra su
 * PDF y publica el criterio del tribunal con su página. España es el único país
 * con corpus porque alguien reunió sus sentencias, no por una limitación del
 * código. Lo que decide si un país entra es el conocimiento de quien lo conoce,
 * así que la invitación se dirige a expertos, no solo a desarrolladores.
 *
 * Fuente única de los dos canales y de los perfiles: `/colaborar` y las páginas
 * de país los comparten para que no se desincronicen.
 */
export const REPO_URL = 'https://github.com/jmgb/residenciafiscal';

/** Buzón del proyecto, para quien no tiene cuenta de GitHub. */
export const CONTACT_EMAIL = 'info@residenciafiscal.org';

/** Página pública que centraliza la invitación. Es la ruta indexable. */
export const COLLABORATE_PATH = '/colaborar';

/** Formulario de `.github/ISSUE_TEMPLATE/`. Si se renombra allí, cambia aquí. */
const COUNTRY_ISSUE_TEMPLATE = 'aportar_pais.yml';

/** URL de la issue de aportación de un país, prerrellenada con su nombre. */
export function countryContributionUrl(countryName?: string): string {
  const params = new URLSearchParams({ template: COUNTRY_ISSUE_TEMPLATE });
  if (countryName) {
    params.set('title', `Aportar jurisprudencia: ${countryName}`);
    params.set('pais', countryName);
  }
  return `${REPO_URL}/issues/new?${params.toString()}`;
}

/**
 * `mailto:` con el asunto ya puesto. Muchos juristas del público objetivo no
 * tienen cuenta de GitHub y crearla para escribir es fricción suficiente para
 * perderlos; el correo es el canal equivalente, no un plan B.
 */
export function contributionMailto(countryName?: string): string {
  const subject = countryName
    ? `Aportar jurisprudencia: ${countryName}`
    : 'Colaborar con Residencia Fiscal';
  return `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}`;
}

export interface ExpertProfile {
  /** Perfil profesional, tal y como se reconocería quien lo lee. */
  title: string;
  /** Qué aporta ese perfil concreto, no un «ayuda al proyecto» genérico. */
  detail: string;
}

/**
 * Perfiles que mueven la aguja en un corpus nuevo. El orden no es casual: va de
 * quien decide si el análisis es correcto a quien lo hace posible técnicamente.
 */
export const EXPERT_PROFILES: ExpertProfile[] = [
  {
    title: 'Abogados y asesores fiscales',
    detail:
      'Revisar que el análisis dice lo que dice la resolución, y señalar qué criterio pesa de verdad ante sus tribunales frente al que solo figura en la ley.',
  },
  {
    title: 'Académicos e investigadores de fiscalidad internacional',
    detail:
      'Delimitar qué preceptos y qué convenios deciden la residencia en su jurisdicción, y en qué punto está la doctrina.',
  },
  {
    title: 'Documentalistas y bibliotecarios jurídicos',
    detail:
      'Localizar y catalogar las resoluciones en el buscador oficial. Es la parte que más tiempo consume y la que menos se ofrece nadie a hacer.',
  },
  {
    title: 'Traductores jurídicos',
    detail:
      'Adaptar la terminología del análisis a la del país sin falsear el concepto. Hoy el schema está en español y eso limita a las jurisdicciones no hispanohablantes.',
  },
  {
    title: 'Economistas y peritos',
    detail:
      'Valorar la prueba económica —centro de intereses económicos, vínculos patrimoniales—, que es donde se decide buena parte de los litigios.',
  },
  {
    title: 'Desarrolladores y científicos de datos',
    detail:
      'Pipeline, recuperación y frontend. Es lo único que ya existe, así que aquí la aportación es mejorar, no arrancar.',
  },
];
