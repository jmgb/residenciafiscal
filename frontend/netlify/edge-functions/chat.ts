/**
 * Fachada same-origin del chat.
 *
 * Netlify no contiene lógica jurídica ni credenciales de proveedores: limita
 * tráfico, autentica la llamada interna y transmite el stream del servicio
 * Python. No registra ni inspecciona el texto fiscal del usuario.
 */
import type { Config } from '@netlify/edge-functions';

const MAX_REQUEST_BYTES = 200_000;

const jsonError = (status: number, message: string, headers?: HeadersInit) =>
  Response.json(
    { error: message },
    {
      status,
      headers: { 'cache-control': 'no-store', ...headers },
    }
  );

export default async function chatProxy(request: Request): Promise<Response> {
  if (request.method !== 'POST') {
    return jsonError(405, 'Método no permitido', { allow: 'POST' });
  }

  const backendUrl = Netlify.env.get('CHAT_BACKEND_URL')?.trim();
  const proxySecret = Netlify.env.get('CHAT_PROXY_SECRET')?.trim();
  if (!backendUrl || !proxySecret) {
    return jsonError(503, 'Chat no configurado');
  }
  let chatEndpoint: URL;
  try {
    chatEndpoint = new URL('/chat', backendUrl);
  } catch {
    return jsonError(503, 'Chat no configurado');
  }
  if (chatEndpoint.protocol !== 'https:') {
    return jsonError(503, 'Chat no configurado');
  }

  const declaredLength = Number(request.headers.get('content-length'));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    return jsonError(413, 'Petición demasiado grande');
  }

  let body: string;
  try {
    body = await request.text();
  } catch {
    return jsonError(400, 'Petición inválida');
  }
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) {
    return jsonError(413, 'Petición demasiado grande');
  }

  let upstream: Response;
  try {
    upstream = await fetch(chatEndpoint.toString(), {
      method: 'POST',
      headers: {
        accept: 'text/event-stream',
        'content-type': 'application/json',
        'x-chat-proxy-secret': proxySecret,
      },
      body,
      redirect: 'error',
      signal: request.signal,
    });
  } catch {
    return jsonError(502, 'No se ha podido contactar con el motor');
  }

  const headers = new Headers({ 'cache-control': 'no-store' });
  const contentType = upstream.headers.get('content-type');
  const protocol = upstream.headers.get('x-chat-protocol');
  if (contentType) headers.set('content-type', contentType);
  if (protocol) headers.set('x-chat-protocol', protocol);

  return new Response(upstream.body, {
    status: upstream.status,
    headers,
  });
}

export const config: Config = {
  path: '/api/chat',
  rateLimit: {
    aggregateBy: ['ip', 'domain'],
    windowSize: 60,
    windowLimit: 5,
  },
};
