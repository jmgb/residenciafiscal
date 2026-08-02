import type { AnclajeLiteral } from '@/types/sentencias';

function pageLabel(fragment: { pageIndex: number; printedPage: string | null }): string {
  const physical = `Página PDF ${fragment.pageIndex}`;
  if (!fragment.printedPage || fragment.printedPage === String(fragment.pageIndex)) return physical;
  return `${physical} · Página impresa ${fragment.printedPage}`;
}

/** Extractos literales, sin recortar ni reformatear el texto del PDF. */
export function SentenciaAnchors({ anchors }: { anchors: AnclajeLiteral[] }) {
  if (anchors.length === 0) return null;
  return (
    <section aria-labelledby='anclajes' className='mt-8 border-border border-t pt-6'>
      <h2 id='anclajes' className='mb-1.5 font-heading font-semibold text-lg'>
        Extractos literales de la sentencia
      </h2>
      <p className='mb-4 text-muted-foreground text-xs leading-relaxed'>
        Texto copiado del PDF publicado por el CENDOJ y verificado carácter a carácter contra él.
        Todo lo demás de esta página es análisis estructurado, no palabras del tribunal.
      </p>
      <ul className='space-y-4'>
        {anchors.map((anchor) => (
          <li key={anchor.anchorId}>
            {anchor.fragments.map((fragment) => (
              <figure key={`${anchor.anchorId}:${fragment.pageIndex}`}>
                <blockquote className='border-border border-l-2 pl-3 text-sm leading-relaxed italic'>
                  {fragment.verbatimText}
                </blockquote>
                <figcaption className='mt-1 text-muted-foreground text-xs'>
                  {pageLabel(fragment)}
                </figcaption>
              </figure>
            ))}
          </li>
        ))}
      </ul>
    </section>
  );
}
