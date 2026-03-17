# Análisis de Evaluaciones Docentes — Universidad del Valle de Guatemala

Sistema de análisis automático de evaluaciones de profesores. Procesa PDFs generados por el sistema UVG y comentarios importados desde CSV, extrae comentarios de estudiantes, los traduce al inglés, aplica preprocesamiento lingüístico, análisis de sentimiento y modelado de tópicos, y genera reportes comparativos por año y ciclo académico.

---

## Tabla de contenidos

1. [Arquitectura general](#arquitectura-general)
2. [Estructura del proyecto](#estructura-del-proyecto)
3. [Esquema de base de datos](#esquema-de-base-de-datos)
4. [Pipeline de procesamiento](#pipeline-de-procesamiento)
5. [Extracción de PDF](#1-extracción-de-pdf)
6. [Importación CSV](#2-importación-csv)
7. [Traducción automática](#3-traducción-automática)
8. [Preprocesamiento de texto](#4-preprocesamiento-de-texto)
9. [Análisis de sentimiento](#5-análisis-de-sentimiento)
10. [Modelado de tópicos](#6-modelado-de-tópicos)
11. [API — Endpoints principales](#api--endpoints-principales)
12. [Configuración y arranque](#configuración-y-arranque)
13. [Variables de entorno](#variables-de-entorno)
14. [Scripts de utilidad](#scripts-de-utilidad)

---

## Arquitectura general

El sistema está compuesto por seis servicios Docker que se comunican en una red interna:

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
                               ┌─────────────────┐     ┌─────────────────┐
                               │      MySQL       │     │  LibreTranslate  │
                               │  (datos + NLP)   │     │  ES → EN (local) │
                               └─────────────────┘     └─────────────────┘
```

| Servicio | Imagen / Stack | Puerto |
|---|---|---|
| `teacher_frontend` | Vue 3 + Vite + Chart.js | 5173 |
| `teacher_backend` | FastAPI + Uvicorn | 8000 |
| `teacher_worker` | Celery 5 (misma imagen que backend) | — |
| `teacher_redis` | Redis 7 Alpine | 6379 (interno) |
| `teacher_libretranslate` | LibreTranslate (ES+EN) | 5000 (interno) |
| Base de datos | MySQL 8 (producción) / externa (dev) | 3306 |

### Flujo de una carga de PDF

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
  translating  → traduce comentarios ES → EN (DeepL o LibreTranslate)
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
├── docker-compose.yml.example  # plantilla para producción (incluye MySQL + Adminer)
├── .env                        # variables de entorno (no en git)
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── rescore.py              # re-puntuar sentimiento en comentarios traducidos
│   ├── translate.py            # traducir comentarios sin comment_en
│   ├── import_csv.py           # importar comentarios desde CSV masivo
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
│       │   └── reports.py      # resumen, evaluaciones, filtros, tópicos
│       ├── services/
│       │   ├── pdf_parser.py   # extracción de texto y campos
│       │   ├── translation.py  # DeepL (primario) + LibreTranslate (fallback)
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
            └── ReportsView.vue # filtros + gráfico + tópicos + tabla paginada + panel detalle
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
| `comment_en` | TEXT | Traducción al inglés (DeepL o LibreTranslate) |
| `comment_preprocessed` | TEXT | Lemas tokenizados para topic modeling |
| `sentiment_compound` | FLOAT | Puntaje compuesto −1.0 a +1.0 |
| `sentiment_label_id` | TINYINT | FK → positive / neutral / negative |
| `topic_id` | INT | FK → topics(id), asignado por NMF |

### Columnas clave de `evaluations`

| Columna | Tipo | Descripción |
|---|---|---|
| `job_id` | VARCHAR(36) | UUID del job (PDFs) o `csv:{materia}:{prof}:{ciclo}:{año}` (CSV) |
| `number` | INT | Número de evaluación (PDFs) o secuencial (CSV) |
| `code_prefix` | VARCHAR(2) | Prefijo del código de carrera (ej. `BE`, `CC`) |
| `cycle` | INT | Ciclo académico |
| `year` | SMALLINT | Año académico |

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

## 2. Importación CSV

**Script:** `backend/import_csv.py`

Permite importar comentarios en masa desde un archivo CSV con el siguiente formato:

```
comments_texts,idProfesor,idMateria,ciclo,anio
muy buen docente.,144968,BE2001 - 10,1,2023
```

Cada combinación única de `(idProfesor, idMateria, ciclo, anio)` genera un registro `Evaluation`. Los comentarios se insertan, se traducen y se puntúan en el mismo proceso.

```bash
# Importar + traducir + puntuar
docker compose exec backend python import_csv.py data/archivo.csv

# Solo importar (sin traducir ni puntuar)
docker compose exec backend python import_csv.py data/archivo.csv --no-translate --no-sentiment

# Importar y traducir (puntuar después con rescore.py)
docker compose exec backend python import_csv.py data/archivo.csv --no-sentiment
```

**Deduplicación:** si se vuelve a correr con el mismo archivo, los grupos ya importados se omiten automáticamente.

---

## 3. Traducción automática

**Archivo:** `app/services/translation.py`
**Servicios:** DeepL (primario) → LibreTranslate (fallback automático)

Los comentarios en español se traducen al inglés (`ES → EN-US`). El sistema elige el motor de traducción automáticamente:

1. Si `DEEPL_API_KEY` está configurado → usa **DeepL** (mejor calidad).
2. Si DeepL falla o la cuota se agota → cae automáticamente a **LibreTranslate** (autoalojado, sin límites).

LibreTranslate corre como servicio Docker dentro de la misma red. Solo carga los modelos ES↔EN (`LT_LOAD_ONLY=es,en`) para reducir el uso de memoria.

El resultado se almacena en `comment_en`. Solo se procesan comentarios donde `comment_en IS NULL`.

---

## 4. Preprocesamiento de texto

**Archivo:** `app/services/sentiment.py` — función `preprocessing()`
**Librerías:** `nltk`

El texto en inglés pasa por una cadena de transformaciones antes del análisis de tópicos. El objetivo es reducir el texto a sus **lemas informativos**:

```
Texto original (EN):
"He always takes the time to answer our questions in class."

Tokenización → filtro stop words → filtro longitud (≥3) → minúsculas → lematización

Resultado almacenado en comment_preprocessed:
"always take time answer question class"
```

> Este texto preprocesado se usa exclusivamente para **topic modeling**. El análisis de sentimiento corre sobre el texto en inglés **sin procesar** para preservar el contexto lingüístico.

---

## 5. Análisis de sentimiento

**Archivo:** `app/services/sentiment.py` — función `run_sentiment()`
**Librerías:** `vaderSentiment`, `textblob`

### Modelo ensemble: VADER + TextBlob

| Modelo | Fortaleza | Debilidad |
|---|---|---|
| **VADER** | Slang, puntuación, mayúsculas, intensificadores | Negación de palabras muy negativas |
| **TextBlob** | Negación pattern-based ("no X" → positivo) | Menos sensible a matices de intensidad |

```
compound = (vader_compound + textblob_polarity) / 2

compound ≥  0.05  →  positive
compound ≤ -0.05  →  negative
entre ambos       →  neutral
```

### Calibración del léxico para contexto educativo

| Palabra | Puntaje calibrado | Razón |
|---|---|---|
| `doubts`, `questions` | 0.0 | Preguntar es parte del aprendizaje |
| `hassle`, `problem` | −0.5 | "no problems" → la negación debe funcionar |
| `understandable`, `mastery` | +2.5 | Calidad docente importante |
| `patient`, `dedicated` | +2.0 | Paciencia y dedicación muy valoradas |
| `available`, `organized` | +1.5 | Disponibilidad y organización del docente |

---

## 6. Modelado de tópicos

**Archivo:** `app/services/topic_modeling.py`
**Librería:** `scikit-learn` (TF-IDF + NMF)

El modelado de tópicos es **global**: corre sobre todos los comentarios preprocesados de la base de datos al mismo tiempo. Se dispara **bajo demanda** desde el botón "Analizar tópicos" en la vista de Reportes.

```
1. Obtener todos los comment_preprocessed (no nulos)
2. Vectorizar con TF-IDF (max_features=1000)
3. Factorizar con NMF (n_components=n_topics, default 5)
4. Eliminar tópicos anteriores (ON DELETE SET NULL limpia topic_id)
5. Insertar nuevos tópicos con keywords (top 8 palabras por componente)
6. Asignar topic_id a cada comentario (argmax de la matriz W)
```

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
| `GET` | `/api/reports/summary` | Conteos positivo/neutro/negativo por año y ciclo (filtrable) |
| `GET` | `/api/reports/filters` | Valores disponibles para los filtros (años, ciclos, códigos) |
| `GET` | `/api/reports/evaluations` | Tabla paginada de evaluaciones con puntaje promedio (filtrable) |
| `GET` | `/api/reports/evaluations/{id}` | Detalle completo: comentarios, traducción, lemas, puntaje, tópico |

Parámetros de filtro disponibles en `/summary` y `/evaluations`: `year`, `cycle`, `code_prefix`.
Parámetros de paginación en `/evaluations`: `page` (default 1), `page_size` (default 25).

### Tópicos

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/reports/run-topics?n_topics=5` | Encola análisis NMF global, retorna `{task_id}` |
| `GET` | `/api/reports/topics-status/{task_id}` | Estado de la tarea (PENDING / STARTED / SUCCESS / FAILURE) |
| `GET` | `/api/reports/topics` | Lista de tópicos actuales con keywords y conteo |

Documentación interactiva disponible en: `http://localhost:8000/api/docs`

---

## Configuración y arranque

### Requisitos

- Docker y Docker Compose
- MySQL 8 accesible (ver `docker-compose.yml.example` para producción con MySQL incluido)

### Primera vez

```bash
# 1. Copiar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 2. Construir y levantar todos los servicios
docker compose up --build
```

> LibreTranslate descarga el modelo ES↔EN (~100 MB) en el primer arranque. Esperar a que el log indique `Listening on 0.0.0.0:5000` antes de lanzar traducciones.

### Arranque normal

```bash
docker compose up
```

---

## Scripts de utilidad

| Script | Descripción | Comando |
|---|---|---|
| `import_csv.py` | Importar comentarios desde CSV | `docker compose exec backend python import_csv.py data/archivo.csv` |
| `translate.py` | Traducir comentarios sin `comment_en` | `docker compose exec backend python translate.py` |
| `rescore.py` | Re-puntuar sentimiento en comentarios traducidos | `docker compose exec backend python rescore.py` |
| `rescore.py --force` | Re-puntuar todos (incluye ya puntuados) | `docker compose exec backend python rescore.py --force` |
| `migrate_topics.py` | Migrar BD existente para soporte de tópicos | `docker compose exec backend python migrate_topics.py` |

### Flujo típico para importación masiva

```bash
# 1. Importar CSV (solo inserta, sin traducir ni puntuar)
docker compose exec backend python import_csv.py data/archivo.csv --no-translate --no-sentiment

# 2. Traducir (cuando tengas créditos / LibreTranslate listo)
docker compose exec backend python translate.py

# 3. Puntuar sentimiento
docker compose exec backend python rescore.py
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DB_HOST` | Host de la base de datos | `db` |
| `DB_PORT` | Puerto MySQL | `3306` |
| `DB_NAME` | Nombre de la base de datos | `teacher_analysis` |
| `DB_USER` | Usuario de la BD | `teacher_user` |
| `DB_PASSWORD` | Contraseña de la BD | — |
| `DB_ROOT_PASSWORD` | Contraseña root MySQL | — |
| `SECRET_KEY` | Clave secreta de la app (≥32 chars) | — |
| `DEEPL_API_KEY` | API key de DeepL (opcional) | — |
| `LIBRETRANSLATE_URL` | URL del servicio LibreTranslate | `http://libretranslate:5000` |
| `REDIS_URL` | URL del broker Redis | `redis://redis:6379/0` |
| `ALLOWED_ORIGINS` | CORS origins permitidos | `http://localhost:5173` |
| `BACKEND_PORT` | Puerto del backend | `8000` |
| `FRONTEND_PORT` | Puerto del frontend | `5173` |
| `ADMINER_PORT` | Puerto de Adminer (producción) | `8080` |

---

## Próximas fases

- **Comparación entre docentes** — ranking por puntaje promedio y por código de carrera
- **Evolución temporal** — gráficas de tendencia de sentimiento por docente a lo largo de ciclos
- **Exportación** — descarga de reportes en PDF o Excel
