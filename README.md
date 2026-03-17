# Análisis de Evaluaciones Docentes — Universidad del Valle de Guatemala

Sistema de análisis automático de evaluaciones de profesores. Procesa los PDFs generados por el sistema UVG, extrae comentarios de estudiantes, los traduce al inglés, aplica preprocesamiento lingüístico, análisis de sentimiento y modelado de tópicos, y genera reportes comparativos por año y ciclo académico.

---

## Tabla de contenidos

1. [Arquitectura general](#arquitectura-general)
2. [Estructura del proyecto](#estructura-del-proyecto)
3. [Esquema de base de datos](#esquema-de-base-de-datos)
4. [Pipeline de procesamiento](#pipeline-de-procesamiento)
5. [Extracción de PDF](#1-extracción-de-pdf)
6. [Traducción automática](#2-traducción-automática)
7. [Preprocesamiento de texto](#3-preprocesamiento-de-texto)
8. [Análisis de sentimiento](#4-análisis-de-sentimiento)
9. [Modelado de tópicos](#5-modelado-de-tópicos)
10. [API — Endpoints principales](#api--endpoints-principales)
11. [Configuración y arranque](#configuración-y-arranque)
12. [Variables de entorno](#variables-de-entorno)

---

## Arquitectura general

El sistema está compuesto por cuatro servicios Docker que se comunican en una red interna:

```
┌─────────────┐     HTTP      ┌─────────────────┐
│   Frontend  │ ─────────────▶│     Backend      │
│  Vue 3 +    │               │  FastAPI 0.111   │
│  Chart.js   │               │  Python 3.12     │
└─────────────┘               └────────┬─────────┘
                                        │ encola tarea
                                        ▼
                               ┌─────────────────┐
                               │      Redis       │
                               │  (broker/backend)│
                               └────────┬─────────┘
                                        │ despacha
                                        ▼
                               ┌─────────────────┐
                               │  Celery Worker   │
                               │  (pipeline NLP)  │
                               └────────┬─────────┘
                                        │ persiste
                                        ▼
                               ┌─────────────────┐
                               │    MariaDB       │
                               │  (datos + NLP)   │
                               └─────────────────┘
```

| Servicio | Imagen / Stack | Puerto |
|---|---|---|
| `teacher_frontend` | Vue 3 + Vite + Chart.js | 5173 |
| `teacher_backend` | FastAPI + Uvicorn | 8000 |
| `teacher_worker` | Celery 5 (mismo imagen que backend) | — |
| `teacher_redis` | Redis 7 Alpine | 6379 (interno) |
| Base de datos | MariaDB (externa) | 3306 |

### Flujo de una carga

```
Usuario sube PDF
      │
      ▼
POST /api/evaluations/upload
      │  guarda PDF en /app/uploads/{job_id}.pdf
      │  crea registro Job (status: pending)
      │  encola tarea Celery
      │  retorna {job_id} inmediatamente
      │
      ▼
Frontend hace polling GET /api/jobs/{job_id} cada 1.5 s
      │
      ▼
Worker ejecuta pipeline:
  parsing      → extrae evaluaciones del PDF
  translating  → traduce comentarios ES → EN (DeepL)
  sentiment    → preprocesa + puntúa (VADER + TextBlob)
  complete     ✓

Usuario pulsa "Analizar tópicos" en Reportes
      │
      ▼
POST /api/reports/run-topics
      │  encola run_topic_modeling_task en Celery
      │  retorna {task_id}
      │
      ▼
Frontend hace polling GET /api/reports/topics-status/{task_id} cada 2 s
      │
      ▼
Worker ejecuta NMF global sobre todos los comentarios preprocesados
  → elimina tópicos anteriores
  → inserta tópicos nuevos
  → asigna topic_id a cada comentario
  complete     ✓
```

---

## Estructura del proyecto

```
teacher-analysis/
├── docker-compose.yml
├── .env                        # variables de entorno (no en git)
├── .env.example
├── db/
│   └── init.sql                # esquema inicial de MariaDB
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── rescore.py              # re-puntuar sentimiento en toda la BD
│   ├── migrate_topics.py       # migración: añade tabla topics y columna topic_id
│   └── app/
│       ├── main.py             # aplicación FastAPI
│       ├── core/
│       │   └── config.py       # configuración desde .env
│       ├── db/
│       │   └── session.py      # sesión SQLAlchemy
│       ├── models/
│       │   ├── evaluation.py   # Evaluation, EvaluationComment, SentimentLabel, Topic
│       │   └── job.py          # Job (seguimiento del pipeline)
│       ├── routers/
│       │   ├── evaluations.py  # upload, upload/analyze
│       │   ├── jobs.py         # estado del job con resultados
│       │   └── reports.py      # resumen, evaluaciones, tópicos
│       ├── services/
│       │   ├── pdf_parser.py   # extracción de texto y campos
│       │   ├── translation.py  # integración DeepL
│       │   ├── sentiment.py    # preprocesamiento + VADER + TextBlob
│       │   └── topic_modeling.py # NMF global + persistencia en BD
│       └── worker/
│           ├── celery_app.py   # configuración Celery
│           └── tasks.py        # process_pdf + run_topic_modeling_task
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── App.vue             # layout + navegación
        ├── api/index.js        # cliente Axios
        ├── router/index.js
        └── views/
            ├── HomeView.vue    # resumen del sistema y stack técnico
            ├── UploadView.vue  # carga + progress bar + resultados
            └── ReportsView.vue # gráfico + tópicos + tabla + panel detalle
```

---

## Esquema de base de datos

```sql
sentiment_labels     -- positivo / neutro / negativo
topics               -- tópicos NMF (keywords + weight)
evaluations          -- metadatos de cada evaluación extraída
evaluation_comments  -- comentarios con traducciones, lemas, puntajes y tópico
jobs                 -- seguimiento del pipeline por archivo subido
```

### Diagrama de relaciones

```
jobs (1) ──────────────────── (N) evaluations
                                       │
                                       │ (1)
                                       ▼
                               evaluation_comments (N)
                                       │           │
                                       │ (N)       │ (N)
                                       ▼           ▼
                               sentiment_labels  topics
                                    (1)            (1)
```

### Columnas clave de `evaluation_comments`

| Columna | Tipo | Descripción |
|---|---|---|
| `comment` | TEXT | Comentario original en español |
| `comment_en` | TEXT | Traducción al inglés (DeepL) |
| `comment_preprocessed` | TEXT | Lemas tokenizados para topic modeling |
| `sentiment_compound` | FLOAT | Puntaje compuesto −1.0 a +1.0 |
| `sentiment_label_id` | TINYINT | FK → positive / neutral / negative |
| `topic_id` | INT | FK → topics(id), asignado por NMF |

### Tabla `topics`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INT | PK auto-incremental |
| `keywords` | TEXT | JSON array con las palabras clave del tópico |
| `weight` | FLOAT | Peso máximo del componente NMF |
| `created_at` | DATETIME | Fecha del último recálculo |

### Estados del Job

```
pending → parsing → translating → sentiment → complete
                                                  │
                                    (duplicado) skipped
                                    (error)     failed
```

---

## Pipeline de procesamiento

El pipeline se ejecuta de forma asíncrona en el **Celery Worker**. Cada archivo PDF subido genera un `Job` con un UUID y pasa por tres etapas automáticas. El modelado de tópicos se ejecuta por separado, bajo demanda.

---

## 1. Extracción de PDF

**Archivo:** `app/services/pdf_parser.py`
**Librería:** `pdfplumber`

El sistema soporta PDFs de una o múltiples evaluaciones. La detección de bloques funciona así:

1. Se extraen todas las páginas como texto plano.
2. Se identifica cada **página principal** de evaluación: cualquier página que contenga `TABLA DE EVALUACIÓN` pero **no** `AUTOEVALUACIÓN`.
3. Cada bloque va desde una página principal hasta la siguiente, formando una evaluación independiente.

```
PDF con 20 páginas (5 evaluaciones × 4 páginas cada una)
│
├─ Página 1  → TABLA DE EVALUACIÓN ✓  → inicio bloque 1
├─ Página 2  → COMENTARIOS DE ESTUDIANTES
├─ Página 3  → AUTOEVALUACIÓN DE ESTUDIANTES
├─ Página 4  → (footer)
├─ Página 5  → TABLA DE EVALUACIÓN ✓  → inicio bloque 2
│  ...
```

**Campos extraídos por evaluación:**

| Campo | Patrón en PDF | Resultado |
|---|---|---|
| Número | `Evaluación No.: 128,253` | `128253` |
| Año | `AÑO: 2,024` | `2024` |
| Ciclo | `CICLO: 1` | `1` |
| Código | `CÓDIGO: CC2005 - 60` | `CC` (primeras 2 letras) |

Los **comentarios** se extraen de las páginas con `COMENTARIOS DE ESTUDIANTES`, delimitados por el carácter `•`. Cada entrada multi-línea se colapsa en una sola cadena.

> Las evaluaciones sin comentarios se omiten y se registra una advertencia en el Job.

---

## 2. Traducción automática

**Archivo:** `app/services/translation.py`
**Servicio:** DeepL API

Los comentarios en español se traducen al inglés (`ES → EN-US`) usando la API de DeepL. La traducción se realiza en lote (todos los comentarios de una evaluación en una sola llamada) para eficiencia.

El resultado se almacena en `comment_en`. Si `DEEPL_API_KEY` no está configurado, este paso se omite con una advertencia.

---

## 3. Preprocesamiento de texto

**Archivo:** `app/services/sentiment.py` — función `preprocessing()`
**Librerías:** `nltk`

El texto en inglés pasa por una cadena de transformaciones antes del análisis de tópicos. El objetivo es reducir el texto a sus **lemas informativos**:

```
Texto original (EN):
"He always takes the time to answer our questions in class."

Tokenización por oraciones y palabras:
['He', 'always', 'takes', 'the', 'time', 'to', 'answer',
 'our', 'questions', 'in', 'class', '.']

Eliminación de stop words (NLTK, inglés):
['always', 'takes', 'time', 'answer', 'questions', 'class', '.']

Filtro de longitud mínima (≥ 3 caracteres):
['always', 'takes', 'time', 'answer', 'questions', 'class']

Normalización a minúsculas:
['always', 'takes', 'time', 'answer', 'questions', 'class']

Lematización (WordNetLemmatizer):
['always', 'take', 'time', 'answer', 'question', 'class']

Resultado almacenado en comment_preprocessed:
"always take time answer question class"
```

> Este texto preprocesado se usa exclusivamente para **topic modeling**. El análisis de sentimiento corre sobre el texto en inglés **sin procesar** para preservar el contexto lingüístico.

---

## 4. Análisis de sentimiento

**Archivo:** `app/services/sentiment.py` — función `run_sentiment()`
**Librerías:** `vaderSentiment`, `textblob`

### Modelo ensemble: VADER + TextBlob

Se usa un ensemble de dos modelos complementarios para mayor robustez:

| Modelo | Fortaleza | Debilidad |
|---|---|---|
| **VADER** | Slang, puntuación, mayúsculas, intensificadores | Negación de palabras muy negativas ("no hassle" → falla) |
| **TextBlob** | Negación pattern-based ("no X" → positivo) | Menos sensible a matices de intensidad |

El puntaje final es el **promedio aritmético** de ambos modelos:

```
compound = (vader_compound + textblob_polarity) / 2
```

### Clasificación

```
compound ≥  0.05  →  positive
compound ≤ -0.05  →  negative
entre ambos       →  neutral
```

### Calibración del léxico para contexto educativo

VADER fue entrenado con texto de redes sociales. Algunas palabras tienen connotaciones distintas en feedback educativo. Se aplica un parche al léxico:

| Palabra | Puntaje VADER original | Puntaje calibrado | Razón |
|---|---|---|---|
| `doubts` | −1.9 | 0.0 | "resolver dudas" es positivo en clase |
| `questions` | −0.5 | 0.0 | preguntar es parte del aprendizaje |
| `hassle` | −2.5 | −0.5 | "no hassle" → la negación debe funcionar |
| `problem` | −2.0 | −0.5 | "no problems" → igual |
| `understandable` | +0.5 | +2.5 | calidad docente importante |
| `mastery` | +0.8 | +2.5 | dominio del tema = muy positivo |
| `patient` | +1.0 | +2.0 | paciencia docente muy valorada |
| `available` | +0.3 | +1.5 | disponibilidad del docente |

> Esta lista se extiende a medida que se identifican nuevos casos mal clasificados.

---

## 5. Modelado de tópicos

**Archivo:** `app/services/topic_modeling.py`
**Librería:** `scikit-learn` (TF-IDF + NMF)

El modelado de tópicos es **global**: corre sobre todos los comentarios preprocesados de la base de datos al mismo tiempo, no por evaluación individual. Se dispara **bajo demanda** desde el botón "Analizar tópicos" en la vista de Reportes.

### Proceso

```
1. Obtener todos los comment_preprocessed de la BD (no nulos)
2. Vectorizar con TF-IDF (max_features=1000, stop_words=english)
3. Factorizar con NMF (n_components=n_topics, default 5)
4. Eliminar tópicos anteriores de la BD (ON DELETE SET NULL limpia topic_id)
5. Insertar nuevos tópicos con sus keywords (top 8 palabras por componente)
6. Asignar topic_id a cada comentario (argmax de la matriz documento-tópico W)
7. Commit
```

### Resultado en la BD

- Tabla `topics`: un registro por tópico con sus palabras clave en JSON.
- `evaluation_comments.topic_id`: FK al tópico dominante de cada comentario.

### Comportamiento con pocos datos

El número de tópicos se ajusta automáticamente: `n_topics = min(n_topics, n_comentarios)`. Con menos de 5 comentarios se generan menos tópicos.

### Interfaz

- **Botón "Analizar tópicos"** en la cabecera de Reportes con selector de cantidad (2–15).
- Mientras corre, el botón muestra "⏳ Analizando…" y se deshabilita.
- Al completar, aparece una **grilla de tarjetas de tópicos** con chips de palabras clave y conteo de comentarios asignados.
- El panel de detalle de evaluación incluye columna **Tópico** con badge `T{id}` y las 3 primeras palabras clave.

---

## API — Endpoints principales

### Evaluaciones

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/evaluations/upload` | Sube PDFs, crea jobs, inicia pipeline |
| `POST` | `/api/evaluations/upload/analyze` | Analiza PDFs sin guardar en BD |
| `GET` | `/api/evaluations/` | Lista todas las evaluaciones |

### Jobs

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/jobs/{job_id}` | Estado del job + resultados cuando complete |

### Reportes

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/reports/summary` | Conteos positivo/neutro/negativo por año y ciclo |
| `GET` | `/api/reports/evaluations` | Tabla de evaluaciones con puntaje promedio |
| `GET` | `/api/reports/evaluations/{id}` | Detalle completo: comentarios, traducción, lemas, puntaje, tópico |

### Tópicos

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/reports/run-topics?n_topics=5` | Encola análisis NMF global, retorna `{task_id}` |
| `GET` | `/api/reports/topics-status/{task_id}` | Estado de la tarea (PENDING / STARTED / SUCCESS / FAILURE) |
| `GET` | `/api/reports/topics` | Lista de tópicos actuales con keywords y conteo de comentarios |

Documentación interactiva disponible en: `http://localhost:8000/api/docs`

---

## Configuración y arranque

### Requisitos

- Docker y Docker Compose
- MariaDB accesible (externa al compose)
- Cuenta en DeepL API (plan gratuito: 500k caracteres/mes)

### Primera vez

```bash
# 1. Copiar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 2. Construir y levantar todos los servicios
docker compose up --build

# La base de datos se inicializa automáticamente con db/init.sql
```

### Arranque normal

```bash
docker compose up
```

### Utilidades

```bash
# Re-puntuar todas las evaluaciones existentes (útil tras ajustar el léxico)
docker compose exec backend python rescore.py

# Migrar BD existente para añadir soporte de tópicos
docker compose exec backend python migrate_topics.py

# Ver logs del worker (pipeline en tiempo real)
docker compose logs -f worker
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DB_HOST` | Host de la base de datos | `db` |
| `DB_PORT` | Puerto MariaDB | `3306` |
| `DB_NAME` | Nombre de la base de datos | `teacher_analysis` |
| `DB_USER` | Usuario de la BD | `teacher_user` |
| `DB_PASSWORD` | Contraseña de la BD | — |
| `DB_ROOT_PASSWORD` | Contraseña root MariaDB | — |
| `SECRET_KEY` | Clave secreta de la app (≥32 chars) | — |
| `DEEPL_API_KEY` | API key de DeepL | — |
| `REDIS_URL` | URL del broker Redis | `redis://redis:6379/0` |
| `ALLOWED_ORIGINS` | CORS origins permitidos | `http://localhost:5173` |
| `BACKEND_PORT` | Puerto del backend | `8000` |
| `FRONTEND_PORT` | Puerto del frontend | `5173` |

---

## Próximas fases

- **Importación CSV** — carga masiva de comentarios desde CSV, con análisis de sentimiento automático y re-ejecución de tópicos al finalizar
- **Comparación entre docentes** — ranking por puntaje promedio y por código de carrera
- **Evolución temporal** — gráficas de tendencia de sentimiento por docente a lo largo de ciclos
- **Exportación** — descarga de reportes en PDF o Excel
