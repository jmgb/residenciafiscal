import answers from '@/data/editorialChatAnswers.json';
import type { EditorialChatAnswer } from '@/types/chat';

/**
 * Catálogo editorial. El dato vive en JSON —y no en este módulo— porque la
 * Netlify Function necesita exactamente el mismo texto para registrar el turno en
 * el ledger, y no puede importar código del frontend: solo artefactos de datos.
 */
export const EDITORIAL_CHAT_ANSWERS: readonly EditorialChatAnswer[] =
  answers as readonly EditorialChatAnswer[];
