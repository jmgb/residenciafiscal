import { AlertTriangle } from 'lucide-react';

export const ChatSafetyBanner = () => (
  <div
    role='status'
    aria-label='Aviso de investigación jurídica'
    className='mx-auto mb-3 flex w-full max-w-3xl items-start gap-2 rounded-lg border border-accent-500/40 bg-accent px-3 py-2 text-xs leading-relaxed text-accent-foreground'
  >
    <AlertTriangle className='mt-0.5 h-4 w-4 shrink-0' aria-hidden='true' />
    <p>
      <strong>Aviso:</strong> respuestas experimentales, no constituye asesoramiento jurídico.
      <a className='ml-1 underline' href='/privacidad'>
        Privacidad
      </a>
      .
    </p>
  </div>
);
