import { render, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { usePageTitle } from '@/lib/usePageTitle';

function Metadata({ indexable }: { indexable: boolean }) {
  usePageTitle('Residencia fiscal en Argentina', '/argentina', 'Descripción de prueba', indexable);
  return null;
}

describe('usePageTitle', () => {
  it('marca como noindex las páginas de países sin corpus', async () => {
    document.head.innerHTML = '<meta name="robots" content="index, follow" />';

    render(<Metadata indexable={false} />);

    await waitFor(() => {
      expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
        'content',
        'noindex, follow'
      );
    });
  });
});
