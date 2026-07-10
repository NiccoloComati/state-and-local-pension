"""PDF text access + (diagnostic) keyword page ranking.

The pipeline's default is WHOLE-DOCUMENT extraction: the model receives the
full text layer and locates the table itself (locating across heterogeneous
documents is part of what the ML solves). The keyword ranking below is kept
only as a cheap DIAGNOSTIC (--locate-only) and a possible future cost lever;
it is not part of the extraction flow.

Text-layer only (pypdf). Documents whose content lives in images will come
out empty and need the vision fallback (later).
"""
from pypdf import PdfReader


def _layout_page_text(pl_page, py_page):
    """Layout-preserving text for one page: pdfplumber layout mode (keeps
    column alignment via x-coordinates - essential for tables whose plain
    text collapses into ambiguous whitespace, e.g. Segal-style exhibits with
    interleaved count/salary rows), falling back to pypdf plain extraction
    when layout mode drops the content (it does on some pages)."""
    try:
        text = pl_page.extract_text(layout=True) or ""
    except Exception:
        text = ""
    plain = py_page.extract_text() or ""
    # layout mode occasionally loses the body; fall back if clearly emptier
    if len(text.strip()) < 0.5 * len(plain.strip()):
        return plain
    return text


def full_text(pdf_path):
    """Whole document, layout-preserved, with per-page markers."""
    import pdfplumber
    reader = PdfReader(pdf_path)
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, (pl, py) in enumerate(zip(pdf.pages, reader.pages)):
            parts.append(f"=== PDF PAGE {i + 1} ===\n{_layout_page_text(pl, py)}")
    return "\n\n".join(parts)


def locate_pages(pdf_path, keywords, top_k=5):
    """Return [(page_number_1indexed, score, matched_keywords)], best first."""
    reader = PdfReader(pdf_path)
    scored = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").lower()
        matched = [k for k in keywords if k.lower() in text]
        if matched:
            scored.append((i + 1, len(matched), matched))
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored[:top_k]


def page_text(pdf_path, page_numbers):
    """Layout-preserved text of the given 1-indexed pages (debug lever)."""
    import pdfplumber
    reader = PdfReader(pdf_path)
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in page_numbers:
            parts.append(f"=== PDF PAGE {p} ===\n"
                         f"{_layout_page_text(pdf.pages[p - 1], reader.pages[p - 1])}")
    return "\n\n".join(parts)
