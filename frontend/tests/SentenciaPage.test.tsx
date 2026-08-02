import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SentenciaPreloadContext } from '@/lib/sentencia-preload';
import { resetSentenciasCache } from '@/lib/sentencias';
import { SentenciaPage } from '@/pages/SentenciaPage';
import type { SentenciaPublica } from '@/types/sentencias';

const REVIEW = {
  legal: 'AGENT_REVIEWED',
  technical: 'VALIDATED',
  reviewedAt: '2026-07-29',
  reviewedBy: 'agent:codex',
};

const SENTENCIA: SentenciaPublica = {
  schemaVersion: 'residenciafiscal-public-judgment/1',
  jurisdiction: 'es',
  publicationState: 'internal_preview',
  judgment: {
    judgmentId: 'san-1386-2017',
    roj: 'SAN 1386/2017',
    ecli: 'ECLI:ES:AN:2017:1386',
    court: 'Audiencia Nacional',
    chamber: 'Sala de lo Contencioso-Administrativo, Sección Cuarta',
    decisionDate: '2017-03-29',
    taxYears: [2009],
    pageCount: 12,
    sourceFile: 'sentencias/SAN_1386_2017.pdf',
    sourceSha256: 'a'.repeat(64),
    isTaxResidenceCase: true,
    provenance: {
      producer: 'residenciafiscal-hybrid-agent-pipeline',
      modelId: 'codex-agent',
      generatedAt: '2026-07-29T20:10:00+02:00',
    },
    review: REVIEW,
  },
  issues: [
    {
      issueId: 'residencia-fiscal-suiza',
      issueType: 'TAX_RESIDENCE',
      question: '¿Tenía el recurrente residencia fiscal en Suiza desde abril de 2009?',
      criterionIds: ['CRIT_183_DIAS', 'CRIT_CDI_TIEBREAKER'],
      holding: {
        holdingId: 'holding-residencia-fiscal-suiza',
        outcome: 'GANA_CONTRIBUYENTE',
        conclusion: 'El recurrente tenía residencia fiscal en Suiza desde el 1 de abril de 2009.',
        decisiveReasoning: 'El conjunto de inmigración, empleo y vivienda situó su vida en Suiza.',
        consequences: ['Consideración como no residente en España desde el 1 de abril.'],
        residenceDetermination: {
          spanishResidence: 'PARTIAL_YEAR_IN_SPAIN',
          otherCountry: 'Suiza',
          nonResidentFrom: '2009-04-01',
          taxYears: [2009],
        },
        anchorIds: ['anchor-residencia-suiza-conclusion'],
        review: REVIEW,
      },
      facts: [],
      evidence: [
        {
          evidenceId: 'evidence-certificados-suizos',
          category: 'DOCUMENTACION_FISCAL_EXTRANJERA',
          description: 'Certificados del Cantón de Ticino.',
          offeredBy: 'TAXPAYER',
          assessment: 'PARTIAL',
          assessmentReason: 'No expresaban de forma inequívoca la residencia fiscal.',
          anchorIds: [],
          review: REVIEW,
        },
      ],
      legalRules: [
        {
          legalRuleId: 'rule-articulo-9-lirpf',
          ruleType: 'STATUTE',
          citation: 'Artículo 9.1 de la Ley 35/2006',
          proposition: 'La residencia se determina por permanencia y núcleo de intereses.',
          anchorIds: [],
          review: REVIEW,
        },
      ],
      burdenOfProof: [],
      presencePeriods: [],
      treatyAnalyses: [],
      anchorIds: [],
      review: REVIEW,
    },
  ],
  anchors: [
    {
      anchorId: 'anchor-residencia-suiza-conclusion',
      purpose: 'HOLDING',
      fidelity: 'EXACT',
      sourceSha256: 'a'.repeat(64),
      fragments: [
        {
          pageIndex: 9,
          printedPage: '8',
          verbatimText:
            'procede declarar la residencia fiscal en Suiza desde el 1 de abril de 2009',
        },
      ],
      review: REVIEW,
    },
  ],
  jurisdictions: [
    { code: 'ch', roles: ['residence_claimed'], treatyBoeId: 'BOE-A-1967-3470' },
    { code: 'es', roles: ['residence_claimed'], treatyBoeId: null },
  ],
};

function renderFicha(sentencia: SentenciaPublica = SENTENCIA) {
  return render(
    <SentenciaPreloadContext.Provider
      value={{ index: null, fichas: { [sentencia.judgment.judgmentId]: sentencia } }}
    >
      <MemoryRouter initialEntries={[`/espana/sentencias/${sentencia.judgment.judgmentId}`]}>
        <Routes>
          <Route path='/espana/sentencias/:judgmentId' element={<SentenciaPage />} />
        </Routes>
      </MemoryRouter>
    </SentenciaPreloadContext.Provider>
  );
}

/** Etiqueta `robots` limpia para comprobar qué escribe la página. */
function prepararMetaRobots(): HTMLMetaElement {
  for (const previa of document.querySelectorAll('meta[name="robots"]')) previa.remove();
  const meta = document.createElement('meta');
  meta.setAttribute('name', 'robots');
  meta.setAttribute('content', 'index, follow');
  document.head.appendChild(meta);
  return meta;
}

afterEach(() => {
  vi.restoreAllMocks();
  resetSentenciasCache();
});

describe('SentenciaPage', () => {
  it('publica identidad, cuestión, pruebas, normas y conclusión', () => {
    renderFicha();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('SAN 1386/2017');
    expect(screen.getByText('ECLI:ES:AN:2017:1386')).toBeInTheDocument();
    expect(screen.getByText(/residencia fiscal en Suiza desde abril/)).toBeInTheDocument();
    expect(screen.getByText(/Certificados del Cantón de Ticino/)).toBeInTheDocument();
    expect(screen.getByText(/Artículo 9.1 de la Ley 35\/2006/)).toBeInTheDocument();
    expect(screen.getByText('Gana el contribuyente')).toBeInTheDocument();
  });

  it('reproduce el extracto literal con su página física e impresa', () => {
    renderFicha();

    expect(
      screen.getByText(/procede declarar la residencia fiscal en Suiza desde el 1 de abril de 2009/)
    ).toBeInTheDocument();
    expect(screen.getByText('Página PDF 9 · Página impresa 8')).toBeInTheDocument();
  });

  it('declara la procedencia automática y el estado real de revisión', () => {
    renderFicha();

    expect(
      screen.getByText(/Análisis generado por un modelo, pendiente de revisión humana/)
    ).toBeInTheDocument();
    expect(screen.getByText(/residenciafiscal-hybrid-agent-pipeline/)).toBeInTheDocument();
    expect(screen.getByText(/Borrador interno/)).toBeInTheDocument();
  });

  it('no afirma que el análisis esté revisado por expertos', () => {
    const { container } = renderFicha();

    const texto = container.textContent ?? '';
    expect(texto).not.toMatch(/revisad[oa]s? por (un )?expert/i);
    expect(texto).not.toMatch(/validad[oa]s? por (un )?especialista/i);
  });

  it('un borrador interno se marca noindex aunque se comparta su URL', () => {
    const meta = prepararMetaRobots();

    renderFicha();

    expect(meta.getAttribute('content')).toBe('noindex, follow');
  });

  it('emite BreadcrumbList y ningún Article, Review ni FAQPage', () => {
    const { container } = renderFicha();

    const bloques = [...container.querySelectorAll('script[type="application/ld+json"]')].map(
      (script) => JSON.parse(script.textContent ?? '{}')
    );
    expect(bloques.map((bloque) => bloque['@type'])).toEqual(['BreadcrumbList']);
  });

  it('renderiza un caso sin hechos sin dejar una sección vacía', () => {
    renderFicha();

    expect(screen.queryByText('Hechos relevantes')).not.toBeInTheDocument();
    expect(screen.getByText('Pruebas valoradas')).toBeInTheDocument();
  });

  it('enlaza la jurisdicción solo con los roles que la proyección autoriza', () => {
    renderFicha();

    expect(screen.getByRole('link', { name: 'Suiza' })).toHaveAttribute('href', '/suiza');
  });

  it('tiene una jerarquía de encabezados navegable', () => {
    const { container } = renderFicha();

    // Un solo h1 y ningún salto de nivel: es lo que permite recorrer la ficha
    // con un lector de pantalla sin perderse entre cuestiones.
    expect(container.querySelectorAll('h1')).toHaveLength(1);
    const niveles = [...container.querySelectorAll('h1, h2, h3')].map((el) =>
      Number(el.tagName.slice(1))
    );
    for (const [indice, nivel] of niveles.entries()) {
      if (indice === 0) continue;
      expect(nivel - niveles[indice - 1]).toBeLessThanOrEqual(1);
    }
    // Las secciones se anuncian por su propio encabezado.
    for (const seccion of container.querySelectorAll('section[aria-labelledby]')) {
      const id = seccion.getAttribute('aria-labelledby') ?? '';
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    }
  });

  it('avisa cuando la sentencia no está publicada, sin inventar contenido', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('null', { status: 404 }) as Response
    );
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <MemoryRouter initialEntries={['/espana/sentencias/sts-9999-2030']}>
        <Routes>
          <Route path='/espana/sentencias/:judgmentId' element={<SentenciaPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no está publicada en el corpus/)).toBeInTheDocument();
    });
  });
});
