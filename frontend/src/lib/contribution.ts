/**
 * Enlaces de contribución del proyecto.
 *
 * El pipeline no es español: analiza resoluciones, verifica las citas contra su
 * PDF y publica el criterio del tribunal con su página. España es el único país
 * con corpus porque alguien reunió sus sentencias, no por una limitación del
 * código. Las páginas de los países pendientes enlazan aquí para que quien pueda
 * aportar la fuente de su jurisdicción llegue al formulario con el país ya
 * rellenado.
 */
export const REPO_URL = 'https://github.com/jmgb/residenciafiscal';

/** Formulario de `.github/ISSUE_TEMPLATE/`. Si se renombra allí, cambia aquí. */
const COUNTRY_ISSUE_TEMPLATE = 'aportar_pais.yml';

/** URL de la issue de aportación de un país, prerrellenada con su nombre. */
export function countryContributionUrl(countryName: string): string {
  const params = new URLSearchParams({
    template: COUNTRY_ISSUE_TEMPLATE,
    title: `Aportar jurisprudencia: ${countryName}`,
    pais: countryName,
  });
  return `${REPO_URL}/issues/new?${params.toString()}`;
}
