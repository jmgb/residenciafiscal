import { AlertTriangle } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useConversations } from '@/stores/useConversations';
import type { ChatEngine, ChatMessage, ChatSource } from '@/types/chat';
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

function StubBanner() {
  return (
    <div
      role='status'
      aria-label='Aviso: motor simulado'
      className='mx-auto mb-3 flex w-full max-w-3xl items-start gap-2 rounded-lg border border-accent-500/40 bg-accent px-3 py-2 text-xs leading-relaxed text-accent-foreground'
    >
      <AlertTriangle className='mt-0.5 h-4 w-4 shrink-0' aria-hidden='true' />
      <p>
        <strong>Demo:</strong> el motor de análisis todavía no está conectado. Las respuestas son
        simuladas y no constituyen asesoramiento jurídico. Las sentencias citadas sí son reales.
      </p>
    </div>
  );
}

export interface ChatViewProps {
  engine: ChatEngine;
  /** Muestra el aviso de contenido simulado. */
  isStub: boolean;
}

/**
 * Contenedor de la conversación: orquesta store, motor de chat y UI.
 *
 * La conversación se crea de forma perezosa con el primer mensaje, para no
 * llenar el historial de conversaciones vacías cada vez que alguien abre `/`.
 */
export function ChatView({ engine, isStub }: ChatViewProps) {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const conversations = useConversations((state) => state.conversations);
  const createConversation = useConversations((state) => state.createConversation);
  const appendMessage = useConversations((state) => state.appendMessage);
  const updateMessage = useConversations((state) => state.updateMessage);

  const conversation = conversations.find((c) => c.id === conversationId);
  const messages = conversation?.messages ?? [];

  const [isStreaming, setIsStreaming] = useState(false);
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
  const lastMessageContent = lastMessage?.content ?? '';

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

      try {
        for await (const chunk of engine.askQuestion(history, controller.signal)) {
          if (chunk.type === 'token') {
            buffer += chunk.text;
            updateMessage(targetId, assistantId, { content: buffer });
          } else if (chunk.type === 'sources') {
            sources = chunk.sources;
          }
        }
      } catch {
        buffer = buffer || 'No se ha podido completar la consulta. Inténtalo de nuevo.';
      } finally {
        updateMessage(targetId, assistantId, {
          content: buffer,
          sources,
          isStreaming: false,
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
    [appendMessage, conversationId, createConversation, engine, navigate, updateMessage]
  );

  const hasMessages = messages.length > 0;
  const showTypingIndicator = isStreaming && lastMessage?.isStreaming && !lastMessage.content;

  return (
    <div className='flex min-h-0 flex-1 flex-col'>
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        data-testid='chat-scroll'
        className='flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4'
      >
        {isStub && <StubBanner />}

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
          <ChatWelcome onSelectPrompt={handleSend} />
        )}
      </div>

      <ChatComposer onSend={handleSend} onStop={handleStop} isStreaming={isStreaming} />
    </div>
  );
}
