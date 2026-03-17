<template>
  <div>
    <div class="page-header">
      <div>
        <h1>📈 Reportes Comparativos</h1>
        <p class="subtitle">Análisis de sentimiento agrupado por año y ciclo académico.</p>
      </div>
      <div class="header-actions">
        <div class="topic-controls">
          <label class="topics-label">Tópicos:</label>
          <input v-model.number="nTopics" type="number" min="2" max="15" class="n-topics-input" />
          <button
            class="btn-topics"
            :disabled="topicRunning || !summary.length"
            @click="runTopics"
          >
            {{ topicRunning ? '⏳ Analizando…' : '🔍 Analizar tópicos' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">⏳ Cargando datos…</div>
    <div v-else-if="!summary.length" class="empty">
      🔧 No hay evaluaciones procesadas aún. Sube y analiza PDFs primero.
    </div>

    <template v-else>
      <!-- ── Filters ── -->
      <div class="filters-bar">
        <select v-model="filterYear" @change="applyFilters">
          <option :value="null">Todos los años</option>
          <option v-for="y in filterOptions.years" :key="y" :value="y">{{ y }}</option>
        </select>
        <select v-model="filterCycle" @change="applyFilters">
          <option :value="null">Todos los ciclos</option>
          <option v-for="c in filterOptions.cycles" :key="c" :value="c">Ciclo {{ c }}</option>
        </select>
        <select v-model="filterCode" @change="applyFilters">
          <option :value="null">Todos los códigos</option>
          <option v-for="c in filterOptions.codes" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>

      <!-- ── Chart ── -->
      <div class="card">
        <h2>📊 Comentarios por sentimiento</h2>
        <p class="card-sub">Cantidad de comentarios positivos, neutros y negativos por año y ciclo.</p>
        <div class="chart-wrap">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <!-- ── Secondary charts ── -->
      <div class="charts-grid">
        <div class="card">
          <h2>📊 Por código</h2>
          <p class="card-sub">Comentarios por carrera.</p>
          <div class="chart-wrap-sm">
            <Bar :data="byCodeData" :options="barOptions" />
          </div>
        </div>
        <div class="card">
          <h2>📊 Por ciclo</h2>
          <p class="card-sub">Comentarios por ciclo académico.</p>
          <div class="chart-wrap-sm">
            <Bar :data="byCycleData" :options="barOptions" />
          </div>
        </div>
      </div>

      <!-- ── Topics ── -->
      <div v-if="topics.length" class="card" style="margin-top:1.5rem">
        <h2>🏷️ Tópicos identificados</h2>
        <p class="card-sub">
          Temas recurrentes en los comentarios de estudiantes (NMF global).
          Actualizado {{ topicsDate }}.
        </p>
        <div class="topics-grid">
          <div v-for="t in topics" :key="t.id" class="topic-card">
            <div class="topic-num">Tópico {{ t.id }}</div>
            <div class="topic-wc">
              <span
                v-for="kw in t.keywords" :key="kw.word"
                class="wc-word"
                :style="{
                  fontSize: (10 + Math.round(kw.weight * 14)) + 'px',
                  opacity: 0.5 + kw.weight * 0.5,
                  color: kw.weight > 0.7 ? '#1a1a2e' : kw.weight > 0.4 ? '#3949ab' : '#7986cb',
                }"
              >{{ kw.word }}</span>
            </div>
            <div class="topic-sentiment-bar" :title="`${t.sentiment.positive} pos · ${t.sentiment.neutral} neu · ${t.sentiment.negative} neg`">
              <div class="tsb-pos" :style="{ flex: t.sentiment.positive }"></div>
              <div class="tsb-neu" :style="{ flex: t.sentiment.neutral }"></div>
              <div class="tsb-neg" :style="{ flex: t.sentiment.negative }"></div>
            </div>
            <div class="topic-sentiment-legend">
              <span class="tsb-label pos">😊 {{ t.sentiment.positive }}</span>
              <span class="tsb-label neu">😐 {{ t.sentiment.neutral }}</span>
              <span class="tsb-label neg">😟 {{ t.sentiment.negative }}</span>
            </div>
            <div class="tsb-total">{{ t.comment_count }} comentario{{ t.comment_count !== 1 ? 's' : '' }}</div>
          </div>
        </div>
      </div>

      <!-- ── Evaluations table ── -->
      <div class="card" style="margin-top:1.5rem">
        <div class="table-header">
          <h2>📋 Evaluaciones</h2>
          <span class="total-count">{{ evalTotal }} evaluaciones</span>
        </div>

        <table class="eval-table">
          <thead>
            <tr>
              <th>No.</th>
              <th>Código</th>
              <th>Año</th>
              <th>Ciclo</th>
              <th>Comentarios</th>
              <th>Puntaje promedio</th>
              <th>Sentimiento</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ev in evaluations" :key="ev.id">
              <td>{{ ev.number }}</td>
              <td>{{ ev.code_prefix }}</td>
              <td>{{ ev.year }}</td>
              <td>{{ ev.cycle }}</td>
              <td>{{ ev.comment_count }}</td>
              <td :style="{ color: sentimentColor(ev.average_compound), fontWeight: 600 }">
                {{ ev.average_compound != null ? ev.average_compound.toFixed(2) : '—' }}
              </td>
              <td>
                <span v-if="ev.overall_label" :class="['badge', ev.overall_label]">
                  {{ sentimentEmoji(ev.overall_label) }} {{ ev.overall_label }}
                </span>
                <span v-else class="badge">—</span>
              </td>
              <td>
                <button class="btn-detail" @click="openDetail(ev.id)">Ver detalle →</button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pager -->
        <div class="pager">
          <button class="pager-btn" :disabled="evalPage === 1" @click="goToPage(1)">«</button>
          <button class="pager-btn" :disabled="evalPage === 1" @click="goToPage(evalPage - 1)">‹</button>
          <span class="pager-info">Página {{ evalPage }} de {{ evalPages }}</span>
          <button class="pager-btn" :disabled="evalPage === evalPages" @click="goToPage(evalPage + 1)">›</button>
          <button class="pager-btn" :disabled="evalPage === evalPages" @click="goToPage(evalPages)">»</button>
          <select class="pager-size" :value="evalPageSize" @change="changePageSize($event.target.value)">
            <option value="25">25 / pág.</option>
            <option value="50">50 / pág.</option>
            <option value="100">100 / pág.</option>
          </select>
        </div>
      </div>
    </template>

    <!-- ── Detail panel ── -->
    <div v-if="detail" class="overlay" @click.self="detail = null">
      <div class="panel">
        <div class="panel-header">
          <div>
            <h2>Evaluación No. {{ detail.number }}</h2>
            <p class="panel-meta">{{ detail.year }} — Ciclo {{ detail.cycle }} — Código {{ detail.code_prefix }}</p>
          </div>
          <div class="panel-summary">
            <span :class="['badge', detail.overall_label]" style="font-size:.95rem; padding:.3rem .9rem">
              {{ sentimentEmoji(detail.overall_label) }} {{ detail.overall_label }}
            </span>
            <span class="avg-score" :style="{ color: sentimentColor(detail.average_compound) }">
              {{ detail.average_compound?.toFixed(2) }}
            </span>
          </div>
          <button class="close-btn" @click="detail = null">✕</button>
        </div>

        <div class="comment-table-wrap">
          <table class="comment-table">
            <thead>
              <tr>
                <th>Comentario original</th>
                <th>Traducción (EN)</th>
                <th>Lemas</th>
                <th>Puntaje</th>
                <th>Sentimiento</th>
                <th>Tópico</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in detail.comments" :key="c.id" :class="c.label">
                <td>{{ c.comment }}</td>
                <td>{{ c.comment_en ?? '—' }}</td>
                <td class="lemmas">{{ c.comment_preprocessed ?? '—' }}</td>
                <td :style="{ color: sentimentColor(c.compound), fontWeight: 600 }">
                  {{ c.compound != null ? c.compound.toFixed(2) : '—' }}
                </td>
                <td>
                  <span v-if="c.label" :class="['badge', c.label]">
                    {{ sentimentEmoji(c.label) }} {{ c.label }}
                  </span>
                  <span v-else class="badge">—</span>
                </td>
                <td class="topic-cell">
                  <span v-if="c.topic_keywords" class="topic-inline">
                    <span class="topic-id-badge">T{{ c.topic_id }}</span>
                    {{ c.topic_keywords.slice(0, 3).join(', ') }}
                  </span>
                  <span v-else class="dim">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { Line, Bar } from "vue-chartjs";
import {
  Chart as ChartJS,
  LineElement, BarElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler,
} from "chart.js";
import api from "../api";

ChartJS.register(LineElement, BarElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler);

const loading = ref(true);
const summary = ref([]);
const evaluations = ref([]);
const evalTotal = ref(0);
const evalPage = ref(1);
const evalPages = ref(1);
const evalPageSize = ref(25);
const detail = ref(null);

// ── Secondary charts ─────────────────────────────────────────────────────────
const byCode  = ref([]);
const byCycle = ref([]);

// ── Filters ──────────────────────────────────────────────────────────────────
const filterOptions = ref({ years: [], cycles: [], codes: [] });
const filterYear  = ref(null);
const filterCycle = ref(null);
const filterCode  = ref(null);

// ── Topics ──────────────────────────────────────────────────────────────────
const topics = ref([]);
const topicsDate = ref("");
const topicRunning = ref(false);
const nTopics = ref(5);
let topicPollTimer = null;


async function loadTopics() {
  const res = await api.get("/reports/topics");
  topics.value = res.data;
  if (res.data.length) {
    topicsDate.value = new Date(res.data[0].created_at).toLocaleString("es-GT");
  }
}

async function runTopics() {
  topicRunning.value = true;
  const res = await api.post(`/reports/run-topics?n_topics=${nTopics.value}`);
  const taskId = res.data.task_id;
  topicPollTimer = setInterval(async () => {
    const status = await api.get(`/reports/topics-status/${taskId}`);
    if (status.data.ready) {
      clearInterval(topicPollTimer);
      topicPollTimer = null;
      topicRunning.value = false;
      await loadTopics();
      // Reload detail panel if open (to refresh topic assignments)
      if (detail.value) {
        const r = await api.get(`/reports/evaluations/${detail.value.id}`);
        detail.value = r.data;
      }
    }
  }, 2000);
}

onUnmounted(() => {
  if (topicPollTimer) clearInterval(topicPollTimer);
});

async function loadEvaluations(page = evalPage.value, pageSize = evalPageSize.value) {
  const params = await buildFilterParams();
  params.set("page", page);
  params.set("page_size", pageSize);
  const res = await api.get(`/reports/evaluations?${params}`);
  evaluations.value = res.data.items;
  evalTotal.value = res.data.total;
  evalPage.value = res.data.page;
  evalPages.value = res.data.pages;
}

async function buildFilterParams() {
  const p = new URLSearchParams();
  if (filterYear.value)  p.set("year", filterYear.value);
  if (filterCycle.value) p.set("cycle", filterCycle.value);
  if (filterCode.value)  p.set("code_prefix", filterCode.value);
  return p;
}

async function loadSummary() {
  const p = await buildFilterParams();
  const [s, bc, bcy] = await Promise.all([
    api.get(`/reports/summary?${p}`),
    api.get(`/reports/summary/by-code?${p}`),
    api.get(`/reports/summary/by-cycle?${p}`),
  ]);
  summary.value = s.data;
  byCode.value  = bc.data;
  byCycle.value = bcy.data;
}

async function applyFilters() {
  await Promise.all([loadSummary(), loadEvaluations(1)]);
}

async function goToPage(page) {
  await loadEvaluations(page);
}

async function changePageSize(size) {
  evalPageSize.value = Number(size);
  await loadEvaluations(1);
}

onMounted(async () => {
  const [f] = await Promise.all([
    api.get("/reports/filters"),
    loadSummary(),
    loadEvaluations(),
  ]);
  filterOptions.value = f.data;
  loading.value = false;
  await loadTopics();
});


async function openDetail(id) {
  const res = await api.get(`/reports/evaluations/${id}`);
  detail.value = res.data;
}

// ── Chart ──────────────────────────────────────────────────────────────────
const chartData = computed(() => ({
  labels: summary.value.map((r) => r.label),
  datasets: [
    {
      label: "😊 Positivo",
      data: summary.value.map((r) => r.positive),
      borderColor: "#4caf8a",
      backgroundColor: "rgba(76,175,138,.1)",
      pointBackgroundColor: "#4caf8a",
      tension: 0.3,
      fill: false,
    },
    {
      label: "😐 Neutro",
      data: summary.value.map((r) => r.neutral),
      borderColor: "#f5a623",
      backgroundColor: "rgba(245,166,35,.1)",
      pointBackgroundColor: "#f5a623",
      tension: 0.3,
      fill: false,
    },
    {
      label: "😟 Negativo",
      data: summary.value.map((r) => r.negative),
      borderColor: "#e94560",
      backgroundColor: "rgba(233,69,96,.1)",
      pointBackgroundColor: "#e94560",
      tension: 0.3,
      fill: false,
    },
  ],
}));

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: "top" },
    tooltip: { mode: "index", intersect: false },
  },
  scales: {
    x: { grid: { display: false } },
    y: { beginAtZero: true, ticks: { stepSize: 1 } },
  },
};

function barDatasets(rows) {
  return [
    { label: "😊 Positivo", data: rows.map((r) => r.positive), backgroundColor: "#4caf8a" },
    { label: "😐 Neutro",   data: rows.map((r) => r.neutral),  backgroundColor: "#f5a623" },
    { label: "😟 Negativo", data: rows.map((r) => r.negative), backgroundColor: "#e94560" },
  ];
}

const byCodeData = computed(() => ({
  labels: byCode.value.map((r) => r.label),
  datasets: barDatasets(byCode.value),
}));

const byCycleData = computed(() => ({
  labels: byCycle.value.map((r) => r.label),
  datasets: barDatasets(byCycle.value),
}));

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: "top" },
    tooltip: { mode: "index", intersect: false },
  },
  scales: {
    x: { grid: { display: false } },
    y: { beginAtZero: true },
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────
function sentimentColor(score) {
  if (score == null) return "#999";
  if (score >= 0.05) return "#1a7a4a";
  if (score <= -0.05) return "#c0392b";
  return "#b26a00";
}

function sentimentEmoji(label) {
  return { positive: "😊", neutral: "😐", negative: "😟" }[label] ?? "";
}
</script>

<style scoped>
h1 { margin-bottom: .4rem; }
.subtitle { color: #555; margin-bottom: 0; }
.loading, .empty { color: #888; font-style: italic; background: #fff; padding: 2rem;
                   border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }

.page-header { display: flex; align-items: flex-start; justify-content: space-between;
               gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.header-actions { display: flex; align-items: center; gap: .75rem; flex-shrink: 0; }
.topic-controls { display: flex; align-items: center; gap: .5rem; }
.topics-label { font-size: .85rem; color: #555; font-weight: 600; }
.n-topics-input { width: 52px; padding: .3rem .5rem; border: 1px solid #ccc; border-radius: 6px;
                  font-size: .88rem; text-align: center; }
.btn-topics { background: #1a1a2e; color: #fff; border: none; padding: .42rem 1rem;
              border-radius: 8px; font-size: .88rem; cursor: pointer; transition: opacity .15s; }
.btn-topics:disabled { opacity: .55; cursor: not-allowed; }
.btn-topics:not(:disabled):hover { opacity: .85; }

/* Topics grid */
.topics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
               gap: 1rem; margin-top: .75rem; }
.topic-card { background: #f8f8ff; border: 1px solid #e0e0f0; border-radius: 10px;
              padding: .85rem 1rem; }
.topic-num { font-size: .75rem; font-weight: 700; color: #1a1a2e; text-transform: uppercase;
             letter-spacing: .05em; margin-bottom: .45rem; }
.topic-wc { display: flex; flex-wrap: wrap; gap: .3rem .5rem; align-items: baseline;
            padding: .4rem 0; min-height: 80px; }
.wc-word { font-weight: 600; line-height: 1.3; transition: opacity .15s; cursor: default; }
.topic-sentiment-bar { display: flex; height: 6px; border-radius: 4px; overflow: hidden;
                       margin: .55rem 0 .3rem; background: #eee; }
.tsb-pos { background: #4caf8a; }
.tsb-neu { background: #f5a623; }
.tsb-neg { background: #e94560; }
.topic-sentiment-legend { display: flex; gap: .5rem; }
.tsb-label { font-size: .72rem; font-weight: 600; }
.tsb-label.pos { color: #1a7a4a; }
.tsb-label.neu { color: #b26a00; }
.tsb-label.neg { color: #c0392b; }
.tsb-total { font-size: .75rem; color: #999; margin-top: .25rem; }

.card { background: #fff; border-radius: 12px; padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.card h2 { margin-bottom: .25rem; }
.card-sub { color: #777; font-size: .88rem; margin-bottom: 1.25rem; }
.chart-wrap { height: 320px; }
.chart-wrap-sm { height: 160px; }
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1.5rem; }

/* Table */
.eval-table { width: 100%; border-collapse: collapse; font-size: .9rem; margin-top: .75rem; }
.eval-table th { text-align: left; padding: .6rem .8rem; border-bottom: 2px solid #eee;
                 color: #555; font-size: .8rem; text-transform: uppercase; }
.eval-table td { padding: .65rem .8rem; border-bottom: 1px solid #f0f0f0; }
.eval-table tr:last-child td { border-bottom: none; }
.eval-table tr:hover td { background: #fafafa; }

.badge { font-size: .78rem; font-weight: 600; padding: .2rem .6rem; border-radius: 20px; }
.badge.positive { background: #e6f9f0; color: #1a7a4a; }
.badge.neutral  { background: #fff8e1; color: #b26a00; }
.badge.negative { background: #fdecea; color: #c0392b; }

.btn-detail { background: none; border: 1px solid #1a1a2e; color: #1a1a2e; padding: .3rem .7rem;
              border-radius: 6px; font-size: .82rem; cursor: pointer; transition: all .15s; }
.btn-detail:hover { background: #1a1a2e; color: #fff; }

.table-header { display: flex; align-items: baseline; gap: .75rem; margin-bottom: .75rem; }
.table-header h2 { margin: 0; }
.total-count { font-size: .82rem; color: #999; }

.filters-bar { display: flex; gap: .6rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.filters-bar select { font-size: .85rem; border: 1px solid #ddd; border-radius: 6px;
                      padding: .35rem .65rem; color: #333; cursor: pointer; background: #fff;
                      box-shadow: 0 1px 3px rgba(0,0,0,.06); }

.pager { display: flex; align-items: center; gap: .4rem; justify-content: center;
         padding-top: 1rem; margin-top: .5rem; border-top: 1px solid #f0f0f0; }
.pager-btn { background: none; border: 1px solid #ddd; border-radius: 6px; padding: .25rem .6rem;
             font-size: .9rem; cursor: pointer; transition: all .15s; color: #333; line-height: 1; }
.pager-btn:hover:not(:disabled) { background: #1a1a2e; color: #fff; border-color: #1a1a2e; }
.pager-btn:disabled { opacity: .35; cursor: not-allowed; }
.pager-info { font-size: .85rem; color: #555; padding: 0 .5rem; }
.pager-size { font-size: .82rem; border: 1px solid #ddd; border-radius: 6px; padding: .25rem .4rem;
              color: #555; cursor: pointer; margin-left: .5rem; }

/* Detail overlay */
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 100;
           display: flex; align-items: flex-start; justify-content: center; padding: 2rem 1rem; overflow-y: auto; }
.panel { background: #fff; border-radius: 14px; width: 100%; max-width: 1000px;
         box-shadow: 0 8px 40px rgba(0,0,0,.2); overflow: hidden; }
.panel-header { display: flex; align-items: flex-start; gap: 1rem; padding: 1.25rem 1.5rem;
                border-bottom: 1px solid #eee; }
.panel-header h2 { margin: 0 0 .2rem; }
.panel-meta { color: #777; font-size: .88rem; margin: 0; }
.panel-summary { margin-left: auto; display: flex; align-items: center; gap: .75rem; }
.avg-score { font-size: 1.4rem; font-weight: 700; }
.close-btn { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #999;
             padding: .25rem; align-self: flex-start; }

.comment-table-wrap { overflow-x: auto; padding: 1rem 1.5rem 1.5rem; }
.comment-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.comment-table th { text-align: left; padding: .6rem .75rem; border-bottom: 2px solid #eee;
                    color: #555; font-size: .78rem; text-transform: uppercase; white-space: nowrap; }
.comment-table td { padding: .65rem .75rem; border-bottom: 1px solid #f0f0f0; vertical-align: top; line-height: 1.5; }
.comment-table tr:last-child td { border-bottom: none; }
.comment-table tr.positive td:first-child { border-left: 3px solid #4caf8a; }
.comment-table tr.neutral  td:first-child { border-left: 3px solid #f5a623; }
.comment-table tr.negative td:first-child { border-left: 3px solid #e94560; }
.lemmas { color: #888; font-size: .8rem; font-family: monospace; max-width: 220px; word-break: break-word; }
.topic-cell { font-size: .8rem; color: #555; max-width: 180px; }
.topic-inline { display: flex; align-items: center; gap: .35rem; flex-wrap: wrap; }
.topic-id-badge { background: #e8eaf6; color: #3949ab; font-size: .72rem; font-weight: 700;
                  padding: .1rem .4rem; border-radius: 10px; white-space: nowrap; }
.dim { color: #ccc; }
</style>
