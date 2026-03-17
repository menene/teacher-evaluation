"""PDF parsing — supports single and multi-evaluation PDFs."""
import re
import pdfplumber


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_int(s: str) -> int:
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0


def _is_main_page(text: str) -> bool:
    """True for the scoring summary page that starts each evaluation block."""
    return "TABLA DE EVALUACIÓN" in text and "AUTOEVALUACIÓN" not in text


# ── Field extraction (operates on a list of page texts for one block) ──────────

def _extract_fields(pages: list[str]) -> dict:
    """Extract metadata from an evaluation block (all pages joined)."""
    full = "\n".join(pages)
    result = {}

    # Number: try inline first (pages 2/3 have it on same line), then column fallback
    m = re.search(r"Evaluaci[oó]n\s+No\.?\s*:\s*([\d,\.]+)", full, re.IGNORECASE)
    if not m:
        m = re.search(r"([\d,]+)\s*\nESTUDIANTES ASIGNADOS", full, re.IGNORECASE)
    if m:
        result["number"] = _to_int(m.group(1))

    m = re.search(r"A[ÑN]O:\s*([\d,]+)", full, re.IGNORECASE)
    if m:
        result["year"] = _to_int(m.group(1))

    m = re.search(r"CICLO:\s*(\d+)", full, re.IGNORECASE)
    if m:
        result["cycle"] = int(m.group(1))

    m = re.search(r"C[OÓ]DIGO[:\s]+([A-Za-z]{2})", full, re.IGNORECASE)
    if m:
        result["code_prefix"] = m.group(1).upper()

    return result


def _extract_comments(pages: list[str]) -> list[str]:
    """Extract student comments from the non-main pages of a block."""
    comments: list[str] = []
    for text in pages:
        if "COMENTARIOS DE ESTUDIANTES" not in text:
            continue
        block = re.split(r"COMENTARIOS DE ESTUDIANTES", text, maxsplit=1)[-1]
        block = re.split(r"NOTA:\s*LOS COMENTARIOS", block)[0]
        for entry in re.split(r"•", block):
            comment = " ".join(entry.split())
            if comment:
                comments.append(comment)
    return comments


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_pdf(file_path: str) -> list[dict]:
    """
    Parse a PDF and return a list of evaluation dicts, one per evaluation found.
    Each dict has keys: fields (dict), comments (list[str]).
    Works for both single-evaluation and multi-evaluation PDFs.
    """
    with pdfplumber.open(file_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]

    # Find the index of every main/scoring page — these are block boundaries
    boundaries = [i for i, text in enumerate(pages) if _is_main_page(text)]

    if not boundaries:
        # Fallback: treat the whole PDF as one block
        boundaries = [0]

    evaluations = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(pages)
        block = pages[start:end]
        evaluations.append({
            "fields": _extract_fields(block),
            "comments": _extract_comments(block[1:]),
        })

    return evaluations


# ── Legacy wrappers (kept for /upload/analyze) ─────────────────────────────────

def parse_first_page(file_path: str) -> dict:
    results = parse_pdf(file_path)
    return results[0]["fields"] if results else {}


def parse_comments(file_path: str) -> list[str]:
    results = parse_pdf(file_path)
    return results[0]["comments"] if results else []
