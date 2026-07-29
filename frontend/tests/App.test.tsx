import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '@/App';

describe('App', () => {
  it('redirige la home a la página de España', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByTestId('chat-welcome')).toBeInTheDocument();
  });
});
