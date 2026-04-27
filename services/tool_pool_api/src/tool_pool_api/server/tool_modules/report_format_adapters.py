"""Phase 4 (R4.2) — format adapters for report deliverables.

Each adapter takes a structured payload (markdown text + indicator
dict) and returns ``(bytes, mime_type, suggested_filename)``. PDF and
XLSX adapters lazy-import their backends so that missing system
dependencies surface as a clean ``ToolError`` instead of an import
failure when the rest of the module loads.

Supported:
    - markdown → text/markdown (raw bytes, no conversion)
    - pdf      → application/pdf via :mod:`reportlab` (preferred) or
                 :mod:`weasyprint` if reportlab is missing
    - xlsx     → application/vnd.openxmlformats-... via :mod:`openpyxl`
"""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from typing import Any

from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────
# Markdown
# ────────────────────────────────────────────────────────────────────────


def to_markdown(*, markdown_body: str, **_: Any) -> tuple[bytes, str, str]:
    body = (markdown_body or "").strip() + "\n"
    return body.encode("utf-8"), "text/markdown", _filename("md")


# ────────────────────────────────────────────────────────────────────────
# PDF
# ────────────────────────────────────────────────────────────────────────


def to_pdf(*, markdown_body: str, title: str, **_: Any) -> tuple[bytes, str, str]:
    """Render markdown to PDF.

    Uses :mod:`reportlab` (pure-Python, easy to ship in containers). The
    converter is intentionally minimal: headings, paragraphs, list items
    and table rows. Anything more elaborate should escalate to a Google
    Doc export.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except ImportError as exc:
        raise ToolError(
            "PDF export requires the optional 'reportlab' dependency. "
            "Install with `poetry add reportlab` to enable."
        ) from exc

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=title or "Relatório",
        leftMargin=42,
        rightMargin=42,
        topMargin=48,
        bottomMargin=48,
    )
    styles = getSampleStyleSheet()
    flow: list[Any] = [Paragraph(_escape(title or "Relatório"), styles["Title"]), Spacer(1, 12)]

    pending_items: list[Any] = []

    def flush_list() -> None:
        if not pending_items:
            return
        flow.append(ListFlowable(pending_items, bulletType="bullet"))
        flow.append(Spacer(1, 6))
        pending_items.clear()

    for raw in (markdown_body or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_list()
            flow.append(Spacer(1, 6))
            continue
        if line.startswith("# "):
            flush_list()
            flow.append(Paragraph(_escape(line[2:].strip()), styles["Heading1"]))
        elif line.startswith("## "):
            flush_list()
            flow.append(Paragraph(_escape(line[3:].strip()), styles["Heading2"]))
        elif line.startswith("### "):
            flush_list()
            flow.append(Paragraph(_escape(line[4:].strip()), styles["Heading3"]))
        elif line.lstrip().startswith(("- ", "* ")):
            pending_items.append(
                ListItem(Paragraph(_escape(line.lstrip()[2:].strip()), styles["BodyText"]))
            )
        elif line.startswith("|") and line.endswith("|"):
            # Render markdown tables as simple monospace lines — keeps the
            # converter dependency-free.
            flush_list()
            flow.append(Paragraph(f"<font face='Courier'>{_escape(line)}</font>", styles["BodyText"]))
        else:
            flush_list()
            flow.append(Paragraph(_escape(line), styles["BodyText"]))

    flush_list()
    doc.build(flow)
    return buffer.getvalue(), "application/pdf", _filename("pdf")


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ────────────────────────────────────────────────────────────────────────
# XLSX
# ────────────────────────────────────────────────────────────────────────


def to_xlsx(
    *,
    markdown_body: str,
    title: str,
    indicators: dict[str, Any] | None = None,
    **_: Any,
) -> tuple[bytes, str, str]:
    """Build a one-tab XLSX with the indicator block.

    Sheet 1 ``Indicadores`` lists every key/value pair in ``indicators``;
    sheet 2 ``Relatório`` paste the markdown body line-by-line so the
    operator still has the narrative context.
    """
    try:
        import openpyxl
    except ImportError as exc:
        raise ToolError(
            "XLSX export requires the optional 'openpyxl' dependency. "
            "Install with `poetry add openpyxl` to enable."
        ) from exc

    wb = openpyxl.Workbook()
    ws_kpis = wb.active
    ws_kpis.title = "Indicadores"
    ws_kpis.append(["Indicador", "Valor"])
    for key, value in (indicators or {}).items():
        ws_kpis.append([str(key), _stringify(value)])

    ws_md = wb.create_sheet("Relatório")
    ws_md.append([title or "Relatório"])
    for line in (markdown_body or "").splitlines():
        ws_md.append([line])

    buf = io.BytesIO()
    wb.save(buf)
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return buf.getvalue(), mime, _filename("xlsx")


def _stringify(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────


def _filename(ext: str) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"relatorio_{stamp}.{ext}"


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return cleaned or "relatorio"
