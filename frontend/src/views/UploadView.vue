<template>
  <div>
    <h1>📂 Subir Evaluaciones</h1>
    <p class="subtitle">Sube los PDFs de evaluación generados por el sistema UVG para su análisis.</p>

    <div
      class="dropzone"
      :class="{ active: dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <div class="dz-icon">📄</div>
      <p>Arrastra y suelta archivos PDF aquí, o <strong>haz clic para seleccionar</strong></p>
      <input ref="fileInput" type="file" accept=".pdf" multiple hidden @change="onFileChange" />
    </div>

    <ul v-if="files.length" class="file-list">
      <li v-for="(f, i) in files" :key="i">
        <span>📎 {{ f.name }}</span>
        <button @click="removeFile(i)">✕</button>
      </li>
    </ul>

    <div class="actions">
      <div class="action-block">
        <button class="btn btn-primary" :disabled="!files.length || uploading" @click="upload">
          {{ uploading ? '⏳ Enviando…' : '💾 Analizar y Guardar' }}
        </button>
        <p class="action-desc">Guarda los datos y comentarios en la base de datos. Los comentarios se traducen automáticamente al inglés con DeepL.</p>
      </div>

      <div class="action-block">
        <button class="btn btn-secondary" :disabled="!files.length || uploading" @click="analyze">
          {{ uploading ? '⏳ Analizando…' : '🔍 Solo analizar' }}
        </button>
        <p class="action-desc">Extrae y muestra la información del PDF <strong>sin guardar</strong> nada en la base de datos.</p>
      </div>
    </div>

    <p v-if="error" class="error">⚠️ {{ error }}</p>

    <!-- Job progress cards -->
    <div v-if="jobs.length" class="results">
      <h2>⚙️ Procesando</h2>
      <div v-for="job in jobs" :key="job.job_id" class="job-card">
        <div class="job-header">
          <span class="filename">📎 {{ job.filename }}</span>
          <span :class="['badge', job.status]">{{ statusLabel(job.status) }}</span>
        </div>

        <div class="steps">
          <div
            v-for="(step, i) in STEPS"
            :key="i"
            :class="['step', stepState(job, i)]"
          >
            <span class="step-icon">{{ stepState(job, i) === 'done' ? '✅' : stepState(job, i) === 'active' ? '⚡' : '○' }}</span>
            <span class="step-label">{{ step.label }}</span>
          </div>
        </div>

        <div v-if="stepState(job, activeStepIndex(job)) === 'active'" class="loading-bar">
          <span class="ticker">{{ job.ticker }}</span>
          <span class="fun-text">{{ job.funText }}</span>
        </div>

        <div v-if="job.status === 'failed'" class="job-error">❌ {{ job.error || 'Error desconocido' }}</div>
        <div v-if="job.warnings?.length" class="job-warnings">
          <div v-for="(w, wi) in job.warnings" :key="wi">⚠️ {{ w }}</div>
        </div>

        <div v-if="job.evaluations?.length" class="job-result">
          <p class="eval-count">📊 {{ job.evaluations.length }} evaluación(es) encontrada(s)</p>
          <div v-for="(ev, ei) in job.evaluations" :key="ei" class="eval-block">
            <div class="result-fields">
              <div class="field"><span class="label">Evaluación No.</span><span class="value">{{ ev.number }}</span></div>
              <div class="field"><span class="label">Año</span><span class="value">{{ ev.year }}</span></div>
              <div class="field"><span class="label">Ciclo</span><span class="value">{{ ev.cycle }}</span></div>
              <div class="field"><span class="label">Código</span><span class="value">{{ ev.code_prefix }}</span></div>
              <div v-if="ev.average_compound != null" class="field">
                <span class="label">Puntaje promedio</span>
                <span class="value" :style="{ color: sentimentColor(ev.average_compound) }">
                  {{ ev.average_compound.toFixed(2) }}
                </span>
              </div>
              <div v-if="ev.overall_label" class="field">
                <span class="label">Sentimiento general</span>
                <span :class="['sentiment-badge', ev.overall_label]">{{ sentimentEmoji(ev.overall_label) }} {{ ev.overall_label }}</span>
              </div>
            </div>
            <div v-if="ev.comments?.length" class="comments">
              <h3>💬 Comentarios ({{ ev.comments.length }})</h3>
              <ul>
                <li v-for="(c, j) in ev.comments" :key="j">
                  <span class="comment-text">{{ c.text }}</span>
                  <span v-if="c.compound != null" :class="['comment-badge', c.label]">
                    {{ sentimentEmoji(c.label) }} {{ c.compound?.toFixed(2) }}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Analyze-only loading -->
    <div v-if="analyzing" class="job-card" style="margin-top:2rem">
      <div class="job-header"><span class="filename">🔍 Analizando PDF…</span></div>
      <div class="steps">
        <div v-for="(step, i) in PREVIEW_STEPS" :key="i" :class="['step', i === previewStep ? 'active' : i < previewStep ? 'done' : 'pending']">
          <span class="step-icon">{{ i < previewStep ? '✅' : i === previewStep ? '⚡' : '○' }}</span>
          <span class="step-label">{{ step }}</span>
        </div>
      </div>
      <div class="loading-bar">
        <span class="ticker">{{ previewTicker }}</span>
        <span class="fun-text">{{ previewFunText }}</span>
      </div>
    </div>

    <!-- Analyze-only results -->
    <div v-if="previewResults.length" class="results">
      <h2>📋 Resultados</h2>
      <div v-for="(r, i) in previewResults" :key="i" class="result-card">
        <div class="result-header">
          <span class="filename">📎 {{ r.filename }}</span>
          <span class="eval-count-badge">{{ r.evaluations.length }} evaluación(es)</span>
        </div>
        <div v-for="(ev, ei) in r.evaluations" :key="ei" class="eval-block">
          <div class="result-fields">
            <div class="field"><span class="label">Evaluación No.</span><span class="value">{{ ev.fields.number ?? '—' }}</span></div>
            <div class="field"><span class="label">Año</span><span class="value">{{ ev.fields.year ?? '—' }}</span></div>
            <div class="field"><span class="label">Ciclo</span><span class="value">{{ ev.fields.cycle ?? '—' }}</span></div>
            <div class="field"><span class="label">Código</span><span class="value">{{ ev.fields.code_prefix ?? '—' }}</span></div>
          </div>
          <div v-if="ev.comments?.length" class="comments">
            <h3>💬 Comentarios ({{ ev.comments.length }})</h3>
            <ul>
              <li v-for="(c, j) in ev.comments" :key="j">{{ c }}</li>
            </ul>
          </div>
          <div v-else class="no-comments-warning">
            ⚠️ Esta evaluación no tiene comentarios y <strong>no será guardada</strong> en la base de datos.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted, onBeforeUnmount } from "vue";
import api from "../api";

const STEPS = [
  { key: "pending",     label: "En cola" },
  { key: "parsing",     label: "Leyendo PDF" },
  { key: "translating", label: "Traduciendo" },
  { key: "sentiment",   label: "Sentimiento" },
  { key: "topics",      label: "Temas" },
  { key: "complete",    label: "Completado" },
];

const FUN_WORDS = {
  parsing:     ["Descifrando el PDF…", "Extrayendo datos…", "Leyendo entre píxeles…", "Sobreviviendo al OCR…"],
  translating: ["Cruzando el charco lingüístico…", "Hablando con DeepL…", "Traduciendo a la fuerza…", "Buscando al traductor…"],
  sentiment:   ["Leyendo el estado de ánimo…", "Analizando emociones…", "¿Feliz o frustrado?…", "Midiendo la temperatura…"],
  topics:      ["Buscando patrones ocultos…", "Modelando temas…", "Agrupando ideas…", "Aplicando magia estadística…"],
};

const PREVIEW_STEPS = ["Leyendo PDF", "Extrayendo datos", "Listo"];
const PREVIEW_FUN = ["Leyendo entre líneas…", "Extrayendo el alma del PDF…", "Casi listo…", "Sobreviviendo al parser…"];

const files = ref([]);
const dragging = ref(false);
const uploading = ref(false);
const analyzing = ref(false);
const error = ref("");
const jobs = ref([]);
const previewResults = ref([]);
const fileInput = ref(null);
const pollIntervals = ref({});
const previewStep = ref(0);
const previewTicker = ref("-");
const previewFunText = ref("Leyendo entre líneas…");
let previewInterval = null;

function onFileChange(e) { addFiles(Array.from(e.target.files)); }
function onDrop(e) {
  dragging.value = false;
  addFiles(Array.from(e.dataTransfer.files).filter((f) => f.type === "application/pdf"));
}
function addFiles(newFiles) { files.value.push(...newFiles); }
function removeFile(i) { files.value.splice(i, 1); }

function statusLabel(s) {
  const map = {
    pending: "⏳ En cola", parsing: "📄 Leyendo", translating: "🌐 Traduciendo",
    sentiment: "🧠 Sentimiento", topics: "🔍 Temas",
    complete: "✅ Listo", skipped: "⏭️ Ya existe", failed: "❌ Error",
  };
  return map[s] ?? s;
}

function activeStepIndex(job) {
  const i = STEPS.findIndex((s) => s.key === job.status);
  return i === -1 ? 0 : i;
}

function stepState(job, index) {
  const active = activeStepIndex(job);
  if (job.status === "complete") return index < STEPS.length ? "done" : "done";
  if (index < active) return "done";
  if (index === active) return "active";
  return "pending";
}

function sentimentColor(score) {
  if (score >= 0.05) return "#1a7a4a";
  if (score <= -0.05) return "#c0392b";
  return "#b26a00";
}

function sentimentEmoji(label) {
  return { positive: "😊", neutral: "😐", negative: "😟" }[label] ?? "";
}

function pickFunText(status) {
  const list = FUN_WORDS[status] || ["Procesando…"];
  return list[Math.floor(Math.random() * list.length)];
}

function startPolling(job_id) {
  let tick = 0;
  pollIntervals.value[job_id] = setInterval(async () => {
    try {
      const res = await api.get(`/jobs/${job_id}`);
      const data = res.data;
      const job = jobs.value.find((j) => j.job_id === job_id);
      if (!job) return;

      // Animate ticker
      tick++;
      const frames = ["-", "\\", "|", "/", "*"];
      job.ticker = frames[tick % frames.length];

      if (job.status !== data.status) {
        job.status = data.status;
        job.funText = pickFunText(data.status);
        job.error = data.error;
        job.evaluation_id = data.evaluation_id;
        job.evaluations = data.evaluations;
        job.warnings = data.warnings;
      }

      if (["complete", "skipped", "failed"].includes(data.status)) {
        clearInterval(pollIntervals.value[job_id]);
        delete pollIntervals.value[job_id];
      }
    } catch {
      // ignore transient errors
    }
  }, 1500);
}

async function upload() {
  uploading.value = true;
  error.value = "";
  previewResults.value = [];
  try {
    const form = new FormData();
    files.value.forEach((f) => form.append("files", f));
    const res = await api.post("/evaluations/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    files.value = [];
    for (const item of res.data) {
      jobs.value.unshift({ ...item, status: "pending", ticker: "-", funText: "En cola…", error: null });
      startPolling(item.job_id);
    }
  } catch (e) {
    error.value = e.response?.data?.detail ?? "Error al subir el archivo.";
  } finally {
    uploading.value = false;
  }
}

async function analyze() {
  uploading.value = true;
  analyzing.value = true;
  error.value = "";
  jobs.value = [];
  previewResults.value = [];
  previewStep.value = 0;
  previewFunText.value = PREVIEW_FUN[0];

  let tick = 0;
  const frames = ["-", "\\", "|", "/", "*"];
  previewInterval = setInterval(() => {
    tick++;
    previewTicker.value = frames[tick % frames.length];
    if (tick % 6 === 0 && previewStep.value < PREVIEW_STEPS.length - 2) previewStep.value++;
    previewFunText.value = PREVIEW_FUN[tick % PREVIEW_FUN.length];
  }, 300);

  try {
    const form = new FormData();
    files.value.forEach((f) => form.append("files", f));
    const res = await api.post("/evaluations/upload/analyze", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    previewStep.value = PREVIEW_STEPS.length - 1;
    previewResults.value = res.data.map((item) => ({
      filename: item.filename,
      evaluations: item.evaluations,
    }));
    files.value = [];
  } catch (e) {
    error.value = e.response?.data?.detail ?? "Error al analizar el archivo.";
  } finally {
    clearInterval(previewInterval);
    analyzing.value = false;
    uploading.value = false;
  }
}

onUnmounted(() => {
  Object.values(pollIntervals.value).forEach(clearInterval);
  if (previewInterval) clearInterval(previewInterval);
});
</script>

<style scoped>
h1 { margin-bottom: 0.4rem; }
.subtitle { color: #555; margin-bottom: 1.5rem; }

.dropzone { border: 2px dashed #bbb; border-radius: 12px; padding: 3rem 2rem; text-align: center;
            cursor: pointer; background: #fff; margin-bottom: 1rem; transition: border-color .2s, background .2s; }
.dropzone.active { border-color: #e94560; background: #fff5f7; }
.dz-icon { font-size: 2.5rem; margin-bottom: .5rem; }
.dropzone p { color: #666; }

.file-list { list-style: none; margin-bottom: 1.25rem; display: flex; flex-direction: column; gap: .4rem; }
.file-list li { display: flex; justify-content: space-between; align-items: center;
                padding: .5rem .9rem; background: #fff; border-radius: 8px;
                box-shadow: 0 1px 4px rgba(0,0,0,.07); font-size: .9rem; }
.file-list button { background: none; border: none; cursor: pointer; color: #e94560; font-size: 1rem; }

.actions { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.action-block { flex: 1; min-width: 220px; background: #fff; border-radius: 12px;
                padding: 1.25rem; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.action-desc { color: #777; font-size: .85rem; margin-top: .5rem; line-height: 1.4; }

.btn { border: none; padding: .7rem 1.5rem; border-radius: 8px; font-size: .95rem;
       cursor: pointer; font-weight: 600; width: 100%; }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-primary { background: #1a1a2e; color: #fff; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-secondary:hover:not(:disabled) { background: #e2e2e2; }

.error { color: #e94560; margin-top: .5rem; }

.results { margin-top: 2rem; }
.results h2 { margin-bottom: 1rem; }

/* Job cards */
.job-card { background: #fff; border-radius: 12px; padding: 1.25rem;
            box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 1rem; }
.job-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.filename { font-weight: 600; font-size: .95rem; }

.badge { font-size: .78rem; padding: .25rem .7rem; border-radius: 20px; font-weight: 600; }
.badge.complete  { background: #e6f9f0; color: #1a7a4a; }
.badge.failed    { background: #fdecea; color: #c0392b; }
.badge.skipped   { background: #fff3e0; color: #b26a00; }
.badge.pending, .badge.parsing, .badge.translating,
.badge.sentiment, .badge.topics { background: #e8eaf6; color: #3949ab; }

.steps { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: .75rem; }
.step { display: flex; align-items: center; gap: .3rem; font-size: .82rem; padding: .3rem .7rem;
        border-radius: 20px; background: #f5f5f5; color: #aaa; transition: all .3s; }
.step.done    { background: #e6f9f0; color: #1a7a4a; }
.step.active  { background: #1a1a2e; color: #fff; font-weight: 600; }
.step.pending { background: #f5f5f5; color: #bbb; }

.loading-bar { display: flex; align-items: center; gap: .75rem; padding: .5rem .75rem;
               background: #f8f8f8; border-radius: 8px; font-size: .85rem; color: #555; }
.ticker { font-family: monospace; font-size: 1.1rem; color: #e94560; font-weight: 700;
          display: inline-block; width: 1rem; text-align: center; }
.fun-text { font-style: italic; }

.job-error { color: #c0392b; font-size: .85rem; margin-top: .5rem; }
.job-warnings { margin-top: .5rem; display: flex; flex-direction: column; gap: .25rem; }
.job-warnings div { font-size: .85rem; color: #b26a00; background: #fff8e1; padding: .4rem .7rem; border-radius: 6px; }
.no-comments-warning { font-size: .85rem; color: #b26a00; background: #fff8e1; padding: .5rem .8rem;
                       border-radius: 6px; margin-top: .5rem; }
.job-result { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #eee; }
.eval-count { font-size: .85rem; color: #555; margin-bottom: .75rem; }
.eval-block { margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px dashed #eee; }
.eval-block:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }

/* Preview result cards */
.result-card { background: #fff; border-radius: 12px; padding: 1.5rem;
               box-shadow: 0 2px 8px rgba(0,0,0,.08); margin-bottom: 1.25rem; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.eval-count-badge { font-size: .8rem; background: #e8eaf6; color: #3949ab; padding: .25rem .7rem; border-radius: 20px; font-weight: 600; }
.result-fields { display: flex; flex-wrap: wrap; gap: .75rem; margin-bottom: 1rem; }
.field { background: #f8f8f8; border-radius: 8px; padding: .5rem .9rem; }
.label { font-size: .75rem; color: #888; display: block; margin-bottom: .1rem; }
.value { font-size: 1rem; font-weight: 600; color: #1a1a2e; }
.comments h3 { font-size: .95rem; margin-bottom: .6rem; color: #444; }
.comments ul { list-style: none; display: flex; flex-direction: column; gap: .5rem; }
.comments li { background: #f8f8f8; border-left: 3px solid #e94560; padding: .6rem .9rem;
               border-radius: 0 8px 8px 0; font-size: .9rem; color: #444; line-height: 1.5;
               display: flex; justify-content: space-between; align-items: flex-start; gap: .5rem; }
.comment-text { flex: 1; }
.comment-badge { font-size: .75rem; font-weight: 600; padding: .2rem .5rem; border-radius: 12px;
                 white-space: nowrap; }
.comment-badge.positive { background: #e6f9f0; color: #1a7a4a; }
.comment-badge.neutral  { background: #fff8e1; color: #b26a00; }
.comment-badge.negative { background: #fdecea; color: #c0392b; }
.sentiment-badge { font-size: .85rem; font-weight: 600; padding: .25rem .6rem; border-radius: 12px; }
.sentiment-badge.positive { background: #e6f9f0; color: #1a7a4a; }
.sentiment-badge.neutral  { background: #fff8e1; color: #b26a00; }
.sentiment-badge.negative { background: #fdecea; color: #c0392b; }
</style>
