import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { serializeComparison } from '../netlify/functions/chat/chat';
import type { ComparisonReport } from '../netlify/functions/chat/contracts';

/**
 * Mismo fichero que consume `tests/test_chat_protocol_fixtures.py`. Los dos
 * serializadores tienen que producir el mismo SSE byte a byte: es la única
 * forma de que portar el dominio a Python no cambie el contrato del navegador
 * sin que nadie se entere.
 */
const fixtures = JSON.parse(
  readFileSync(resolve(__dirname, '../../schemas/chat-protocol-2.fixtures.json'), 'utf-8')
) as {
  cases: { name: string; report: ComparisonReport; expected_sse: string }[];
};

describe('contrato SSE compartido del protocolo 2', () => {
  for (const testCase of fixtures.cases) {
    it(testCase.name, () => {
      expect(serializeComparison(testCase.report)).toBe(testCase.expected_sse);
    });
  }
});
