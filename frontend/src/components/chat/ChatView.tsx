import { Search } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router';
import { trackEvent } from '@/components/layout/PostHogAnalytics';
import { type CountryRoute, SPAIN_ROUTE } from '@/data/countryRoutes';
import {
  type ChatSessionMessageUsage,
  consumeChatSessionMessage,
} from '@/lib/chat-session-message-limit';
import { useEditorialChatAnswer } from '@/lib/useEditorialChatAnswer';
import { usePageTitle } from '@/lib/usePageTitle';
import { useConversations } from '@/stores/useConversations';
import type {
  ChatEngine,
  ChatMessage,
  ChatSource,
  ChatStrategyAnswer,
  ChatStrategyId,
} from '@/types/chat';
import { ChatBubble } from './ChatBubble';
import { ChatComposer } from './ChatComposer';
import { ChatSafetyBanner } from './ChatSafetyBanner';
import { ChatWelcome } from './ChatWelcome';
import { TypingIndicator } from './TypingIndicator';
import { useDeepResearch } from './useDeepResearch';

function newMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `msg-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

/**
 * Margen (px) dentro del cual se considera que el usuario sigue "pegado al fondo".
 * Absorbe el redondeo subpíxel del navegador y los últimos píxeles de inercia.
 */
const STICK_TO_BOTTOM_THRESHOLD_PX = 48;
const isDeepResearchUiEnabled = () => import.meta.env.VITE_DEEP_RESEARCH_ENABLED === 'true';

/**
 * ¿Es el placeholder del asistente aún sin nada que enseñar? Mientras lo sea,
 * su burbuja no se pinta: en su lugar se muestra el `TypingIndicator`.
 */
function isEmptyStreamingPlaceholder(message: ChatMessage): boolean {
  return (
    message.role === 'assistant' &&
    message.isStreaming === true &&
    !message.content &&
    !message.answers?.length
  );
}

export interface ChatViewProps {
  engine: ChatEngine;
  /**
   * Motor simulado activo. Con el stub NO se pinta ninguna banda de aviso: el
   * texto de cada respuesta simulada ya declara su naturaleza (`chat-engine.stub`),
   * y la banda jurídica se reserva para las respuestas reales.
   */
  isStub: boolean;
  /** Ruta canónica de la vista que contiene el chat. */
  canonicalPath?: string;
  /** País cuyo corpus debe utilizar el motor. */
  country?: CountryRoute;
}

/**
 * Contenedor de la conversación: orquesta store, motor de chat y UI.
 *
 * La conversación se crea de forma perezosa con el primer mensaje, para no
 * llenar el historial de conversaciones vacías cada vez que alguien abre `/`.
 */
export function ChatView({
  engine,
  isStub,
  canonicalPath = '/',
  country = SPAIN_ROUTE,
}: ChatViewProps) {
  const { pathname } = useLocation();
  // El título es el de la ruta de país, escrito en `countryRoutes.json`: es el
  // mismo que fija el prerender, y componerlo aquí haría divergir bot y SPA.
  // `/consulta` y `/c/:id` heredan el de España porque canonicalizan allí, pero
  // solo la URL canónica se indexa: un crawler con JavaScript no debe ver cómo
  // estas rutas deshacen el `noindex` de la shell.
  usePageTitle(country.title, canonicalPath, country.description, pathname === canonicalPath, true);
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const conversations = useConversations((state) => state.conversations);
  const createConversation = useConversations((state) => state.createConversation);
  const appendMessage = useConversations((state) => state.appendMessage);
  const updateMessage = useConversations((state) => state.updateMessage);

  const conversation = conversations.find((c) => c.id === conversationId);
  const messages = conversation?.messages ?? [];
  const showEditorialAnswer = useEditorialChatAnswer({
    conversationId,
    countryPath: country.path,
  });

  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionMessageLimit, setSessionMessageLimit] = useState<ChatSessionMessageUsage | null>(
    null
  );
  const abortRef = useRef<AbortController | null>(null);
  /**
   * Conversación DUEÑA del streaming en curso (`null` si no hay ninguno).
   * Es lo que permite distinguir "el usuario se ha ido a otra conversación" de
   * "acabamos de navegar de `/` a `/c/:id` por el primer mensaje".
   */
  const streamOwnerRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  /** ¿El usuario está al final del hilo? Si ha subido a leer, no lo arrastramos. */
  const isPinnedToBottomRef = useRef(true);

  // Cancela cualquier streaming en curso al desmontar.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
      streamOwnerRef.current = null;
    };
  }, []);

  // Cancela el streaming al cambiar a OTRA conversación: si no, la respuesta de la
  // anterior sigue viva y deja el composer de la nueva bloqueado en "Detener respuesta".
  //
  // Depender de `conversationId` a secas no sirve: el primer envío desde `/` navega a
  // `/c/:id` justo después de arrancar el stream y este efecto abortaría su propia
  // respuesta. Por eso se compara con la conversación dueña del stream.
  useEffect(() => {
    const owner = streamOwnerRef.current;
    if (owner === null || owner === conversationId) return;
    abortRef.current?.abort();
    abortRef.current = null;
    streamOwnerRef.current = null;
    setIsStreaming(false);
  }, [conversationId]);

  // Una URL antigua (o un localStorage limpiado) puede apuntar a una conversación que ya
  // no existe. Sin esto `appendMessage` es un no-op silencioso y el usuario escribe al
  // vacío: volvemos a `/`, donde el primer mensaje crea una conversación nueva.
  const isMissingConversation = conversationId !== undefined && conversation === undefined;
  useEffect(() => {
    if (isMissingConversation) navigate('/', { replace: true });
  }, [isMissingConversation, navigate]);

  const handleScroll = useCallback(() => {
    const container = scrollRef.current;
    if (!container) return;
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    isPinnedToBottomRef.current = distanceToBottom <= STICK_TO_BOTTOM_THRESHOLD_PX;
  }, []);

  const lastMessage = messages.at(-1);
  const {
    activeDeepResearch,
    deepResearchJob,
    cancelDeepResearch: handleCancelDeepResearch,
    startDeepResearch: handleStartDeepResearch,
  } = useDeepResearch({
    conversationId,
    countryPath: country.path,
    createMessageId: newMessageId,
    isStreaming,
    messages,
  });
  // El contenido del último mensaje es lo único que cambia mientras llegan tokens:
  // sin él el autoscroll se quedaría congelado en la respuesta larga en curso.
  const lastMessageContent = `${lastMessage?.content ?? ''}${
    lastMessage?.answers?.map((answer) => answer.content).join('') ?? ''
  }`;

  // `messages.length` y `lastMessageContent` son las dependencias DISPARADORAS del
  // autoscroll aunque su valor no se lea dentro del efecto: quitarlas dejaría el scroll
  // pegado arriba tras el primer mensaje y congelado durante el streaming.
  // biome-ignore lint/correctness/useExhaustiveDependencies: disparadores intencionados.
  useEffect(() => {
    if (!isPinnedToBottomRef.current) return;
    const container = scrollRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  }, [messages.length, lastMessageContent]);

  const completedAnswerId =
    lastMessage?.role === 'assistant' &&
    lastMessage.isStreaming !== true &&
    !lastMessage.answers?.some((answer) => answer.isStreaming)
      ? lastMessage.id
      : null;

  // Al completarse cualquier respuesta, editorial o generada, empieza su lectura arriba.
  useEffect(() => {
    if (!completedAnswerId) return;
    const container = scrollRef.current;
    if (!container) return;
    const answer = Array.from(
      container.querySelectorAll<HTMLElement>('[data-chat-message-id]')
    ).find((element) => element.dataset.chatMessageId === completedAnswerId);
    if (!answer) return;

    const answerTop =
      container.scrollTop +
      answer.getBoundingClientRect().top -
      container.getBoundingClientRect().top;
    container.scrollTop = Math.max(0, answerTop);
    isPinnedToBottomRef.current = false;
  }, [completedAnswerId]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    streamOwnerRef.current = null;
    setIsStreaming(false);
  }, []);

  const handleEditorialPrompt = useCallback(
    (answer: Parameters<typeof showEditorialAnswer>[0]) => {
      if (isStreaming) return;
      isPinnedToBottomRef.current = true;
      const controller = new AbortController();
      const run = showEditorialAnswer(answer, controller.signal);
      abortRef.current = controller;
      streamOwnerRef.current = run.conversationId;
      setIsStreaming(true);

      void run.completion.finally(() => {
        if (abortRef.current !== controller) return;
        abortRef.current = null;
        streamOwnerRef.current = null;
        setIsStreaming(false);
      });
    },
    [isStreaming, showEditorialAnswer]
  );

  const handleSend = useCallback(
    async (content: string) => {
      const sessionUsage = consumeChatSessionMessage();
      if (!sessionUsage.allowed) {
        setSessionMessageLimit(sessionUsage);
        return;
      }
      setSessionMessageLimit(sessionUsage.count >= sessionUsage.limit ? sessionUsage : null);

      // Si la URL apunta a una conversación inexistente se crea una nueva en vez de
      // escribir en el vacío (el efecto de arriba ya habrá redirigido en la práctica).
      const existing = conversationId
        ? useConversations.getState().getConversation(conversationId)
        : undefined;
      const targetId = existing?.id ?? createConversation();
      if (targetId !== conversationId) navigate(`/c/${targetId}`, { replace: true });

      // Enviar es una acción explícita: devuelve al usuario al final del hilo.
      isPinnedToBottomRef.current = true;

      const now = new Date().toISOString();
      const userMessage: ChatMessage = {
        id: newMessageId(),
        role: 'user',
        content,
        createdAt: now,
      };
      appendMessage(targetId, userMessage);

      const assistantId = newMessageId();
      appendMessage(targetId, {
        id: assistantId,
        role: 'assistant',
        content: '',
        createdAt: new Date().toISOString(),
        isStreaming: true,
      });

      const controller = new AbortController();
      abortRef.current = controller;
      streamOwnerRef.current = targetId;
      setIsStreaming(true);

      const history = [
        ...(useConversations.getState().getConversation(targetId)?.messages ?? []),
      ].filter((message) => message.id !== assistantId);

      let buffer = '';
      let sources: ChatSource[] | undefined;
      let answers: ChatStrategyAnswer[] | undefined;
      let comparisonId: string | undefined;
      let fallo: string | undefined;

      const updateAnswers = () => {
        updateMessage(targetId, assistantId, { answers: answers ? [...answers] : undefined });
      };

      const answerFor = (strategy: ChatStrategyId): ChatStrategyAnswer | undefined =>
        answers?.find((answer) => answer.strategy === strategy);

      // La analítica de producto nunca recibe el texto: solo volumen,
      // jurisdicción y resultado. La persistencia privada del turno se realiza
      // dentro de la Function, no mediante el SDK de analítica del navegador.
      trackEvent('consulta_enviada', {
        pais: country.path,
        es_primera_de_la_conversacion: history.length <= 1,
      });

      try {
        for await (const chunk of engine.askQuestion(history, controller.signal, {
          countryPath: country.path,
          countryName: country.name,
          conversationId: targetId,
        })) {
          if (chunk.type === 'answer_start') {
            answers ??= [];
            answers.push({
              strategy: chunk.strategy,
              content: '',
              sources: [],
              limits: [],
              isStreaming: true,
            });
            updateAnswers();
          } else if (chunk.type === 'token') {
            if (chunk.strategy) {
              const answer = answerFor(chunk.strategy);
              if (answer) {
                answer.content += chunk.text;
                updateAnswers();
              }
            } else {
              buffer += chunk.text;
              updateMessage(targetId, assistantId, { content: buffer });
            }
          } else if (chunk.type === 'sources') {
            sources = chunk.sources;
          } else if (chunk.type === 'strategy_sources') {
            const answer = answerFor(chunk.strategy);
            if (answer) {
              answer.sources = chunk.sources;
              updateAnswers();
            }
          } else if (chunk.type === 'answer_done') {
            const answer = answerFor(chunk.strategy);
            if (answer) {
              answer.status = chunk.status;
              answer.claims = chunk.claims ?? [];
              answer.limits = chunk.limits;
              answer.cost = chunk.cost;
              answer.model = chunk.model;
              answer.latencyMs = chunk.latencyMs;
              answer.isStreaming = false;
              updateAnswers();
            }
          } else if (chunk.type === 'done') {
            comparisonId = chunk.requestId;
          }
        }
      } catch {
        if (!controller.signal.aborted) {
          const errorMessage = 'No se ha podido completar la consulta. Inténtalo de nuevo.';
          if (answers) {
            const strategies: ChatStrategyId[] = ['current_structured', 'gemini_file_search'];
            answers = strategies.map((strategy) => {
              const existing = answerFor(strategy);
              if (existing?.status) return existing;
              return {
                strategy,
                status: 'error',
                content: existing?.content || 'No se ha podido completar esta estrategia.',
                sources: existing?.sources ?? [],
                limits: [errorMessage],
                isStreaming: false,
              };
            });
          } else {
            buffer = buffer ? `${buffer}\n\n_${errorMessage}_` : errorMessage;
          }
          fallo = 'error_motor';
        }
      } finally {
        if (controller.signal.aborted && !buffer && !answers) buffer = 'Respuesta detenida.';
        if (answers) {
          answers = answers.map((answer) => ({ ...answer, isStreaming: false }));
        }
        updateMessage(targetId, assistantId, {
          content: buffer,
          sources,
          answers,
          comparisonId,
          isStreaming: false,
        });
        // El nº de fuentes distingue una respuesta apoyada en el corpus de una
        // respuesta genérica: es la señal de calidad que interesa vigilar.
        trackEvent('consulta_respondida', {
          pais: country.path,
          resultado: controller.signal.aborted ? 'detenida' : (fallo ?? 'ok'),
          num_fuentes:
            sources?.length ??
            answers?.reduce((total, answer) => total + answer.sources.length, 0) ??
            0,
          longitud_respuesta:
            buffer.length +
            (answers?.reduce((total, answer) => total + answer.content.length, 0) ?? 0),
        });
        // Solo se libera el composer si este sigue siendo el stream vigente: si el usuario
        // ya paró, cambió de conversación o lanzó otra consulta, no es nuestro turno.
        if (abortRef.current === controller) {
          abortRef.current = null;
          streamOwnerRef.current = null;
          setIsStreaming(false);
        }
      }
    },
    [appendMessage, conversationId, country, createConversation, engine, navigate, updateMessage]
  );

  const hasMessages = messages.length > 0;
  const showTypingIndicator =
    isStreaming && lastMessage !== undefined && isEmptyStreamingPlaceholder(lastMessage);

  return (
    <div className='flex min-h-0 flex-1 flex-col'>
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        data-testid='chat-scroll'
        className='flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4'
      >
        {!isStub && <ChatSafetyBanner />}

        {hasMessages ? (
          <div
            className='mx-auto flex w-full max-w-3xl flex-col gap-3'
            role='log'
            aria-label='Mensajes de la conversación'
            aria-live='polite'
            aria-relevant='additions'
          >
            {messages
              .filter((message) => !isEmptyStreamingPlaceholder(message))
              .map((message) => (
                <ChatBubble
                  key={message.id}
                  message={message}
                  hideComparisonVote={Boolean(
                    message.comparisonId &&
                      message.comparisonId === deepResearchJob?.comparisonId &&
                      (deepResearchJob.status === 'queued' ||
                        deepResearchJob.status === 'running' ||
                        deepResearchJob.status === 'completed')
                  )}
                  onCancelDeepResearch={handleCancelDeepResearch}
                />
              ))}
            {showTypingIndicator && <TypingIndicator />}
          </div>
        ) : (
          <ChatWelcome onSelectPrompt={handleEditorialPrompt} />
        )}
      </div>

      {sessionMessageLimit && (
        <p
          role='status'
          aria-label='Límite de mensajes de sesión'
          className='mx-auto w-full max-w-3xl px-4 pb-2 text-center text-xs text-muted-foreground'
        >
          Has alcanzado el límite de {sessionMessageLimit.limit}{' '}
          {sessionMessageLimit.limit === 1 ? 'mensaje' : 'mensajes'} de esta sesión. Podrás volver a
          consultar cuando se renueve la ventana de 24 horas.
        </p>
      )}
      {isDeepResearchUiEnabled() && hasMessages && !isStreaming && !activeDeepResearch && (
        <div className='mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 pb-1'>
          <p className='text-xs text-muted-foreground'>
            ¿Necesitas contrastar la respuesta con más fuentes del corpus?
          </p>
          <button
            type='button'
            onClick={() => void handleStartDeepResearch()}
            className='inline-flex shrink-0 items-center gap-2 rounded-lg border border-primary/30 bg-card px-3 py-2 text-xs font-semibold text-primary transition-colors hover:bg-primary-50 control-focus'
          >
            <Search className='h-4 w-4' aria-hidden='true' />
            Iniciar investigación profunda
          </button>
        </div>
      )}
      <ChatComposer
        onSend={handleSend}
        onStop={handleStop}
        isStreaming={isStreaming}
        disabled={sessionMessageLimit !== null}
      />
    </div>
  );
}
