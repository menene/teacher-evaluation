<template>
  <div class="docs">
    <h1>📚 Documentación</h1>
    <p class="subtitle">Arquitectura, flujo de procesamiento y modelo de datos del sistema.</p>

    <!-- TOC -->
    <nav class="toc">
      <a href="#arquitectura">Arquitectura</a>
      <a href="#flujo">Flujo de procesamiento</a>
      <a href="#der">Modelo de datos</a>
      <a href="#pipeline-nlp">Pipeline NLP</a>
    </nav>

    <!-- ── Arquitectura ── -->
    <section id="arquitectura" class="section">
      <h2>Arquitectura general</h2>
      <p>El sistema está compuesto por seis servicios Docker que se comunican en una red interna. El frontend se comunica exclusivamente con el backend. Las tareas pesadas (traducción, NLP) se delegan al worker de Celery a través de Redis.</p>
      <div class="diagram-wrap" ref="archRef"></div>
    </section>

    <!-- ── Flujo ── -->
    <section id="flujo" class="section">
      <h2>Flujo de procesamiento</h2>
      <p>Cada archivo subido genera un <strong>Job</strong> con un UUID que avanza por estados. El frontend hace polling cada 1.5 s hasta que el job completa o falla. El modelado de tópicos se ejecuta de forma independiente, bajo demanda.</p>
      <div class="diagram-wrap" ref="flowRef"></div>
    </section>

    <!-- ── DER ── -->
    <section id="der" class="section">
      <h2>Modelo de datos</h2>
      <p>Cinco tablas relacionadas. Los comentarios son la entidad central — concentran la traducción, el puntaje de sentimiento y la asignación de tópico.</p>
      <div class="diagram-wrap" ref="derRef"></div>
    </section>

    <!-- ── Pipeline NLP ── -->
    <section id="pipeline-nlp" class="section">
      <h2>Pipeline NLP</h2>
      <p>Los comentarios en inglés pasan por preprocesamiento antes del análisis de sentimiento y el topic modeling. El análisis de sentimiento usa un ensemble para mayor robustez frente al feedback educativo.</p>
      <div class="diagram-wrap" ref="nlpRef"></div>

      <div class="info-grid">
        <div class="info-card">
          <h3>Ensemble de sentimiento</h3>
          <p><strong>VADER</strong> — fuerte en slang, puntuación, mayúsculas e intensificadores.</p>
          <p><strong>TextBlob</strong> — maneja correctamente la negación (<em>"no hassle"</em>, <em>"not bad"</em>).</p>
          <p class="formula">compound = (vader + textblob) / 2</p>
          <ul>
            <li><span class="pos">≥ 0.05</span> → positivo</li>
            <li><span class="neg">≤ −0.05</span> → negativo</li>
            <li><span class="neu">entre ambos</span> → neutro</li>
          </ul>
        </div>
        <div class="info-card">
          <h3>Calibración del léxico</h3>
          <p>VADER fue entrenado en redes sociales. Se parchean palabras con distinto significado en feedback educativo:</p>
          <table class="lex-table">
            <thead><tr><th>Palabra</th><th>Ajuste</th><th>Razón</th></tr></thead>
            <tbody>
              <tr><td><code>doubts</code>, <code>questions</code></td><td class="neu">0.0</td><td>Preguntar es aprendizaje</td></tr>
              <tr><td><code>problem</code>, <code>hassle</code></td><td class="neg">−0.5</td><td>Permite que la negación funcione</td></tr>
              <tr><td><code>mastery</code>, <code>understandable</code></td><td class="pos">+2.5</td><td>Calidad docente clave</td></tr>
              <tr><td><code>patient</code>, <code>dedicated</code></td><td class="pos">+2.0</td><td>Muy valorados en evaluaciones</td></tr>
              <tr><td><code>available</code>, <code>organized</code></td><td class="pos">+1.5</td><td>Disponibilidad y organización</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import mermaid from "mermaid";

const archRef = ref(null);
const flowRef = ref(null);
const derRef  = ref(null);
const nlpRef  = ref(null);

const diagrams = {
  arch: `
graph TD
  FE["🖥️ Frontend\\nVue 3 + Chart.js"]
  BE["⚡ Backend\\nFastAPI · Python 3.12"]
  Redis["📮 Redis\\nBroker / Result backend"]
  Worker["⚙️ Celery Worker\\nPipeline NLP"]
  DB[("🗄️ MySQL 8")]
  LT["🌐 LibreTranslate\\nES → EN (autoalojado)"]

  FE -- HTTP/JSON --> BE
  BE -- encola tarea --> Redis
  Redis -- despacha --> Worker
  Worker -- persiste --> DB
  BE -- persiste --> DB
  Worker -- traduce --> LT
  BE -- traduce --> LT
`,
  flow: `
flowchart TD
  A(["📄 PDF o 📋 CSV"])
  B["POST /api/evaluations/upload\\nCrea Job UUID · status: pending"]
  C["⚙️ Celery Worker recibe tarea"]
  D["parsing\\nExtrae evaluaciones y comentarios"]
  E["translating\\nDeepL → LibreTranslate fallback"]
  F["sentiment\\nVADER + TextBlob ensemble"]
  G(["✅ complete"])
  H(["🔍 Usuario pulsa Analizar tópicos"])
  I["NMF + TF-IDF global\\nasigna topic_id a cada comentario"]
  J(["✅ tópicos actualizados"])

  A --> B --> C --> D --> E --> F --> G
  G -.-> H --> I --> J
`,
  der: `
erDiagram
  jobs {
    varchar id PK
    int evaluation_id FK
    varchar filename
    varchar status
    text notes
    datetime created_at
  }
  evaluations {
    int id PK
    varchar job_id FK
    int number
    varchar code_prefix
    int cycle
    smallint year
    datetime uploaded_at
  }
  evaluation_comments {
    int id PK
    int evaluation_id FK
    text comment
    text comment_en
    text comment_preprocessed
    float sentiment_compound
    int sentiment_label_id FK
    int topic_id FK
  }
  sentiment_labels {
    int id PK
    varchar label
  }
  topics {
    int id PK
    text keywords
    float weight
    datetime created_at
  }

  jobs ||--o{ evaluations : "genera"
  evaluations ||--o{ evaluation_comments : "tiene"
  sentiment_labels ||--o{ evaluation_comments : "clasifica"
  topics ||--o{ evaluation_comments : "agrupa"
`,
  nlp: `
flowchart LR
  A["comment_en\\n(texto EN)"]
  B["Tokenización\\nNLTK sent + word"]
  C["Filtro stop words\\n+ longitud ≥ 3"]
  D["Lematización\\nWordNetLemmatizer"]
  E["comment_preprocessed\\n(bag of lemmas)"]
  F["VADER\\ncompound score"]
  G["TextBlob\\npolarity score"]
  H["Promedio\\n(vader + textblob) / 2"]
  I["sentiment_compound\\n+ sentiment_label"]
  J["TF-IDF + NMF\\ntopic modeling"]

  A --> B --> C --> D --> E
  A --> F --> H
  A --> G --> H
  H --> I
  E --> J
`,
};

async function renderDiagram(el, definition, id) {
  if (!el) return;
  const { svg } = await mermaid.render(id, definition);
  el.innerHTML = svg;
}

onMounted(async () => {
  mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
  await Promise.all([
    renderDiagram(archRef.value, diagrams.arch, "diag-arch"),
    renderDiagram(flowRef.value, diagrams.flow, "diag-flow"),
    renderDiagram(derRef.value,  diagrams.der,  "diag-der"),
    renderDiagram(nlpRef.value,  diagrams.nlp,  "diag-nlp"),
  ]);
});
</script>

<style scoped>
.docs { max-width: 900px; }
h1 { font-size: 2rem; margin-bottom: .4rem; }
.subtitle { color: #555; margin-bottom: 2rem; }

.toc { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 2.5rem;
       padding: 1rem 1.5rem; background: #fff; border-radius: 10px;
       box-shadow: 0 2px 8px rgba(0,0,0,.07); }
.toc a { color: #3949ab; font-size: .9rem; font-weight: 600; text-decoration: none; }
.toc a:hover { text-decoration: underline; }

.section { background: #fff; border-radius: 12px; padding: 1.75rem;
           box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 1.75rem; }
.section h2 { font-size: 1.2rem; margin-bottom: .5rem; color: #1a1a2e; }
.section > p { color: #666; font-size: .9rem; line-height: 1.6; margin-bottom: 1.25rem; }

.diagram-wrap { overflow-x: auto; }
.diagram-wrap :deep(svg) { max-width: 100%; height: auto; display: block; margin: 0 auto; }

.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-top: 1.5rem; }
@media (max-width: 700px) { .info-grid { grid-template-columns: 1fr; } }

.info-card { background: #f8f8ff; border: 1px solid #e0e0f0; border-radius: 10px; padding: 1.1rem; }
.info-card h3 { font-size: .95rem; color: #1a1a2e; margin-bottom: .75rem; }
.info-card p { font-size: .85rem; color: #555; line-height: 1.5; margin-bottom: .5rem; }
.formula { font-family: monospace; background: #e8eaf6; color: #1a237e; padding: .3rem .6rem;
           border-radius: 6px; display: inline-block; margin: .25rem 0; }
.info-card ul { list-style: none; display: flex; flex-direction: column; gap: .25rem; margin-top: .5rem; }
.info-card li { font-size: .85rem; }

.pos { color: #1a7a4a; font-weight: 600; }
.neg { color: #c0392b; font-weight: 600; }
.neu { color: #b26a00; font-weight: 600; }

.lex-table { width: 100%; border-collapse: collapse; font-size: .8rem; margin-top: .5rem; }
.lex-table th { text-align: left; padding: .4rem .5rem; border-bottom: 2px solid #ddd; color: #555; }
.lex-table td { padding: .35rem .5rem; border-bottom: 1px solid #eee; }
.lex-table code { background: #eee; padding: .05rem .3rem; border-radius: 4px; }
</style>
