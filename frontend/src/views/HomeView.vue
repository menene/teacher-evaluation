<template>
  <div>
    <div class="hero">
      <h1>🎓 Análisis de Evaluaciones Docentes</h1>
      <p>Plataforma de análisis para las evaluaciones de profesores de la Universidad del Valle de Guatemala. Procesa PDFs del sistema UVG e importaciones masivas desde CSV, traduce comentarios automáticamente y genera reportes comparativos de sentimiento y tópicos.</p>
    </div>

    <div class="cards">
      <router-link class="card" to="/upload">
        <div class="card-icon">📂</div>
        <h2>Subir Evaluaciones</h2>
        <p>Sube uno o varios PDFs de evaluación. Los comentarios se extraen, traducen y puntúan automáticamente en segundo plano.</p>
        <span class="card-action">Ir a subir →</span>
      </router-link>

      <router-link class="card" to="/reports">
        <div class="card-icon">📈</div>
        <h2>Ver Reportes</h2>
        <p>Filtra por año, ciclo y código. Visualiza sentimiento en gráficas de línea y barras, explora tópicos con distribución de sentimiento y revisa el detalle de cada evaluación.</p>
        <span class="card-action">Ver reportes →</span>
      </router-link>
    </div>

    <!-- Pipeline -->
    <div class="pipeline">
      <h3>Pipeline de procesamiento</h3>
      <div class="steps">
        <div class="step">
          <div class="step-icon">📄</div>
          <div class="step-body">
            <strong>Extracción de PDF / CSV</strong>
            <span>PDFs del sistema UVG o importación masiva desde CSV con <code>import_csv.py</code>. Soporta ~24k+ comentarios.</span>
          </div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-icon">🌐</div>
          <div class="step-body">
            <strong>Traducción automática</strong>
            <span>DeepL (primario) con fallback automático a <strong>LibreTranslate</strong> autoalojado. Sin límites de tokens.</span>
          </div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-icon">🧠</div>
          <div class="step-body">
            <strong>Análisis de sentimiento</strong>
            <span>Ensemble VADER + TextBlob con léxico calibrado para feedback educativo. Puntaje −1.0 a +1.0 por comentario.</span>
          </div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-icon">🏷️</div>
          <div class="step-body">
            <strong>Modelado de tópicos</strong>
            <span>NMF + TF-IDF global. Muestra distribución de sentimiento por tópico y nube de palabras con pesos NMF.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Scripts -->
    <div class="scripts-section">
      <h3>Scripts de utilidad</h3>
      <div class="scripts-grid">
        <div class="script-card">
          <code class="script-name">import_csv.py</code>
          <span class="script-desc">Importa comentarios desde CSV agrupando por profesor, materia, ciclo y año.</span>
          <code class="script-cmd">docker compose exec backend python import_csv.py data/archivo.csv</code>
        </div>
        <div class="script-card">
          <code class="script-name">translate.py</code>
          <span class="script-desc">Traduce todos los comentarios sin <code>comment_en</code>. Retoma donde se quedó si se interrumpe.</span>
          <code class="script-cmd">docker compose exec backend python translate.py</code>
        </div>
        <div class="script-card">
          <code class="script-name">rescore.py</code>
          <span class="script-desc">Re-puntúa sentimiento en comentarios traducidos. Usa <code>--force</code> para re-puntuar todos.</span>
          <code class="script-cmd">docker compose exec backend python rescore.py</code>
        </div>
      </div>
    </div>

    <!-- Tech stack -->
    <div class="tech-grid">
      <div class="tech-card">
        <span class="tech-label">Backend</span>
        <div class="tool-list">
          <span class="tool"><img src="https://cdn.simpleicons.org/fastapi" class="tool-logo" alt="FastAPI" />FastAPI</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/sqlalchemy" class="tool-logo" alt="SQLAlchemy" />SQLAlchemy</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/mysql" class="tool-logo" alt="MySQL" />MySQL 8</span>
        </div>
      </div>
      <div class="tech-card">
        <span class="tech-label">Pipeline NLP</span>
        <div class="tool-list">
          <span class="tool"><img src="https://cdn.simpleicons.org/python" class="tool-logo" alt="Python" />VADER</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/python" class="tool-logo" alt="Python" />TextBlob</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/python" class="tool-logo" alt="Python" />NLTK</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/scikitlearn" class="tool-logo" alt="scikit-learn" />scikit-learn</span>
        </div>
      </div>
      <div class="tech-card">
        <span class="tech-label">Traducción</span>
        <div class="tool-list">
          <span class="tool"><img src="https://cdn.simpleicons.org/deepl" class="tool-logo" alt="DeepL" />DeepL</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/python" class="tool-logo" alt="LibreTranslate" />LibreTranslate</span>
        </div>
      </div>
      <div class="tech-card">
        <span class="tech-label">Async</span>
        <div class="tool-list">
          <span class="tool"><img src="https://cdn.simpleicons.org/celery" class="tool-logo" alt="Celery" />Celery 5</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/redis" class="tool-logo" alt="Redis" />Redis 7</span>
        </div>
      </div>
      <div class="tech-card">
        <span class="tech-label">Frontend</span>
        <div class="tool-list">
          <span class="tool"><img src="https://cdn.simpleicons.org/vuedotjs" class="tool-logo" alt="Vue" />Vue 3</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/chartdotjs" class="tool-logo" alt="Chart.js" />Chart.js</span>
          <span class="tool"><img src="https://cdn.simpleicons.org/vite" class="tool-logo" alt="Vite" />Vite</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero { margin-bottom: 2.5rem; }
.hero h1 { font-size: 2rem; margin-bottom: 0.75rem; }
.hero p { color: #555; max-width: 720px; line-height: 1.6; }

.cards { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 2rem; }
.card { background: #fff; border-radius: 12px; padding: 1.75rem; flex: 1; min-width: 240px;
        text-decoration: none; color: inherit; box-shadow: 0 2px 8px rgba(0,0,0,.08);
        transition: box-shadow .2s, transform .2s; display: flex; flex-direction: column; gap: .5rem; }
.card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.13); transform: translateY(-2px); }
.card-icon { font-size: 2rem; }
.card h2 { font-size: 1.2rem; }
.card p { color: #777; font-size: .9rem; line-height: 1.5; flex: 1; }
.card-action { color: #e94560; font-weight: 600; font-size: .9rem; margin-top: .25rem; }

/* Pipeline */
.pipeline { background: #fff; border-radius: 12px; padding: 1.75rem;
            box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 1.5rem; }
.pipeline h3 { font-size: 1.05rem; margin-bottom: 1.25rem; color: #1a1a2e; }
.steps { display: flex; align-items: flex-start; gap: .5rem; flex-wrap: wrap; }
.step { background: #f8f8ff; border: 1px solid #e0e0f0; border-radius: 10px; padding: .9rem 1rem;
        display: flex; gap: .75rem; flex: 1; min-width: 180px; }
.step-icon { font-size: 1.5rem; flex-shrink: 0; }
.step-body { display: flex; flex-direction: column; gap: .3rem; }
.step-body strong { font-size: .88rem; color: #1a1a2e; }
.step-body span { font-size: .8rem; color: #666; line-height: 1.45; }
.step-body code { background: #eee; padding: .05rem .3rem; border-radius: 4px; font-size: .75rem; }
.step-arrow { font-size: 1.2rem; color: #bbb; align-self: center; flex-shrink: 0; }

/* Scripts */
.scripts-section { background: #fff; border-radius: 12px; padding: 1.75rem;
                   box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 1.5rem; }
.scripts-section h3 { font-size: 1.05rem; margin-bottom: 1.25rem; color: #1a1a2e; }
.scripts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
.script-card { background: #f8f8ff; border: 1px solid #e0e0f0; border-radius: 10px;
               padding: 1rem; display: flex; flex-direction: column; gap: .5rem; }
.script-name { font-size: .9rem; font-weight: 700; color: #1a1a2e; }
.script-desc { font-size: .82rem; color: #666; line-height: 1.45; }
.script-desc code { background: #eee; padding: .05rem .3rem; border-radius: 4px; font-size: .75rem; }
.script-cmd { font-size: .75rem; background: #1a1a2e; color: #a5f3c0; padding: .45rem .65rem;
              border-radius: 6px; word-break: break-all; line-height: 1.5; }

/* Tech stack */
.tech-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; }
.tech-card { background: #fff; border-radius: 10px; padding: .9rem 1.1rem;
             box-shadow: 0 2px 8px rgba(0,0,0,.06); display: flex; flex-direction: column; gap: .6rem; }
.tech-label { font-size: .72rem; font-weight: 700; text-transform: uppercase;
              letter-spacing: .06em; color: #3949ab; }
.tool-list { display: flex; flex-direction: column; gap: .35rem; }
.tool { display: flex; align-items: center; gap: .45rem; font-size: .85rem; color: #444; }
.tool-logo { width: 18px; height: 18px; object-fit: contain; flex-shrink: 0; }
</style>
