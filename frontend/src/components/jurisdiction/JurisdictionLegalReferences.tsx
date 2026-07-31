import { BookOpen, ExternalLink } from 'lucide-react';
import type { LegalReference } from '@/data/countryRoutes';

const reviewDateFormatter = new Intl.DateTimeFormat('es-ES', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});

const formatReviewDate = (reviewedAt: string): string =>
  reviewDateFormatter.format(new Date(`${reviewedAt}T00:00:00Z`));

interface JurisdictionLegalReferencesProps {
  references: LegalReference[];
}

export const JurisdictionLegalReferences = ({ references }: JurisdictionLegalReferencesProps) => (
  <section
    aria-labelledby='jurisdiction-legal-framework'
    className='mb-6 w-full max-w-xl rounded-lg border border-border bg-card p-4 text-left shadow-sm'
  >
    <h2
      id='jurisdiction-legal-framework'
      className='mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground'
    >
      Marco jurídico
    </h2>
    <ul className='divide-y divide-border'>
      {references.map((reference) => (
        <li
          key={`${reference.kind}-${reference.officialUrl}`}
          className='py-3 first:pt-0 last:pb-0'
        >
          <div className='flex items-start justify-between gap-4'>
            <div className='min-w-0 flex-1'>
              <a
                href={reference.officialUrl}
                target='_blank'
                rel='noopener noreferrer'
                className='control-focus inline-flex items-center gap-1.5 rounded font-mono text-sm font-semibold text-primary underline-offset-4 hover:underline'
              >
                {reference.shortCitation}
                <ExternalLink className='h-3.5 w-3.5' aria-hidden='true' />
              </a>
              <p className='mt-1 text-sm leading-snug text-foreground'>{reference.title}</p>
            </div>
            <BookOpen className='mt-1 h-5 w-5 shrink-0 text-muted-foreground' aria-hidden='true' />
          </div>
          <p className='mt-2 text-xs text-muted-foreground'>
            Fuente oficial · Revisada el{' '}
            <time dateTime={reference.reviewedAt}>{formatReviewDate(reference.reviewedAt)}</time>
          </p>
        </li>
      ))}
    </ul>
  </section>
);
