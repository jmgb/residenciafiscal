import { Link } from 'react-router';
import { COUNTRY_ROUTES, type CountryRoute } from '@/data/countryRoutes';
import { countryContributionUrl, REPO_URL } from '@/lib/contribution';
import { usePageTitle } from '@/lib/usePageTitle';

interface CountryPageProps {
  country: CountryRoute;
}

export function CountryPage({ country }: CountryPageProps) {
  usePageTitle(
    `Residencia fiscal en ${country.name}`,
    country.path,
    country.description,
    country.indexable
  );

  return (
    <div className='w-full overflow-y-auto'>
      <div className='mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14'>
        <header className='max-w-3xl border-t-4 border-primary pt-6'>
          <p className='mb-3 font-mono text-xs font-semibold uppercase tracking-[0.16em] text-primary'>
            Residencia Fiscal · {country.name}
          </p>
          <h1 className='mb-4 font-heading text-3xl font-semibold tracking-tight sm:text-5xl'>
            Residencia fiscal en {country.name}
          </h1>
          <p className='max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg'>
            Todavía no hay jurisprudencia de {country.name} en el corpus. España es el único país
            publicado, y no porque el proyecto sea español: porque alguien reunió sus sentencias.
          </p>
        </header>

        <section
          className='mt-10 rounded-lg border border-border bg-muted p-6'
          aria-labelledby='country-contribute'
        >
          <h2
            id='country-contribute'
            className='mb-3 font-heading text-2xl font-semibold tracking-tight'
          >
            {country.name} lo puede abrir cualquiera
          </h2>
          <p className='mb-5 max-w-2xl text-sm leading-relaxed text-secondary-foreground'>
            El pipeline es agnóstico del país: analiza resoluciones, contrasta cada cita con el
            documento de origen y publica el criterio del tribunal con su página. Lo que falta para{' '}
            {country.name} no es código, son tres cosas.
          </p>
          <ol
            aria-label='Qué necesita un país nuevo'
            className='mb-6 grid gap-3 text-sm leading-relaxed text-secondary-foreground'
          >
            <li className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>Una fuente pública oficial</strong> — el buscador de
              jurisprudencia del país y sus condiciones de reutilización. Sin una licencia clara, el
              corpus no se publica.
            </li>
            <li className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>El precepto que decide la residencia</strong> — el
              equivalente al art. 9 LIRPF en la normativa nacional, con su texto oficial y el
              artículo de desempate de sus convenios de doble imposición.
            </li>
            <li className='border-l-2 border-primary pl-4'>
              <strong className='font-semibold'>Alguien que lo revise</strong> — el análisis lo
              redacta un modelo de lenguaje, así que hace falta un jurista del país que revise que
              el análisis dice lo que dice la resolución.
            </li>
          </ol>
          <div className='flex flex-col gap-3 sm:flex-row sm:items-center'>
            <a
              href={countryContributionUrl(country.name)}
              target='_blank'
              rel='noopener noreferrer'
              className='control-focus control-press inline-flex items-center justify-center rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-600'
            >
              Proponer {country.name} en GitHub
            </a>
            <a
              href={`${REPO_URL}/blob/main/CONTRIBUTING.md`}
              target='_blank'
              rel='noopener noreferrer'
              className='control-focus inline-flex items-center justify-center rounded-md border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-secondary'
            >
              Cómo se construye un corpus
            </a>
          </div>
        </section>

        <section className='mt-14 border-t border-border pt-8' aria-labelledby='country-routes'>
          <h2 id='country-routes' className='mb-2 font-heading text-2xl font-semibold'>
            Países disponibles
          </h2>
          <p className='mb-5 max-w-2xl text-sm leading-relaxed text-muted-foreground'>
            España es el único país con corpus. El resto están abiertos a quien pueda aportar su
            jurisprudencia: cada país se incorpora de forma independiente.
          </p>
          <nav aria-label='Rutas por país' className='grid gap-2 sm:grid-cols-2 lg:grid-cols-3'>
            {COUNTRY_ROUTES.map((route) => {
              const isActive = route.path === country.path;
              return (
                <Link
                  key={route.path}
                  to={route.path}
                  aria-label={route.name}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex items-center justify-between rounded-md border px-3 py-2.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring ${
                    isActive
                      ? 'border-primary bg-primary-50 font-semibold text-primary'
                      : 'border-border hover:bg-secondary'
                  }`}
                >
                  <span>{route.name}</span>
                  {/* `indexable` es la señal de que un país ya tiene corpus publicado. */}
                  {!route.indexable && (
                    <span className='text-xs text-muted-foreground'>Sin corpus</span>
                  )}
                </Link>
              );
            })}
          </nav>
        </section>
      </div>
    </div>
  );
}
