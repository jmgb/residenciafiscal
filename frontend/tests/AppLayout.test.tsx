import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppLayout } from '@/components/layout/AppLayout';
import { GOOGLE_ANALYTICS_ID } from '@/components/layout/GoogleAnalytics';
import { SIDEBAR_COLLAPSED_STORAGE_KEY } from '@/components/layout/useSidebarCollapsed';
import { useConversations } from '@/stores/useConversations';

function renderLayout(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path='/' element={<div>contenido</div>} />
          <Route path='/c/:conversationId' element={<div>conversación</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('AppLayout', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    useConversations.setState({ conversations: [] });
  });

  it('renderiza el contenido de la ruta', () => {
    renderLayout();
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });

  it('muestra el país seleccionado en el título superior', () => {
    render(
      <MemoryRouter initialEntries={['/espana']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path='/espana' element={<div>España</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Residencia Fiscal en España')).toBeInTheDocument();
    expect(screen.getByText('España · Art. 9 LIRPF')).toBeInTheDocument();
  });

  it('muestra el estado del corpus en una jurisdicción pendiente', () => {
    render(
      <MemoryRouter initialEntries={['/portugal']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path='/portugal' element={<div>Portugal</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Portugal · Sin corpus')).toBeInTheDocument();
    expect(screen.queryByText('Art. 9 LIRPF')).not.toBeInTheDocument();
  });

  it('usa un descriptor neutral en las páginas sin jurisdicción', () => {
    render(
      <MemoryRouter initialEntries={['/metodologia']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path='/metodologia' element={<div>Metodología</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Jurisprudencia por país')).toBeInTheDocument();
  });

  it('reconoce la nueva consulta como contexto español', () => {
    render(
      <MemoryRouter initialEntries={['/consulta']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path='/consulta' element={<div>Consulta</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Residencia Fiscal en España')).toBeInTheDocument();
    expect(screen.getByText('España · Art. 9 LIRPF')).toBeInTheDocument();
  });

  it('reconoce España cuando la ruta contiene la ñ codificada', () => {
    render(
      <MemoryRouter initialEntries={['/espa%C3%B1a']}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path='/españa' element={<div>España</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Residencia Fiscal en España')).toBeInTheDocument();
  });

  it('arranca con el sidebar expandido', () => {
    renderLayout();
    expect(screen.getByRole('button', { name: 'Colapsar menú lateral' })).toBeInTheDocument();
  });

  it('colapsa y persiste la preferencia', async () => {
    const user = userEvent.setup();
    renderLayout();

    await user.click(screen.getByRole('button', { name: 'Colapsar menú lateral' }));

    expect(screen.getByRole('button', { name: 'Expandir menú lateral' })).toBeInTheDocument();
    expect(window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY)).toBe('true');
  });

  it('rehidrata el estado colapsado desde localStorage', () => {
    window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, 'true');
    renderLayout();
    expect(screen.getByRole('button', { name: 'Expandir menú lateral' })).toBeInTheDocument();
  });

  it('muestra el mensaje vacío cuando no hay conversaciones', () => {
    renderLayout();
    expect(screen.getByText('Todavía no has hecho ninguna consulta.')).toBeInTheDocument();
  });

  it('lista las conversaciones guardadas con enlace', () => {
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'pregunta sobre los 183 días',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    renderLayout();

    const link = screen.getByRole('link', { name: 'pregunta sobre los 183 días' });
    expect(link).toHaveAttribute('href', `/c/${id}`);
  });

  it('borra una conversación desde el sidebar', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'consulta a borrar',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    renderLayout();
    await user.click(
      screen.getByRole('button', { name: 'Borrar conversación: consulta a borrar' })
    );

    expect(screen.queryByRole('link', { name: 'consulta a borrar' })).not.toBeInTheDocument();
  });

  it('conserva la conversación si se cancela la confirmación de borrado', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const user = userEvent.setup();
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'consulta importante',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    renderLayout();
    await user.click(
      screen.getByRole('button', { name: 'Borrar conversación: consulta importante' })
    );

    expect(screen.getByRole('link', { name: 'consulta importante' })).toBeInTheDocument();
    expect(window.confirm).toHaveBeenCalledOnce();
  });

  it('marca como activa la conversación de la ruta', () => {
    const id = useConversations.getState().createConversation();
    useConversations.getState().appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'consulta activa',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    renderLayout(`/c/${id}`);

    expect(screen.getByRole('link', { name: 'consulta activa' })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByText('Residencia Fiscal en España')).toBeInTheDocument();
    expect(screen.getByText('España · Art. 9 LIRPF')).toBeInTheDocument();
  });

  it('cierra el drawer móvil al navegar', async () => {
    const user = userEvent.setup();
    renderLayout();

    await user.click(screen.getByRole('button', { name: 'Abrir menú de navegación' }));
    const drawer = await screen.findByRole('dialog');

    await user.click(within(drawer).getByRole('button', { name: 'Nueva consulta' }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('no monta un pie visual y conserva la analítica exactamente una vez', async () => {
    renderLayout();

    expect(document.querySelector('footer')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(
        document.querySelectorAll(
          `script[src="https://www.googletagmanager.com/gtag/js?id=${GOOGLE_ANALYTICS_ID}"]`
        )
      ).toHaveLength(1);
    });
  });
});
