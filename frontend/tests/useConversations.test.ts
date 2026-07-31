import { beforeEach, describe, expect, it } from 'vitest';
import {
  CONVERSATIONS_STORAGE_KEY,
  clearStreamingFlags,
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
    const stored = window.localStorage.getItem(CONVERSATIONS_STORAGE_KEY);

    expect(stored).not.toBeNull();
    expect(JSON.parse(stored as string).version).toBe(2);
  });

  it('apaga el streaming al rehidratar una respuesta que quedó a medias', async () => {
    // Estado tal y como lo dejaría una recarga en mitad de una respuesta.
    window.localStorage.setItem(
      CONVERSATIONS_STORAGE_KEY,
      JSON.stringify({
        version: 0,
        state: {
          conversations: [
            {
              id: 'c1',
              title: 'consulta interrumpida',
              createdAt: '2026-07-29T10:00:00.000Z',
              updatedAt: '2026-07-29T10:00:05.000Z',
              messages: [
                {
                  id: 'm1',
                  role: 'user',
                  content: '¿Y los 183 días?',
                  createdAt: '2026-07-29T10:00:00.000Z',
                },
                {
                  id: 'a1',
                  role: 'assistant',
                  content: 'El Tribunal Supremo',
                  createdAt: '2026-07-29T10:00:05.000Z',
                  isStreaming: true,
                },
              ],
            },
          ],
        },
      })
    );

    await useConversations.persist.rehydrate();

    const messages = useConversations.getState().getConversation('c1')?.messages;
    expect(messages).toHaveLength(2);
    // El texto que alcanzó a llegar se conserva; el cursor desaparece.
    expect(messages?.[1].content).toBe('El Tribunal Supremo');
    expect(messages?.[1].isStreaming).toBe(false);
    expect(messages?.some((message) => message.isStreaming)).toBe(false);
  });

  it('descarta un estado persistido con forma incompatible', async () => {
    window.localStorage.setItem(
      CONVERSATIONS_STORAGE_KEY,
      JSON.stringify({ version: 0, state: { conversations: 'datos-corruptos' } })
    );

    await expect(useConversations.persist.rehydrate()).resolves.toBeUndefined();
    expect(useConversations.getState().conversations).toEqual([]);
  });

  it('descarta solo la conversación dañada si una fuente persistida no es renderizable', async () => {
    const base = {
      title: 'consulta válida',
      createdAt: '2026-07-29T10:00:00.000Z',
      updatedAt: '2026-07-29T10:00:05.000Z',
    };
    window.localStorage.setItem(
      CONVERSATIONS_STORAGE_KEY,
      JSON.stringify({
        version: 0,
        state: {
          conversations: [
            { ...base, id: 'c-valida', messages: [] },
            {
              ...base,
              id: 'c-danada',
              messages: [
                {
                  id: 'a1',
                  role: 'assistant',
                  content: 'respuesta',
                  createdAt: '2026-07-29T10:00:05.000Z',
                  sources: [
                    {
                      archivo: 'STS_107_2018.pdf',
                      roj: 'STS 107/2018',
                      ecli: 'ECLI:ES:TS:2018:107',
                      organo: null,
                      fecha: '2018-01-16',
                      resultado: 'GANA_AEAT',
                      criterioDecisivo: ['CRIT_183_DIAS'],
                      esCasoResidencia: true,
                      extracto: 'Texto',
                    },
                  ],
                },
              ],
            },
          ],
        },
      })
    );

    await useConversations.persist.rehydrate();

    expect(useConversations.getState().conversations.map(({ id }) => id)).toEqual(['c-valida']);
  });

  it('conserva una fuente histórica al migrar sin inventarle campos v2', async () => {
    window.localStorage.setItem(
      CONVERSATIONS_STORAGE_KEY,
      JSON.stringify({
        version: 0,
        state: {
          conversations: [
            {
              id: 'c-legada',
              title: 'consulta antigua',
              createdAt: '2026-07-29T10:00:00.000Z',
              updatedAt: '2026-07-29T10:00:05.000Z',
              messages: [
                {
                  id: 'a1',
                  role: 'assistant',
                  content: 'respuesta',
                  createdAt: '2026-07-29T10:00:05.000Z',
                  sources: [
                    {
                      archivo: 'STS_107_2018.pdf',
                      roj: 'STS 107/2018',
                      ecli: 'ECLI:ES:TS:2018:107',
                      organo: 'Tribunal Supremo',
                      fecha: '2018-01-16',
                      resultado: 'GANA_AEAT',
                      criterioDecisivo: ['CRIT_183_DIAS'],
                      esCasoResidencia: true,
                      extracto: 'Resumen histórico.',
                    },
                  ],
                },
              ],
            },
          ],
        },
      })
    );

    await useConversations.persist.rehydrate();

    const source = useConversations.getState().getConversation('c-legada')?.messages[0]
      .sources?.[0];
    expect(source?.extracto).toBe('Resumen histórico.');
    expect(source).not.toHaveProperty('sourceId');
    expect(source).not.toHaveProperty('pageIndex');
  });

  it('descarta una conversación con una fuente que aparenta ser v2 pero no es trazable', () => {
    const conversations = [
      {
        id: 'c-v2-invalida',
        title: 'consulta',
        createdAt: '2026-07-29T10:00:00.000Z',
        updatedAt: '2026-07-29T10:00:05.000Z',
        messages: [
          {
            id: 'a1',
            role: 'assistant',
            content: 'respuesta',
            createdAt: '2026-07-29T10:00:05.000Z',
            sources: [
              {
                archivo: 'SAN_1210_2023.pdf',
                roj: 'SAN 1210/2023',
                ecli: 'ECLI:ES:AN:2023:1210',
                organo: 'Audiencia Nacional',
                fecha: '2023-02-22',
                resultado: 'GANA_AEAT',
                criterioDecisivo: ['CRIT_183_DIAS'],
                esCasoResidencia: true,
                sourceId: 'source-1',
                issueId: 'residencia-fiscal',
                issueLabel: 'Residencia fiscal',
                anchorId: 'anchor-1',
                pageIndex: 0,
                printedPage: null,
                extracto: 'Texto que no puede atribuirse a una página válida.',
                fidelity: 'exact',
                sourceSha256: 'no-es-un-hash',
                reviewStatus: {
                  technical: 'VALIDATED',
                  legal: 'AGENT_REVIEWED',
                },
              },
            ],
          },
        ],
      },
    ];

    expect(clearStreamingFlags(conversations)).toEqual([]);
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
