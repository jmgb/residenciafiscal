import type { ChatAnswerStatus } from '@/types/chat';

// `completa` no se rotula: el chat no puede certificar que una respuesta agote
// la cuestión sobre un corpus sin revisión jurídica humana. Solo se avisa de los
// límites, nunca de su ausencia.
const ANSWER_STATUS_LABEL = {
  parcial: 'Cobertura parcial',
  pregunta: 'Necesita más datos',
  abstención: 'Sin cobertura suficiente',
  error: 'Error aislado',
} as const;

export const answerStatusLabel = (status: ChatAnswerStatus | undefined): string | null =>
  status === undefined || status === 'completa' ? null : ANSWER_STATUS_LABEL[status];
