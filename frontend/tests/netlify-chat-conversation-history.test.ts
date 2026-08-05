import { describe, expect, it } from 'vitest';
import {
  contextualRetrievalQuery,
  conversationContextBlock,
  MAX_HISTORY_ANSWER_CHARS,
  MAX_HISTORY_TURNS,
} from '../netlify/functions/chat/conversation-history';

describe('contexto conversacional del chat', () => {
  it('no añade bloque cuando el turno es el primero', () => {
    expect(conversationContextBlock([])).toBe('');
  });

  it('ordena los turnos y advierte de que el historial no es evidencia', () => {
    const block = conversationContextBlock([
      { question: '¿Cuántos días exige el artículo 9?', answer: 'Más de 183 días.' },
      { question: '¿Y si me ausento?', answer: 'Depende de la ausencia esporádica.' },
    ]);

    expect(block).toContain('¿Cuántos días exige el artículo 9?');
    expect(block).toContain('Más de 183 días.');
    expect(block.indexOf('artículo 9')).toBeLessThan(block.indexOf('¿Y si me ausento?'));
    expect(block).toContain('no es evidencia');
  });

  it('marca la respuesta editorial como ajena a la estrategia', () => {
    const block = conversationContextBlock([
      { question: '¿Y las ausencias?', answer: 'Las esporádicas suman.', editorial: true },
    ]);

    expect(block).toContain('Las esporádicas suman.');
    expect(block).toContain('editorial');
    expect(block).not.toContain('Tú:');
  });

  it('conserva la pregunta de un turno que esta estrategia no respondió', () => {
    const block = conversationContextBlock([{ question: '¿Y las ausencias?', answer: '' }]);

    expect(block).toContain('¿Y las ausencias?');
  });

  // El historial entra en cada petición: sin tope, una conversación larga infla el
  // coste de todos los turnos siguientes.
  it('recorta las respuestas largas y se queda con los últimos turnos', () => {
    const turns = Array.from({ length: MAX_HISTORY_TURNS + 3 }, (_, index) => ({
      question: `pregunta-${index}`,
      answer: 'x'.repeat(MAX_HISTORY_ANSWER_CHARS + 500),
    }));

    const block = conversationContextBlock(turns);

    expect(block).not.toContain('pregunta-0');
    expect(block).toContain(`pregunta-${MAX_HISTORY_TURNS + 2}`);
    expect(block).not.toContain('x'.repeat(MAX_HISTORY_ANSWER_CHARS + 1));
  });

  it('compone la consulta de recuperación con las preguntas previas y la actual', () => {
    const query = contextualRetrievalQuery(
      [
        { question: '¿Cuántos días exige el artículo 9?', answer: 'Más de 183 días.' },
        { question: '¿Y si me ausento?', answer: '' },
      ],
      'dame un ejemplo de lo anterior'
    );

    expect(query).toContain('artículo 9');
    expect(query).toContain('¿Y si me ausento?');
    expect(query).toContain('dame un ejemplo de lo anterior');
  });

  it('devuelve la pregunta intacta cuando no hay historial', () => {
    expect(contextualRetrievalQuery([], '¿Qué pruebas admite el tribunal?')).toBe(
      '¿Qué pruebas admite el tribunal?'
    );
  });
});
