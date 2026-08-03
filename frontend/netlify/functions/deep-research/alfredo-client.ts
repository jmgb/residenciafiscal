import type {
  DeepResearchAlfredoPayload,
  DeepResearchEnvironment,
  DeepResearchSubmitResult,
} from './contracts';

const encoder = new TextEncoder();

const hex = (bytes: ArrayBuffer): string =>
  [...new Uint8Array(bytes)].map((value) => value.toString(16).padStart(2, '0')).join('');

export async function hmacSha256(secret: string, value: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  return hex(await crypto.subtle.sign('HMAC', key, encoder.encode(value)));
}

export async function verifyAlfredoSignature(
  secret: string,
  timestamp: string | null,
  signature: string | null,
  body: string,
  nowMs = Date.now()
): Promise<boolean> {
  if (!timestamp || !signature || !/^\d+$/.test(timestamp)) return false;
  const seconds = Number(timestamp);
  if (!Number.isSafeInteger(seconds) || Math.abs(nowMs / 1000 - seconds) > 300) return false;
  const expected = await hmacSha256(secret, `${timestamp}.${body}`);
  if (expected.length !== signature.length) return false;
  let mismatch = 0;
  for (let index = 0; index < expected.length; index += 1) {
    mismatch |= expected.charCodeAt(index) ^ signature.charCodeAt(index);
  }
  return mismatch === 0;
}

export async function submitDeepResearchJob(
  environment: DeepResearchEnvironment,
  payload: DeepResearchAlfredoPayload,
  fetchImpl: typeof fetch = fetch
): Promise<DeepResearchSubmitResult> {
  const body = JSON.stringify(payload);
  const timestamp = String(Math.floor(Date.now() / 1000));
  const signature = await hmacSha256(environment.alfredoHmacSecret, `${timestamp}.${body}`);
  const response = await fetchImpl(environment.alfredoJobsUrl, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'X-VA-Timestamp': timestamp,
      'X-VA-Signature': signature,
    },
    body,
  });
  if (!response.ok) throw new Error('Alfredo no ha aceptado la investigación');
  const result = (await response.json()) as { job_id?: unknown; status?: unknown };
  if (typeof result.job_id !== 'string' || typeof result.status !== 'string') {
    throw new Error('respuesta inválida de Alfredo');
  }
  return { jobId: result.job_id, status: result.status };
}

export async function cancelDeepResearchJob(
  environment: DeepResearchEnvironment,
  jobId: string,
  fetchImpl: typeof fetch = fetch
): Promise<boolean> {
  const url = `${environment.alfredoJobsUrl.replace(/\/$/, '')}/${encodeURIComponent(jobId)}/cancel`;
  const timestamp = String(Math.floor(Date.now() / 1000));
  const body = '';
  const signature = await hmacSha256(environment.alfredoHmacSecret, `${timestamp}.${body}`);
  const response = await fetchImpl(url, {
    method: 'POST',
    headers: {
      'X-VA-Timestamp': timestamp,
      'X-VA-Signature': signature,
    },
  });
  return response.ok;
}
