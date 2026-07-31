import { Send, Square } from 'lucide-react';
import { type KeyboardEvent, useRef, useState } from 'react';
import { Button } from '@/shared/components/ui/button';

const MAX_LENGTH = 500;
const TEXTAREA_MAX_HEIGHT_PX = 160;

interface ChatComposerProps {
  onSend: (content: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  placeholder?: string;
}

export function ChatComposer({
  onSend,
  onStop,
  isStreaming,
  placeholder = 'Escribe tu consulta sobre residencia fiscal…',
}: ChatComposerProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const trimmedLength = text.trim().length;
  const isOverMaxLength = trimmedLength > MAX_LENGTH;
  const showCharCount = trimmedLength > MAX_LENGTH * 0.8;
  const canSend = trimmedLength > 0 && !isStreaming && !isOverMaxLength;

  const resetHeight = () => {
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleSubmit = () => {
    if (!canSend) return;
    const message = text.trim();
    setText('');
    resetHeight();
    onSend(message);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className='shrink-0 bg-canvas px-4 pb-8 pt-3'>
      {/* El composer flota como tarjeta blanca sobre el lienzo: el contraste de
          fondo sustituye al borde superior que antes lo separaba del hilo. El
          hueco inferior lo despega del borde del viewport en vez de dejarlo
          pegado abajo. */}
      <div className='mx-auto flex w-full max-w-3xl items-end gap-2 rounded-2xl border border-border bg-card p-3 shadow-md focus-within:ring-2 focus-within:ring-ring'>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            const el = event.target;
            el.style.height = 'auto';
            el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_HEIGHT_PX)}px`;
          }}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder={placeholder}
          aria-label='Consulta'
          // El padding vertical simétrico centra la primera línea dentro de la
          // caja alta; `min-h-14` es solo el suelo, no fija el alto.
          className='max-h-40 min-h-14 flex-1 resize-none bg-transparent px-3 py-4 text-base leading-relaxed outline-none placeholder:text-muted-foreground'
        />
        {isStreaming ? (
          <Button
            type='button'
            variant='outline'
            size='icon'
            onClick={onStop}
            className='h-11 w-11'
            aria-label='Detener respuesta'
          >
            <Square className='h-5 w-5' aria-hidden='true' />
          </Button>
        ) : (
          <Button
            type='button'
            size='icon'
            onClick={handleSubmit}
            disabled={!canSend}
            className='h-11 w-11'
            aria-label='Enviar consulta'
          >
            <Send className='h-5 w-5' aria-hidden='true' />
          </Button>
        )}
      </div>
      {showCharCount && (
        <p
          className={`mx-auto mt-1 w-full max-w-3xl text-right text-xs ${
            isOverMaxLength ? 'text-destructive' : 'text-muted-foreground'
          }`}
        >
          {trimmedLength} / {MAX_LENGTH}
        </p>
      )}
    </div>
  );
}
