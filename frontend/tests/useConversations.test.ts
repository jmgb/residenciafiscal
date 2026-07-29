import { beforeEach, describe, expect, it } from 'vitest';
import {
  CONVERSATIONS_STORAGE_KEY,
  deriveTitle,
  useConversations,
} from '@/stores/useConversations';

function reset() {
  window.localStorage.clear();
  useConversations.setState({ conversations: [] });
}

describe('deriveTitle', () => {
  it('usa el primer mensaje del usuario recortado', () => {
    expect(deriveTitle('¿Cómo se computan los 183 días?')).toBe('¿Cómo se computan los 183 días?');
  });

  it('trunca los títulos largos añadiendo puntos suspensivos', () => {
    const long = 'a'.repeat(80);
    const title = deriveTitle(long);
    expect(title.length).toBeLessThanOrEqual(61);
    expect(title.endsWith('…')).toBe(true);
  });

  it('usa un título por defecto cuando el texto está vacío', () => {
    expect(deriveTitle('   ')).toBe('Consulta sin título');
  });

  it('colapsa los saltos de línea', () => {
    expect(deriveTitle('primera\nsegunda')).toBe('primera segunda');
  });
});

describe('useConversations', () => {
  beforeEach(reset);

  it('crea una conversación con id y sin mensajes', () => {
    const id = useConversations.getState().createConversation();
    const conversation = useConversations.getState().getConversation(id);

    expect(conversation).toBeDefined();
    expect(conversation?.messages).toEqual([]);
    expect(useConversations.getState().conversations).toHaveLength(1);
  });

  it('añade mensajes y actualiza el título con el primero del usuario', () => {
    const store = useConversations.getState();
    const id = store.createConversation();

    store.appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: '¿Qué son las ausencias esporádicas?',
      createdAt: '2026-07-29T10:00:00.000Z',
    });

    const conversation = useConversations.getState().getConversation(id);
    expect(conversation?.messages).toHaveLength(1);
    expect(conversation?.title).toBe('¿Qué son las ausencias esporádicas?');
  });

  it('no cambia el título con mensajes posteriores', () => {
    const store = useConversations.getState();
    const id = store.createConversation();

    store.appendMessage(id, {
      id: 'm1',
      role: 'user',
      content: 'primera pregunta',
      createdAt: '2026-07-29T10:00:00.000Z',
    });
    store.appendMessage(id, {
      id: 'm2',
      role: 'user',
      content: 'segunda pregunta',
      createdAt: '2026-07-29T10:01:00.000Z',
    });

    expect(useConversations.getState().getConversation(id)?.title).toBe('primera pregunta');
  });

  it('actualiza un mensaje existente por id', () => {
    const store = useConversations.getState();
    const id = store.createConversation();

    store.appendMessage(id, {
      id: 'a1',
      role: 'assistant',
      content: '',
      createdAt: '2026-07-29T10:00:00.000Z',
      isStreaming: true,
    });
    store.updateMessage(id, 'a1', { content: 'respuesta completa', isStreaming: false });

    const message = useConversations.getState().getConversation(id)?.messages[0];
    expect(message?.content).toBe('respuesta completa');
    expect(message?.isStreaming).toBe(false);
  });

  it('borra una conversación', () => {
    const store = useConversations.getState();
    const id = store.createConversation();
    store.deleteConversation(id);

    expect(useConversations.getState().conversations).toHaveLength(0);
    expect(useConversations.getState().getConversation(id)).toBeUndefined();
  });

  it('ordena las conversaciones por actualización descendente', async () => {
    const store = useConversations.getState();
    const first = store.createConversation();
    const second = store.createConversation();

    // `createConversation` deja la más reciente arriba; sin la espera, ambas
    // podrían compartir el mismo `updatedAt` al milisegundo y el orden no sería
    // determinista.
    expect(useConversations.getState().conversations[0].id).toBe(second);
    await new Promise((resolve) => setTimeout(resolve, 5));

    store.appendMessage(first, {
      id: 'm1',
      role: 'user',
      content: 'reactivo la primera',
      createdAt: '2026-07-29T11:00:00.000Z',
    });

    expect(useConversations.getState().conversations[0].id).toBe(first);
    expect(useConversations.getState().conversations[1].id).toBe(second);
  });

  it('persiste en localStorage bajo una clave versionada', () => {
    useConversations.getState().createConversation();
    expect(window.localStorage.getItem(CONVERSATIONS_STORAGE_KEY)).not.toBeNull();
  });

  it('ignora operaciones sobre una conversación inexistente', () => {
    const store = useConversations.getState();
    expect(() =>
      store.appendMessage('no-existe', {
        id: 'm1',
        role: 'user',
        content: 'hola',
        createdAt: '2026-07-29T10:00:00.000Z',
      })
    ).not.toThrow();
    expect(useConversations.getState().conversations).toHaveLength(0);
  });
});
