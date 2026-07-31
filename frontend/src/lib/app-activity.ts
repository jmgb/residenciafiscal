/**
 * Detecta si hay algo que una recarga automática destruiría.
 *
 * Lo usa el guardián de versión para decidir entre recargar en silencio o
 * limitarse a avisar. Son dos cosas: una respuesta que todavía está llegando
 * —el generador que la alimenta no sobrevive a la recarga— y una pregunta a
 * medio escribir, que vive solo en el estado local del composer.
 */
import { useConversations } from '@/stores/useConversations';

function isEditableElement(element: Element | null): boolean {
  if (!element) return false;
  if (element instanceof HTMLTextAreaElement) return true;
  if (element instanceof HTMLInputElement) return true;
  // Comparación estricta: `isContentEditable` no está implementado en todos los
  // entornos y devolver `undefined` haría que la función mintiera con un valor
  // que no es booleano.
  return element instanceof HTMLElement && element.isContentEditable === true;
}

export function hasWorkInProgress(): boolean {
  const streaming = useConversations
    .getState()
    .conversations.some((conversation) =>
      conversation.messages.some(
        (message) =>
          message.isStreaming || message.answers?.some((answer) => answer.isStreaming === true)
      )
    );
  if (streaming) return true;

  return isEditableElement(document.activeElement);
}
