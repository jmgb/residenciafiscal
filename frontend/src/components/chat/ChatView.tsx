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
  const scrollRef = useRef<HTMLDivElement>(null);

  // Cancela cualquier streaming en curso al desmontar o al cambiar de conversación.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  // `messages.length` es la dependencia DISPARADORA del autoscroll aunque su valor no se
  // lea dentro del efecto: quitarla dejaría el scroll pegado arriba tras el primer mensaje.
  // biome-ignore lint/correctness/useExhaustiveDependencies: disparador intencionado.
  useEffect(() => {
    const container = scrollRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  }, [messages.length]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

  const handleSend = useCallback(
    async (content: string) => {
      const targetId = conversationId ?? createConversation();
      if (!conversationId) navigate(`/c/${targetId}`, { replace: true });

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
        if (abortRef.current === controller) abortRef.current = null;
        setIsStreaming(false);
      }
    },
    [appendMessage, conversationId, createConversation, engine, navigate, updateMessage]
  );

  const hasMessages = messages.length > 0;
  const lastMessage = messages.at(-1);
  const showTypingIndicator = isStreaming && lastMessage?.isStreaming && !lastMessage.content;

  return (
    <div className='flex min-h-0 flex-1 flex-col'>
      <div ref={scrollRef} className='flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4'>
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
