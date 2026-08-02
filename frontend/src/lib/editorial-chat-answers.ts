import type { EditorialChatAnswer } from '@/types/chat';

const VERSION = 'home-editorial-2026-08-03-v1';
const UPDATED_AT = '2026-08-03';

export const EDITORIAL_CHAT_ANSWERS: readonly EditorialChatAnswer[] = [
  {
    id: 'proof-of-183-days',
    question:
      '¿Qué pruebas valora el Tribunal Supremo para acreditar o discutir el cómputo de los 183 días?',
    version: VERSION,
    updatedAt: UPDATED_AT,
    content:
      '**Respuesta corta:** no existe una lista cerrada de documentos que, por sí solos, acrediten o desvirtúen los 183 días. El dato relevante es la **presencia física efectiva durante el año natural**, reconstruida mediante prueba fechada, completa y coherente.\n\n' +
      '**Criterio judicial.** La valoración conjunta corresponde al tribunal de instancia; el Tribunal Supremo no vuelve a pesar normalmente esa prueba en casación. Por eso, que un documento sea admisible no significa que sea suficiente.\n\n' +
      '**Ejemplo del expediente, no regla general.** La STS 2735/2023 reproduce un caso en el que un pasaporte incompleto no permitía verificar todos los viajes y unas copias de tarjetas, sin extractos de movimientos, no probaban la localización. La calidad y continuidad del rastro importan más que el nombre del documento.\n\n' +
      '**Conclusión:** importa la cobertura del ejercicio completo, la consistencia entre fuentes y la obtención lícita de la prueba; no hay un documento mágico.',
    sources: [
      {
        judgmentId: 'sts-3498-2025',
        roj: 'STS 3498/2025',
        ecli: 'ECLI:ES:TS:2025:3498',
        page: 5,
        sourceSha256: 'cbb02693a5f4408890bb981b80b5d7a03c1d62c47cee650d45689299f0e1080f',
        quote:
          'la sentencia de instancia valora la\nprueba procesal planteada libremente por las partes y alcanza la conclusión, no ya en lo referente al certiﬁcado\naportado, sino al hecho mismo de la residencia del aportante en España, en virtud de datos que considera\nconcluyentes, que el interesado no ha desmentido y que, además, discurren en el ámbito de la valoración de\nla prueba, operación de la que ostenta el monopolio el Tribunal sentenciador, por lo que esa valoración es\ninaccesible al control casacional, en un recurso extraordinario como es este ( art. 87.bis, 1 LJCA).',
        verification: 'EXACT',
      },
      {
        judgmentId: 'sts-2735-2023',
        roj: 'STS 2735/2023',
        ecli: 'ECLI:ES:TS:2023:2735',
        page: 8,
        sourceSha256: 'f000fac5ed80654e305013e7f1e25919ebf2d73131871f303b593d1019d3d976',
        quote:
          'También entrega fotocopia del pasaporte estadounidense con numerosos sellos por viajes a Asia. Esta\ncircunstancia ya fue comentada anteriormente, y es que los viajes se deben a la actividad profesional y no\nes extraño que se desplace a Asia (sin que en el curso de las actuaciones se haya podido veriﬁcar el número\nde viajes que efectuó desde Marruecos ya que no entregó las fotocopias de todas sus hojas del pasaporte\nde Marruecos). Lo importante en este punto es que las retribuciones por su trabajo se cobran en España y\nno en EE.UU.\nIgualmente aporta la fotocopia de sus tarjetas VISA -no de extractos de movimientos- y fotocopia del carnet\nde conducir en aquel país (anverso y reverso), sin que nada pruebe esta documentación.',
        verification: 'EXACT',
      },
    ],
  },
  {
    id: 'sporadic-absences',
    question: '¿Cómo se valoran las ausencias esporádicas del art. 9.1.a) LIRPF?',
    version: VERSION,
    updatedAt: UPDATED_AT,
    content:
      '**Regla legal:** las ausencias verdaderamente esporádicas se suman al tiempo de permanencia en España, salvo que se acredite residencia fiscal en otro país.\n\n' +
      '**Criterio del Tribunal Supremo:** antes de aplicar esa regla hay que decidir si la salida fue realmente esporádica. El concepto es objetivo y atiende a la **duración o intensidad de la permanencia fuera de España**; no depende de la intención de volver.\n\n' +
      'En los casos de becas estudiados por el Supremo, permanecer fuera de España más de 183 días durante el año natural no se consideró una ausencia esporádica. Por tanto, no es correcto razonar siempre que “sin certificado extranjero, toda ausencia suma”: primero debe existir una ausencia que pueda calificarse como esporádica.\n\n' +
      '**Límite:** esta doctrina se fijó sobre unos hechos concretos. No convierte cualquier estancia prolongada en prueba automática de no residencia ni resuelve por sí sola los demás criterios del art. 9 LIRPF.',
    sources: [
      {
        judgmentId: 'sts-115-2018',
        roj: 'STS 115/2018',
        ecli: 'ECLI:ES:TS:2018:115',
        page: 10,
        sourceSha256: 'aa5d36fa948d17e901c017559c162a0d6cf096b8eeb248a3c1f2c88806bce236',
        quote:
          '1º) La permanencia fuera del territorio nacional durante más de 183 días a lo largo del año natural como\nconsecuencia del disfrute de una beca de estudios, no puede considerarse como una ausencia esporádica a\nlos efectos del artículo 9.1.a) de Ley 35/2006, de 28 de noviembre, del Impuesto sobre la Renta de las Personas\nFísicas , esto es, a ﬁn de determinar la permanencia en España por tiempo superior a 183 días durante el año\nnatural y, con ello, su residencia habitual en España.\n2º) El concepto de ausencias esporádicas debe atender exclusivamente al dato objetivo de la duración o\nintensidad de la permanencia fuera del territorio español, sin que para su concurrencia pueda ser vinculado\na la presencia de un elemento volitivo o intencional que otorgue prioridad a la voluntad del contribuyente de\nestablecerse de manera ocasional fuera del territorio español, con clara intención de retorno al lugar de partida.',
        verification: 'EXACT',
      },
    ],
  },
  {
    id: 'foreign-tax-residence-certificate',
    question: '¿Qué valor probatorio tiene un certificado de residencia fiscal extranjero?',
    version: VERSION,
    updatedAt: UPDATED_AT,
    content:
      '**Depende de para qué se aporte.** Cuando lo emite la autoridad competente del otro Estado y declara que se expide **a efectos del CDI**, no puede ignorarse ni rechazarse unilateralmente por la Administración o por un tribunal español. Su validez debe presumirse para determinar si existe un conflicto de residencia.\n\n' +
      'Eso no significa que el certificado decida siempre el país de residencia final. Puede acreditar que el otro Estado también considera residente a la persona; si España llega a la misma conclusión conforme a su normativa interna, aparece una doble residencia y deben aplicarse las reglas de desempate del CDI.\n\n' +
      '**No deben mezclarse dos cuestiones:** una cosa es el certificado expedido a efectos de un convenio y otra la prueba exigida por el art. 9.1.a) LIRPF para excluir ausencias esporádicas. En la jurisprudencia de las becas, el Supremo no fijó una regla universal sobre el certificado porque concluyó antes que aquellas ausencias prolongadas no eran esporádicas.',
    sources: [
      {
        judgmentId: 'sts-3498-2025',
        roj: 'STS 3498/2025',
        ecli: 'ECLI:ES:TS:2025:3498',
        page: 12,
        sourceSha256: 'cbb02693a5f4408890bb981b80b5d7a03c1d62c47cee650d45689299f0e1080f',
        quote:
          'Los órganos administrativos o judiciales nacionales no son competentes para enjuiciar las circunstancias\nen las que se ha expedido un certiﬁcado de residencia ﬁscal por otro Estado ni, en consecuencia, pueden\nprescindir del contenido de un certiﬁcado de residencia ﬁscal emitido por las autoridades ﬁscales de un país\nque ha suscrito con España un Convenio de Doble Imposición, cuando dicho certiﬁcado se ha extendido a los\nefectos del Convenio.\n2.A los efectos de analizar la existencia de un conﬂicto de residencia entre dos Estados, la validez de un\ncertiﬁcado de residencia expedido por las autoridades ﬁscales del otro Estado contratante en el sentido del\nConvenio de Doble Imposición debe ser presumida, no pudiendo ser su contenido rechazado, precisamente\npor haberse suscrito el referido Convenio.',
        verification: 'EXACT',
      },
      {
        judgmentId: 'sts-115-2018',
        roj: 'STS 115/2018',
        ecli: 'ECLI:ES:TS:2018:115',
        page: 10,
        sourceSha256: 'aa5d36fa948d17e901c017559c162a0d6cf096b8eeb248a3c1f2c88806bce236',
        quote:
          'la cuestión acerca de si se precisa o no, en todo caso, la certiﬁcación de la residencia ﬁscal en otro país\npara neutralizar la operatividad de las ausencias esporádicas como complemento de la permanencia en\nEspaña deviene superﬂua si se proyecta sobre una realidad inexistente. En otras palabras, si en el caso que\ndebatimos no podemos dar carta de naturaleza a la existencia de ausencias esporádicas, como concepto\nnormativo complementario al de permanencia, que la Administración constata, sobreviene en tal caso la\nirrelevancia de que nos pronunciemos sobre el modo de acreditar una residencia en otro país incompatible\ncon la española, pues ya hemos partido de la base de que, en este concreto asunto, la residencia en España\nse funda equivocadamente sobre la apreciación de ausencias esporádicas que no son tales.',
        verification: 'EXACT',
      },
    ],
  },
  {
    id: 'tax-treaty-tie-breaker',
    question: '¿Cuándo se aplica la regla de desempate del art. 4 del CDI aplicable?',
    version: VERSION,
    updatedAt: UPDATED_AT,
    content:
      '**Solo entra cuando existe doble residencia:** los dos Estados consideran residente a la misma persona conforme a sus respectivas normas internas y el convenio aplicable contiene una regla para resolver el conflicto. Tener bienes o vínculos en dos países, por sí solo, no basta.\n\n' +
      'El orden habitual es escalonado: **vivienda permanente**, **centro de intereses vitales**, **lugar donde vive habitualmente**, **nacionalidad** y, si nada resuelve el conflicto, **acuerdo amistoso entre las autoridades competentes**. No se puede saltar directamente al criterio que resulte más favorable.\n\n' +
      '**Importante:** se aplica el texto del CDI concreto, no el Modelo OCDE como si fuera una norma directamente vigente. Además, los conceptos del convenio requieren una interpretación autónoma y no se identifican sin más con criterios internos como el núcleo de intereses económicos del art. 9.1.b) LIRPF.',
    sources: [
      {
        judgmentId: 'sts-3498-2025',
        roj: 'STS 3498/2025',
        ecli: 'ECLI:ES:TS:2025:3498',
        page: 12,
        sourceSha256: 'cbb02693a5f4408890bb981b80b5d7a03c1d62c47cee650d45689299f0e1080f',
        quote:
          'Un Estado ﬁrmante de un Convenio de Doble Imposición no puede, de forma unilateral, enjuiciar la existencia\nde un conﬂicto de residencia, prescindiendo de la aplicación de las normas especíﬁcas suscritas en el referido\nConvenio para estos casos. De esta forma, ante un conﬂicto de residencia, es necesario acudir a las normas\nprevistas para su solución en el Convenio de Doble Imposición, requiriendo para ello de una interpretación\nautónoma en relación con las normas internas que alberguen conceptos similares.',
        verification: 'EXACT',
      },
      {
        judgmentId: 'sts-2735-2023',
        roj: 'STS 2735/2023',
        ecli: 'ECLI:ES:TS:2023:2735',
        page: 11,
        sourceSha256: 'f000fac5ed80654e305013e7f1e25919ebf2d73131871f303b593d1019d3d976',
        quote:
          'Cuando en virtud de las disposiciones del apartado 1 una persona física sea residente de ambos Estados\ncontratantes, su situación se resolverá de la siguiente manera:\na) Esta persona será considerada residente del Estado donde tenga una vivienda permanente a su disposición;\nsi tuviera una vivienda permanente a su disposición en ambos Estados, se considerará residente del Estado\ncon el que mantenga relaciones personales y económicas más estrechas (centro de intereses vitales).\nb) Si no pudiera determinarse el Estado en el que dicha persona tiene el centro de sus intereses vitales, o si\nno tuviera una vivienda permanente a su disposición en ninguno de los Estados, se considerará residente del\nEstado donde viva habitualmente.\nc) Si viviera habitualmente en ambos Estados o no lo hiciera en ninguno de ellos, se considerará residente del\nEstado del que sea nacional.\nd) Si fuera nacional de ambos Estados o no lo fuera de ninguno de ellos, las autoridades competentes de los\nEstados contratantes resolverán el caso mediante acuerdo amistoso.',
        verification: 'EXACT',
      },
    ],
  },
];
