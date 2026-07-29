import { Link } from 'react-router';
import { COUNTRY_ROUTES, type CountryRoute } from '@/data/countryRoutes';
import { usePageTitle } from '@/lib/usePageTitle';

interface CountryPageProps {
  country: CountryRoute;
}

export function CountryPage({ country }: CountryPageProps) {
  usePageTitle(`Residencia fiscal en ${country.name}`, country.path);

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
            Estamos preparando la página de jurisprudencia fiscal de {country.name}. Cada país
            tendrá su propia documentación y sus propios criterios nacionales.
          </p>
        </header>

        <div className='mt-8 rounded-lg border border-border bg-muted p-5 text-sm leading-relaxed text-secondary-foreground'>
          <strong>Próximamente:</strong> la página se activará cuando dispongamos de la
          documentación nacional revisada y trazable.
        </div>

        <section className='mt-14 border-t border-border pt-8' aria-labelledby='country-routes'>
          <h2 id='country-routes' className='mb-2 font-heading text-2xl font-semibold'>
            Países disponibles
          </h2>
          <p className='mb-5 max-w-2xl text-sm leading-relaxed text-muted-foreground'>
            Selecciona un país para consultar su página. La jurisprudencia de cada país se
            incorporará de forma independiente.
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
                  {route.path !== '/españa' && (
                    <span className='text-xs text-muted-foreground'>Próximamente</span>
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
