import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PreceptoPreloadContext, type PreceptoPreloadMap } from '@/lib/precepto-preload';
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
    { code: 'ch', roles: ['residence_claimed'], treatyBoeIds: ['BOE-A-1967-3470'] },
    { code: 'es', roles: ['residence_claimed'], treatyBoeIds: [] },
  ],
};

/** Precepto tal como lo siembra `prerender.mjs` para la ficha de sentencia. */
const CONVENIO_SUIZO: PreceptoPreloadMap = {
  'cdi-boe-a-1967-3470-a4': {
    entry: {
      slug: 'cdi-boe-a-1967-3470-a4',
      jurisdiccion: 'es',
      titulo: 'Artículo 4 — Domicilio fiscal',
      norma: 'Convenio entre España y la Confederación Suiza…',
      designacion: 'Artículo 4',
      epigrafe: 'Domicilio fiscal',
      grupo: 'cdi',
      boeId: 'BOE-A-1967-3470',
      urlBoe: 'https://www.boe.es/buscar/act.php?id=BOE-A-1967-3470#a4',
      derogada: false,
      notaDerogacion: null,
      vigenteDesde: '1967-03-02',
      redacciones: 1,
      parrafos: 4,
      sentencias: [],
      totalSentencias: 0,
    },
    texto: null,
  },
};

function renderFicha(sentencia: SentenciaPublica = SENTENCIA, preceptos: PreceptoPreloadMap = {}) {
  return render(
    <PreceptoPreloadContext.Provider value={preceptos}>
      <SentenciaPreloadContext.Provider
        value={{
          indexes: {},
          fichas: { es: { [sentencia.judgment.judgmentId]: sentencia } },
        }}
      >
        <MemoryRouter initialEntries={[`/espana/sentencias/${sentencia.judgment.judgmentId}`]}>
          <Routes>
            <Route
              path='/espana/sentencias/:judgmentId'
              element={<SentenciaPage jurisdictionCode='es' />}
            />
          </Routes>
        </MemoryRouter>
      </SentenciaPreloadContext.Provider>
    </PreceptoPreloadContext.Provider>
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

  it('publica el detalle estructurado de prueba, carga, presencia y convenio', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('[]'));
    const rica = {
      ...SENTENCIA,
      issues: [
        {
          ...SENTENCIA.issues[0],
          burdenOfProof: [
            {
              stepId: 'carga-1',
              sequence: 1,
              initialBearer: 'TAXPAYER',
              factToProve: 'la residencia efectiva en Suiza',
              responseRequired: 'aportar prueba coherente de permanencia',
              conclusion: 'La carga quedó satisfecha con el conjunto documental.',
              anchorIds: [],
              review: REVIEW,
            },
          ],
          presencePeriods: [
            {
              periodId: 'periodo-1',
              country: 'Suiza',
              classification: 'PRESENT',
              startDate: '2009-04-01',
              endDate: '2009-12-31',
              dayCount: 275,
              countedFor183DayRule: true,
              calculationMethod: 'Conteo por días acreditados.',
              determinedBy: 'COURT',
              anchorIds: [],
              review: REVIEW,
            },
          ],
          treatyAnalyses: [
            {
              treatyAnalysisId: 'cdi-1',
              treatyCitation: 'Artículo 4 del CDI España–Suiza',
              countries: ['España', 'Suiza'],
              dualResidenceEstablished: true,
              resultCountry: 'Suiza',
              steps: [
                {
                  stepId: 'cdi-paso-1',
                  sequence: 1,
                  criterion: 'CENTRO_INTERESES_VITALES',
                  applied: true,
                  conclusion: 'El centro de intereses vitales estaba en Suiza.',
                  anchorIds: [],
                  review: REVIEW,
                },
              ],
              anchorIds: [],
              review: REVIEW,
            },
          ],
        },
      ],
    } as SentenciaPublica;

    renderFicha(rica);

    expect(screen.getByText(/Documentación fiscal extranjera/)).toBeInTheDocument();
    expect(screen.getByText(/La carga quedó satisfecha/)).toBeInTheDocument();
    expect(screen.getByText(/Presencia · computa para la regla de 183 días/)).toBeInTheDocument();
    expect(screen.getByText(/El centro de intereses vitales estaba en Suiza/)).toBeInTheDocument();
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

  it('enlaza el convenio desde la precarga, sin esperar a JavaScript', () => {
    // En el build no corren los efectos: si el enlace dependiera del `fetch`,
    // el HTML prerenderizado saldría sin él y Google no podría seguirlo.
    renderFicha(SENTENCIA, CONVENIO_SUIZO);

    const enlace = screen.getByRole('link', { name: /Convenio de doble imposición España–Suiza/ });
    expect(enlace).toHaveAttribute('href', '/espana/normativa/cdi-boe-a-1967-3470-a4');
  });

  it('no enlaza ningún convenio si la proyección no declara ninguno', () => {
    const sinConvenio: SentenciaPublica = {
      ...SENTENCIA,
      jurisdictions: [{ code: 'ch', roles: ['residence_claimed'], treatyBoeIds: [] }],
    };

    renderFicha(sinConvenio, CONVENIO_SUIZO);

    expect(screen.queryByRole('link', { name: /Convenio de doble imposición/ })).toBeNull();
  });

  it('avisa cuando la sentencia no está publicada, sin inventar contenido', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('null', { status: 404 }) as Response
    );
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <MemoryRouter initialEntries={['/espana/sentencias/sts-9999-2030']}>
        <Routes>
          <Route
            path='/espana/sentencias/:judgmentId'
            element={<SentenciaPage jurisdictionCode='es' />}
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no está publicada en el corpus/)).toBeInTheDocument();
    });
  });

  it('restaura la ficha precargada al volver mediante navegación SPA', async () => {
    const otra: SentenciaPublica = {
      ...SENTENCIA,
      judgment: {
        ...SENTENCIA.judgment,
        judgmentId: 'sts-4306-2017',
        roj: 'STS 4306/2017',
      },
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/sts-4306-2017.json')) return new Response(JSON.stringify(otra));
      return new Response('null', { status: 404 });
    });

    render(
      <SentenciaPreloadContext.Provider
        value={{
          indexes: {},
          fichas: { es: { [SENTENCIA.judgment.judgmentId]: SENTENCIA } },
        }}
      >
        <MemoryRouter initialEntries={['/espana/sentencias/san-1386-2017']}>
          <Link to='/espana/sentencias/san-1386-2017'>Ir a SAN</Link>
          <Link to='/espana/sentencias/sts-4306-2017'>Ir a STS</Link>
          <Routes>
            <Route
              path='/espana/sentencias/:judgmentId'
              element={<SentenciaPage jurisdictionCode='es' />}
            />
          </Routes>
        </MemoryRouter>
      </SentenciaPreloadContext.Provider>
    );

    await userEvent.click(screen.getByRole('link', { name: 'Ir a STS' }));
    await screen.findByRole('heading', { level: 1, name: /STS 4306\/2017/ });
    await userEvent.click(screen.getByRole('link', { name: 'Ir a SAN' }));

    expect(await screen.findByRole('heading', { level: 1, name: /SAN 1386\/2017/ })).toBeVisible();
  });
});
