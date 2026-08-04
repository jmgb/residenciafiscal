/**
 * Fachada same-origin firmada para la migración Edge → FastAPI.
 *
 * Este módulo no contiene lógica jurídica, cuota autoritativa ni credenciales
 * de proveedores. Netlify solo descarta abuso evidente, firma el salto interno
 * y transmite el SSE. Se conserva como prototipo hasta superar F0/F5.
 */
import type { Config, Context } from '@netlify/edge-functions';

const MAX_REQUEST_BYTES = 200_000;
const SIGNATURE_VERSION = 'v1';

const jsonError = (status: number, message: string, headers?: HeadersInit) =>
  Response.json(
    { error: message },
    { status, headers: { 'cache-control': 'no-store', ...headers } }
  );

const hex = (bytes: ArrayBuffer): string =>
  [...new Uint8Array(bytes)].map((value) => value.toString(16).padStart(2, '0')).join('');

const digestBody = async (body: string): Promise<string> =>
  hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(body)));

const sign = async (
  secret: string,
  timestamp: string,
  requestId: string,
  bodyDigest: string
): Promise<string> => {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const payload = `chat-proxy/${SIGNATURE_VERSION}\n${timestamp}\n${requestId}\n${bodyDigest}`;
  return `${SIGNATURE_VERSION}=${hex(
    await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload))
  )}`;
};

/**
 * Reparto estable del canary. La misma conversación cae siempre del mismo
 * lado, así que un usuario no ve dos runtimes distintos dentro de un hilo.
 */
const bucketOf = (value: string): number => {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash % 100;
};

const backendPercent = (): number => {
  const raw = Number(Netlify.env.get('CHAT_BACKEND_PERCENT')?.trim() ?? '0');
  if (!Number.isFinite(raw)) return 0;
  return Math.min(100, Math.max(0, Math.trunc(raw)));
};

const conversationOf = (body: string): string => {
  try {
    const parsed = JSON.parse(body) as { conversation_id?: unknown };
    return typeof parsed.conversation_id === 'string' ? parsed.conversation_id : '';
  } catch {
    return '';
  }
};

export default async function chatProxy(request: Request, context: Context): Promise<Response> {
  if (request.method !== 'POST') {
    return jsonError(405, 'Método no permitido', { allow: 'POST' });
  }
  if (!request.headers.get('content-type')?.toLowerCase().includes('application/json')) {
    return jsonError(415, 'Tipo de contenido no permitido');
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

  const percent = backendPercent();
  const routed = percent > 0 && bucketOf(conversationOf(body) || crypto.randomUUID()) < percent;
  if (!routed) {
    // Palanca de rollback: con `CHAT_BACKEND_PERCENT=0` todo el tráfico vuelve
    // a la Function TypeScript sin tocar DNS ni redeplegar el backend.
    return context.next(
      new Request(request.url, { method: 'POST', headers: request.headers, body })
    );
  }

  const backendUrl = Netlify.env.get('CHAT_BACKEND_URL')?.trim();
  const proxySecret = Netlify.env.get('CHAT_HMAC_SECRET')?.trim();
  if (!backendUrl || !proxySecret) return jsonError(503, 'Chat no configurado');

  let chatEndpoint: URL;
  try {
    chatEndpoint = new URL('/chat', backendUrl);
  } catch {
    return jsonError(503, 'Chat no configurado');
  }
  if (chatEndpoint.protocol !== 'https:') return jsonError(503, 'Chat no configurado');

  const timestamp = Math.floor(Date.now() / 1000).toString();
  const requestId = `chat-${crypto.randomUUID()}`;
  const bodyDigest = await digestBody(body);
  const clientKey = await digestBody(
    request.headers.get('x-nf-client-connection-ip') ??
      request.headers.get('x-forwarded-for') ??
      'unknown'
  );
  const signature = await sign(proxySecret, timestamp, requestId, bodyDigest);

  let upstream: Response;
  try {
    upstream = await fetch(chatEndpoint.toString(), {
      method: 'POST',
      headers: {
        accept: 'text/event-stream',
        'content-type': 'application/json',
        'x-chat-timestamp': timestamp,
        'x-chat-request-id': requestId,
        'x-chat-body-sha256': bodyDigest,
        'x-chat-signature': signature,
        'x-chat-client-key': clientKey,
      },
      body,
      redirect: 'error',
      signal: request.signal,
    });
  } catch {
    return jsonError(502, 'No se ha podido contactar con el motor');
  }

  const headers = new Headers({ 'cache-control': 'no-store' });
  for (const name of ['content-type', 'x-chat-protocol', 'retry-after']) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new Response(upstream.body, { status: upstream.status, headers });
}

/**
 * El descarte de abuso lo aplica la plataforma, con la misma ventana que la V1.
 * No se implementa un contador propio sobre Blobs: su compare-and-swap pierde
 * incrementos bajo concurrencia y daría una cuota con fugas. La cuota
 * autoritativa vive en FastAPI.
 */
export const config: Config = {
  path: '/api/chat',
  method: 'POST',
  rateLimit: {
    aggregateBy: ['ip', 'domain'],
    windowSize: 60,
    windowLimit: 5,
  },
};
