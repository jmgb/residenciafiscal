import { AlertTriangle } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router';
import { trackEvent } from '@/components/layout/PostHogAnalytics';
import { type CountryRoute, SPAIN_ROUTE } from '@/data/countryRoutes';
import {
  type ChatSessionMessageUsage,
  consumeChatSessionMessage,
} from '@/lib/chat-session-message-limit';
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
import { ChatWelcome } from './ChatWelcome';

function newMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `msg-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

/**
 * Margen (px) dentro del cual se considera que el usuario sigue "pegado al fondo".
 * Absorbe el redondeo subpíxel del navegador y los últimos píxeles de inercia.
 */
const STICK_TO_BOTTOM_THRESHOLD_PX = 48;

function TypingIndicator() {
  return (
    <div className='flex justify-start' role='status' aria-label='Buscando en las sentencias'>
      <div className='flex items-center gap-1.5 rounded-xl rounded-tl-none border border-border bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm'>
        <span>Buscando en las sentencias</span>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className='h-[7px] w-[7px] animate-bounce rounded-full bg-muted-foreground/60'
            style={{ animationDelay: `${i * 0.2}s`, animationDuration: '1.4s' }}
          />
        ))}
      </div>
    </div>
  );
}

function SafetyBanner() {
  return (
    <div
      role='status'
      aria-label='Aviso de investigación jurídica'
      className='mx-auto mb-3 flex w-full max-w-3xl items-start gap-2 rounded-lg border border-accent-500/40 bg-accent px-3 py-2 text-xs leading-relaxed text-accent-foreground'
    >
      <AlertTriangle className='mt-0.5 h-4 w-4 shrink-0' aria-hidden='true' />
      <p>
        <strong>Aviso:</strong> esta herramienta sirve para investigación y no constituye
        asesoramiento jurídico. Recomendamos siempre consultar a un profesional antes de tomar
        decisiones.
        <a className='ml-1 underline' href='/privacidad'>
          Privacidad
        </a>
        .
      </p>
    </div>
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

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    streamOwnerRef.current = null;
    setIsStreaming(false);
  }, []);

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
              answer.limits = chunk.limits;
              answer.cost = chunk.cost;
              answer.model = chunk.model;
              answer.latencyMs = chunk.latencyMs;
              answer.isStreaming = false;
              updateAnswers();
            }
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
    isStreaming && lastMessage?.isStreaming && !lastMessage.content && !lastMessage.answers?.length;

  return (
    <div className='flex min-h-0 flex-1 flex-col'>
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        data-testid='chat-scroll'
        className='flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4'
      >
        {!isStub && <SafetyBanner />}

        {hasMessages ? (
          <div
            className='mx-auto flex w-full max-w-3xl flex-col gap-3'
            role='log'
            aria-label='Mensajes de la conversación'
            aria-live='polite'
            aria-relevant='additions'
          >
            {messages.map((message) => (
              <ChatBubble key={message.id} message={message} />
            ))}
            {showTypingIndicator && <TypingIndicator />}
          </div>
        ) : (
          <ChatWelcome onSelectPrompt={handleSend} legalReferences={country.legalReferences} />
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
      <ChatComposer
        onSend={handleSend}
        onStop={handleStop}
        isStreaming={isStreaming}
        disabled={sessionMessageLimit !== null}
      />
    </div>
  );
}
