import { describe, expect, it } from 'vitest';
import {
  ChatDiagnosticError,
  diagnosticFromError,
  supabaseDiagnostic,
} from '../netlify/functions/chat/chat-diagnostics';

describe('diagnósticos técnicos del chat', () => {
  it('clasifica una RPC de Supabase ausente sin conservar el mensaje bruto', () => {
    const error = new ChatDiagnosticError(
      'Supabase no disponible',
      supabaseDiagnostic('complete_chat_request', {
        code: 'PGRST202',
        message: 'Could not find the function public.complete_chat_request with secret prompt',
      })
    );

    expect(diagnosticFromError(error)).toEqual({
      dependency: 'supabase',
      operation: 'complete_chat_request',
      kind: 'rpc_not_found',
      code: 'PGRST202',
      retryable: false,
    });
    expect(JSON.stringify(diagnosticFromError(error))).not.toContain('secret prompt');
  });

  it('conserva el diagnóstico seguro de una excepción técnica normal', () => {
    const error = new ChatDiagnosticError('Proveedor no disponible', {
      dependency: 'openai',
      operation: 'responses.create',
      kind: 'provider_error',
      code: 'rate_limit_exceeded',
      status: 429,
      retryable: true,
    });

    expect(diagnosticFromError(error)).toEqual({
      dependency: 'openai',
      operation: 'responses.create',
      kind: 'provider_error',
      code: 'rate_limit_exceeded',
      status: 429,
      retryable: true,
    });
  });
});
